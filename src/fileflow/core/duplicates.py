"""Duplicate detection.

Two passes, in this order for a reason: group by exact byte size first (free,
no reads), then hash only within groups that actually have a collision. On a
typical folder that skips 95%+ of the files entirely.

Hashing is streamed in chunks so a 4 GB video does not become 4 GB of resident
memory, which is what the browser version had to give up on.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from .models import DuplicateGroup, FileEntry

CHUNK_SIZE = 1024 * 1024  # 1 MiB
# Beyond this we stop hashing and say so, rather than hanging on one huge file.
MAX_HASH_BYTES = 8 * 1024**3

ProgressFn = Callable[[int, int], None]  # (hashed, total_candidates)
CancelFn = Callable[[], bool]


@dataclass(frozen=True, slots=True)
class DuplicateReport:
    groups: tuple[DuplicateGroup, ...]
    hashed: int
    skipped_large: int
    cancelled: bool = False

    @property
    def total_redundant_files(self) -> int:
        return sum(len(g.redundant) for g in self.groups)

    @property
    def reclaimable(self) -> int:
        return sum(g.wasted for g in self.groups)


def hash_file(path: Path, *, cancel: CancelFn | None = None) -> str:
    """SHA-256 of a file's contents, read in chunks."""
    if path.stat().st_size > MAX_HASH_BYTES:
        raise ValueError(f"file exceeds hash limit: {path}")

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            if cancel and cancel():
                raise InterruptedError("cancelled")
            digest.update(chunk)

    return digest.hexdigest()


def find_duplicates(
    files: Iterable[FileEntry],
    *,
    cancel: CancelFn | None = None,
    progress: ProgressFn | None = None,
) -> DuplicateReport:
    """Find byte-identical files.

    Zero-byte files are excluded: they are trivially identical and reporting
    every one of them buries the groups that matter.
    """
    by_size: dict[int, list[FileEntry]] = {}
    for entry in files:
        if entry.size == 0:
            continue
        by_size.setdefault(entry.size, []).append(entry)

    candidates = [group for group in by_size.values() if len(group) > 1]
    total = sum(len(group) for group in candidates)

    by_digest: dict[tuple[int, str], list[FileEntry]] = {}
    hashed = 0
    skipped_large = 0
    cancelled = False

    for group in candidates:
        if cancel and cancel():
            cancelled = True
            break

        for entry in group:
            if cancel and cancel():
                cancelled = True
                break

            if entry.size > MAX_HASH_BYTES:
                skipped_large += 1
                continue

            try:
                digest = hash_file(entry.path, cancel=cancel)
            except (InterruptedError, ValueError):
                if cancel and cancel():
                    cancelled = True
                    break
                continue
            except OSError:
                # Unreadable since the scan. Leave it alone.
                continue

            by_digest.setdefault((entry.size, digest), []).append(entry)

            hashed += 1
            if progress:
                progress(hashed, total)

    groups = tuple(
        DuplicateGroup(files=tuple(members), size=size)
        for (size, _digest), members in by_digest.items()
        if len(members) > 1
    )

    # Largest reclaimable first: that is the order a user wants to act in.
    ordered = tuple(sorted(groups, key=lambda g: g.wasted, reverse=True))

    return DuplicateReport(
        groups=ordered,
        hashed=hashed,
        skipped_large=skipped_large,
        cancelled=cancelled,
    )


@dataclass(frozen=True, slots=True)
class NameVariantGroup:
    """Files whose names look like copies of each other but whose contents
    differ. The right response is usually rename, not delete, so these are kept
    separate from true duplicates."""

    stem: str
    variants: tuple[FileEntry, ...]

    @property
    def newest(self) -> FileEntry:
        return max(self.variants, key=lambda f: f.mtime)


_COPY_MARKERS = ("(", "[", " copy", "-copy", "_copy", "final", " v")


def _normalise_stem(name: str) -> str:
    stem = name.rsplit(".", 1)[0] if "." in name else name
    lowered = stem.lower()

    for marker in _COPY_MARKERS:
        index = lowered.find(marker)
        if index > 0:
            stem = stem[:index]
            lowered = lowered[:index]

    # Strip trailing separators and digits: "report 2", "report-2", "report_2".
    while stem and (stem[-1].isdigit() or stem[-1] in " -_"):
        stem = stem[:-1]

    return "".join(ch for ch in stem.lower() if ch.isalnum())


def find_name_variants(files: Iterable[FileEntry]) -> tuple[NameVariantGroup, ...]:
    """Files that look like `report (1).pdf` / `report (2).pdf` but differ in
    size, so they are not duplicates."""
    groups: dict[tuple[str, str], list[FileEntry]] = {}

    for entry in files:
        key = (_normalise_stem(entry.name), entry.extension)
        if not key[0]:
            continue
        groups.setdefault(key, []).append(entry)

    variants = tuple(
        NameVariantGroup(
            stem=members[0].name.rsplit(".", 1)[0],
            variants=tuple(sorted(members, key=lambda f: f.mtime)),
        )
        for members in groups.values()
        if len(members) > 1 and len({m.size for m in members}) > 1
    )

    return tuple(sorted(variants, key=lambda g: len(g.variants), reverse=True))
