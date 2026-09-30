"""Directory scanning.

Runs against the user's real disk, so two things are non-negotiable: it must
never raise out of a partial failure (one locked file should not abort a
40,000-file scan), and it must stay cancellable enough that the UI never
freezes. The walk is iterative rather than recursive for the same reason the
JS version was — deep trees are common and recursion is a latent stack
overflow.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Iterator
from pathlib import Path

from .categories import categorise
from .models import Category, FileEntry, ScanResult, SkippedEntry

# Never descended into. Version-control metadata and OS bookkeeping: no use to
# a file organiser, and walking them is slow.
SKIP_DIRECTORIES = frozenset(
    {
        ".git",
        ".svn",
        ".hg",
        ".bzr",
        "$recycle.bin",
        "system volume information",
        "windows.old",
    }
)

# Build output and dependency trees. Huge, and often the biggest thing worth
# reclaiming — so these are *not* skipped by default. Excluding them would
# hide exactly the folders the cleanup view exists to find. Callers that want
# a fast structural scan can opt in to skipping them.
BUILD_DIRECTORIES = frozenset(
    {
        "node_modules",
        "dist",
        "build",
        "out",
        ".next",
        ".nuxt",
        ".svelte-kit",
        "target",
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".cache",
        "coverage",
    }
)

# A generated tree this deep is almost always a symlink loop.
MAX_DEPTH = 24
MAX_ENTRIES = 250_000
PROGRESS_INTERVAL = 0.1  # seconds between progress callbacks

ProgressFn = Callable[[int, int], None]  # (files_seen, queued_directories)
CancelFn = Callable[[], bool]


def is_hidden(path: Path) -> bool:
    """Dotfiles on any platform, plus the Windows hidden attribute."""
    if path.name.startswith("."):
        return True

    if os.name == "nt":
        try:
            import ctypes

            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs != -1 and attrs & 0x2:  # FILE_ATTRIBUTE_HIDDEN
                return True
        except (OSError, AttributeError):
            pass

    return False


def iter_entries(
    root: Path,
    *,
    cancel: CancelFn | None = None,
    progress: ProgressFn | None = None,
    include_hidden: bool = False,
    skip_build_dirs: bool = False,
) -> Iterator[tuple[FileEntry | None, SkippedEntry | None, int]]:
    """Walk `root`, yielding `(file, None, depth)`, `(None, skipped, depth)`, or
    `(None, None, depth)` for a directory that was descended into.

    Separating the two yield shapes keeps the caller from having to unpack
    three loosely-typed values on every iteration.
    """
    seen = 0
    last_progress = 0.0
    stack: list[tuple[Path, int]] = [(root, 0)]

    while stack:
        if cancel and cancel():
            return

        directory, depth = stack.pop()

        if depth > MAX_DEPTH:
            yield None, SkippedEntry(directory, "max depth reached"), depth
            continue

        try:
            with os.scandir(directory) as iterator:
                for item in iterator:
                    if cancel and cancel():
                        return

                    if seen >= MAX_ENTRIES:
                        yield None, SkippedEntry(directory, "entry limit reached"), depth
                        return

                    path = Path(item.path)

                    try:
                        if item.is_dir(follow_symlinks=False):
                            lowered = item.name.lower()
                            if lowered in SKIP_DIRECTORIES:
                                yield (
                                    None,
                                    SkippedEntry(path, "system directory"),
                                    depth,
                                )
                                continue
                            if skip_build_dirs and lowered in BUILD_DIRECTORIES:
                                yield (
                                    None,
                                    SkippedEntry(path, "build directory"),
                                    depth,
                                )
                                continue
                            stack.append((path, depth + 1))
                            yield None, None, depth
                            continue

                        if not item.is_file(follow_symlinks=False):
                            continue

                        if not include_hidden and is_hidden(path):
                            continue

                        stat = item.stat(follow_symlinks=False)
                        extension = path.suffix.lower().lstrip(".")

                        yield (
                            FileEntry(
                                path=path,
                                size=stat.st_size,
                                mtime=stat.st_mtime,
                                category=categorise(extension) or Category.OTHER,
                            ),
                            None,
                            depth,
                        )
                        seen += 1

                        now = time.monotonic()
                        if progress and (now - last_progress) >= PROGRESS_INTERVAL:
                            progress(seen, len(stack))
                            last_progress = now

                    except OSError as error:
                        # Locked by another process, deleted mid-walk, or a
                        # dangling link. None of these should stop a scan.
                        yield None, SkippedEntry(path, f"unreadable: {error.strerror}"), depth

        except PermissionError:
            yield None, SkippedEntry(directory, "permission denied"), depth
        except OSError as error:
            yield None, SkippedEntry(directory, f"unreadable: {error.strerror}"), depth

    if progress:
        progress(seen, 0)


def scan(
    root: Path,
    *,
    cancel: CancelFn | None = None,
    progress: ProgressFn | None = None,
    include_hidden: bool = False,
    skip_build_dirs: bool = False,
) -> ScanResult:
    """Scan `root` recursively and return everything found."""
    started = time.perf_counter()
    result = ScanResult(root=root)

    for entry, skipped, _depth in iter_entries(
        root,
        cancel=cancel,
        progress=progress,
        include_hidden=include_hidden,
        skip_build_dirs=skip_build_dirs,
    ):
        if entry is not None:
            result.files.append(entry)
        elif skipped is not None:
            result.skipped.append(skipped)
        else:
            result.directories += 1

    result.duration_s = time.perf_counter() - started
    result.cancelled = bool(cancel and cancel())
    return result


class ScanJob:
    """Handle for a scan running on a worker thread.

    `result` is only meaningful once `finished` is true. Reading it earlier
    returns an empty result rather than blocking, so the UI can poll freely.
    """

    def __init__(
        self,
        root: Path,
        *,
        include_hidden: bool = False,
        skip_build_dirs: bool = False,
    ) -> None:
        import threading

        self._root = root
        self._include_hidden = include_hidden
        self._skip_build_dirs = skip_build_dirs
        self._stop = threading.Event()
        self._done = threading.Event()
        self._result = ScanResult(root=root)
        self._error: BaseException | None = None

        self._thread = threading.Thread(target=self._run, name="fileflow-scan", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            self._result = scan(
                self._root,
                cancel=self._stop.is_set,
                include_hidden=self._include_hidden,
                skip_build_dirs=self._skip_build_dirs,
            )
        except BaseException as error:  # surfaced via .error, not swallowed
            self._error = error
        finally:
            self._done.set()

    @property
    def finished(self) -> bool:
        return self._done.is_set()

    @property
    def cancelled(self) -> bool:
        return self._stop.is_set()

    @property
    def result(self) -> ScanResult:
        return self._result

    @property
    def error(self) -> BaseException | None:
        return self._error

    def cancel(self) -> None:
        """Ask the walk to stop. Returns once the thread has actually exited,
        so the caller knows no further filesystem access is in flight."""
        self._stop.set()
        self._thread.join(timeout=5.0)

    def wait(self, timeout: float | None = None) -> ScanResult:
        self._thread.join(timeout)
        if not self.finished:
            raise TimeoutError("scan did not finish in time")
        if self._error is not None:
            raise self._error
        return self._result


def scan_in_background(
    root: Path,
    *,
    include_hidden: bool = False,
    skip_build_dirs: bool = False,
) -> ScanJob:
    """Convenience wrapper returning a `ScanJob`."""
    return ScanJob(
        root,
        include_hidden=include_hidden,
        skip_build_dirs=skip_build_dirs,
    )
