"""Filesystem mutations.

This is the only module that changes anything on disk, and every path through
it writes a journal entry before the change and reverses it on request. The
ordering matters: journal first, then act. A crash between the two leaves a
reversible record of an operation that did not happen, which is recoverable.
The reverse order would leave a file moved with no way back.

Nothing here deletes. Removals move to a quarantine folder so undo is a rename.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .journal import QUARANTINE_DIR, Journal, OperationKind
from .models import FileEntry
from .renamer import RenameStep
from .rules import ActionKind, PlannedChange


@dataclass(frozen=True, slots=True)
class OperationResult:
    """Outcome of one apply. Failures are collected, never raised, so a batch
    that partially succeeds still reports what it did."""

    applied: int = 0
    failed: int = 0
    errors: tuple[str, ...] = ()
    batch: str = ""
    bytes_moved: int = 0

    def __bool__(self) -> bool:
        return self.applied > 0

    def summary(self) -> str:
        if not self.errors:
            return f"{self.applied} file{'s' if self.applied != 1 else ''} done"
        return f"{self.applied} done, {self.failed} failed"


@dataclass(slots=True)
class _Accumulator:
    batch: str = field(default_factory=lambda: "")
    applied: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    bytes_moved: int = 0


def _finish(acc: _Accumulator) -> OperationResult:
    return OperationResult(
        applied=acc.applied,
        failed=acc.failed,
        errors=tuple(acc.errors),
        batch=acc.batch,
        bytes_moved=acc.bytes_moved,
    )


def _move_one(
    source: Path,
    destination: Path,
    *,
    kind: OperationKind,
    summary: str,
    journal: Journal,
    batch: str,
) -> str | None:
    """Move one file, journalling first. Returns an error string, or None."""
    entry_id = journal.record(
        kind,
        summary,
        {"from": str(source), "to": str(destination)},
        batch=batch,
    )

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        # A no-op move (same path) would make the journal's reverse a rename
        # onto itself. Skip it entirely.
        if source.resolve() == destination.resolve():
            journal.mark_undone([entry_id])
            return None

        os.replace(source, destination)
        return None

    except OSError as error:
        # The journal entry described a change that did not happen, so retire
        # it rather than leaving a phantom undoable operation behind.
        journal.mark_undone([entry_id])
        return f"{source.name}: {error.strerror or error}"


def apply_renames(
    steps: Sequence[RenameStep],
    journal: Journal,
    *,
    batch: str | None = None,
) -> OperationResult:
    """Apply a rename plan."""
    acc = _Accumulator(batch=batch or journal.new_batch())

    for step in steps:
        error = _move_one(
            step.source,
            step.target,
            kind=OperationKind.RENAME,
            summary=f"Renamed {step.before} to {step.after}",
            journal=journal,
            batch=acc.batch,
        )
        if error:
            acc.failed += 1
            acc.errors.append(error)
        else:
            acc.applied += 1

    return _finish(acc)


def apply_rule_plan(
    changes: Sequence[PlannedChange],
    journal: Journal,
    *,
    root: Path,
    batch: str | None = None,
) -> OperationResult:
    """Apply the output of `RuleEngine.plan`.

    MOVE and RENAME_AND_MOVE are one rename each — a file renamed and moved
    lands directly at its final path, so there is a single reversible step
    rather than two.
    """
    acc = _Accumulator(batch=batch or journal.new_batch())

    for change in changes:
        if change.kind is ActionKind.TAG:
            # Tags are metadata only. Recorded in the activity log, no disk
            # change, nothing to undo.
            acc.applied += 1
            continue

        if change.target is None:
            acc.failed += 1
            acc.errors.append(f"{change.entry.name}: rule produced no destination")
            continue

        source = change.entry.path
        destination = root / change.target

        if not source.exists():
            acc.failed += 1
            acc.errors.append(f"{source.name}: no longer exists")
            continue

        if destination.exists() and destination != source:
            acc.failed += 1
            acc.errors.append(f"{destination.name}: already exists")
            continue

        error = _move_one(
            source,
            destination,
            kind=OperationKind.MOVE,
            summary=f"Moved {change.entry.name} to {change.target} ({change.rule.name})",
            journal=journal,
            batch=acc.batch,
        )
        if error:
            acc.failed += 1
            acc.errors.append(error)
        else:
            acc.applied += 1
            acc.bytes_moved += change.entry.size

    return _finish(acc)


def quarantine(
    files: Iterable[FileEntry],
    journal: Journal,
    *,
    root: Path,
    reason: str = "",
    batch: str | None = None,
) -> OperationResult:
    """Move files to a quarantine folder rather than deleting them.

    This is what "remove" means in FileFlow. Deleting from a GUI is not
    something to do quietly, and a quarantine folder means undo is a move back
    rather than a recovery from the Recycle Bin.
    """
    acc = _Accumulator(batch=batch or journal.new_batch())
    quarantine_root = root / QUARANTINE_DIR

    for entry in files:
        if not entry.path.exists():
            acc.failed += 1
            acc.errors.append(f"{entry.name}: no longer exists")
            continue

        # Flat layout keyed by original location, so two files called
        # `report.pdf` from different folders do not overwrite each other.
        try:
            safe = str(entry.path.relative_to(root)).replace(os.sep, "__")
        except ValueError:
            # The entry is not under this root. Refuse it rather than letting
            # `relative_to` raise out of a per-file loop and abandon the batch.
            acc.failed += 1
            acc.errors.append(f"{entry.name}: outside the open folder, skipped")
            continue

        destination = quarantine_root / f"{datetime.now():%Y%m%d}_{safe}"

        error = _move_one(
            entry.path,
            destination,
            kind=OperationKind.QUARANTINE,
            summary=f"Removed {entry.name}{f' ({reason})' if reason else ''}",
            journal=journal,
            batch=acc.batch,
        )
        if error:
            acc.failed += 1
            acc.errors.append(error)
        else:
            acc.applied += 1
            acc.bytes_moved += entry.size

    return _finish(acc)


def purge_quarantine(
    entries: Sequence[FileEntry],
    journal: Journal,
    *,
    root: Path,
) -> OperationResult:
    """Permanently delete quarantined files. This one really deletes.

    Separate from `quarantine` on purpose, and it refuses to touch anything
    outside the quarantine folder, so a bug elsewhere cannot turn "remove from
    the view" into "erase from disk".
    """
    acc = _Accumulator(batch=journal.new_batch())
    quarantine_root = (root / QUARANTINE_DIR).resolve()

    for entry in entries:
        try:
            resolved = entry.path.resolve()
        except OSError as error:
            acc.failed += 1
            acc.errors.append(f"{entry.name}: {error}")
            continue

        if quarantine_root not in resolved.parents:
            acc.failed += 1
            acc.errors.append(f"{entry.name}: refusing to delete outside quarantine")
            continue

        try:
            resolved.unlink()
            acc.applied += 1
            acc.bytes_moved += entry.size
        except OSError as error:
            acc.failed += 1
            acc.errors.append(f"{entry.name}: {error.strerror or error}")

    return _finish(acc)


def undo_last(journal: Journal) -> tuple[int, list[str]]:
    """Reverse the most recent batch. The single most-used safety net in the app."""
    batches = journal.batches(limit=1)
    if not batches:
        return 0, ["nothing to undo"]
    return journal.undo_batch(batches[0][0])


def sort_into_categories(
    files: Sequence[FileEntry],
    journal: Journal,
    *,
    root: Path,
    batch: str | None = None,
) -> OperationResult:
    """One-tidy operation: move each file into a folder named after its
    category. The default first-run action, because it needs no configuration
    and is easy to reverse."""
    acc = _Accumulator(batch=batch or journal.new_batch())

    for entry in files:
        if entry.path.parent == root / entry.category.value:
            continue  # already where it belongs

        destination = root / entry.category.value / entry.name

        if destination.exists():
            acc.failed += 1
            acc.errors.append(f"{entry.name}: already in {entry.category.value}")
            continue

        error = _move_one(
            entry.path,
            destination,
            kind=OperationKind.MOVE,
            summary=f"Sorted {entry.name} into {entry.category.value}",
            journal=journal,
            batch=acc.batch,
        )
        if error:
            acc.failed += 1
            acc.errors.append(error)
        else:
            acc.applied += 1
            acc.bytes_moved += entry.size

    return _finish(acc)


def copy_backups(
    files: Sequence[FileEntry],
    destination: Path,
    *,
    progress=None,
) -> OperationResult:
    """Copy files to a backup folder. Copies, not moves, and is not journalled
    because it changes nothing about the originals."""
    acc = _Accumulator()
    total = len(files)

    for index, entry in enumerate(files):
        try:
            target = destination / entry.name
            if target.exists():
                target = destination / f"{entry.path.stem}_{index}{entry.path.suffix}"
            shutil.copy2(entry.path, target)
            acc.applied += 1
            acc.bytes_moved += entry.size
        except OSError as error:
            acc.failed += 1
            acc.errors.append(f"{entry.name}: {error.strerror or error}")

        if progress:
            progress(index + 1, total)

    return _finish(acc)
