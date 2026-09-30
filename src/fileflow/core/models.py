"""Core data types shared across FileFlow.

Everything the scanner produces is immutable. Operations return new values
rather than mutating in place, which keeps the undo journal honest: a journal
entry records the before-state, and reversing it never has to reason about what
some other code path might have changed in the meantime.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path


class Category(enum.StrEnum):
    """File categories. Values are the on-disk folder names."""

    DOCUMENTS = "Documents"
    IMAGES = "Images"
    VIDEO = "Video"
    AUDIO = "Audio"
    ARCHIVES = "Archives"
    CODE = "Code"
    DESIGN = "Design"
    OTHER = "Other"


@dataclass(frozen=True, slots=True)
class FileEntry:
    """A single file found during a scan."""

    path: Path
    size: int
    mtime: float
    category: Category = Category.OTHER
    hidden: bool = False

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def parent(self) -> Path:
        return self.path.parent

    @property
    def extension(self) -> str:
        return self.path.suffix.lower().lstrip(".")

    @property
    def modified(self) -> datetime:
        return datetime.fromtimestamp(self.mtime)

    @property
    def is_locked(self) -> bool:
        """Office and LibreOffice leave lock files that cannot be renamed."""
        return self.name.startswith("~$")

    def with_category(self, category: Category) -> FileEntry:
        return replace(self, category=category)

    def relative_to(self, root: Path) -> str:
        """Display path relative to the scan root, for grouping and display."""
        try:
            return str(self.path.relative_to(root))
        except ValueError:
            return str(self.path)


@dataclass(frozen=True, slots=True)
class SkippedEntry:
    """A path we could not read, with the reason."""

    path: Path
    reason: str


@dataclass(slots=True)
class ScanResult:
    """Outcome of one scan pass."""

    root: Path
    files: list[FileEntry] = field(default_factory=list)
    skipped: list[SkippedEntry] = field(default_factory=list)
    directories: int = 0
    duration_s: float = 0.0
    truncated: bool = False
    cancelled: bool = False

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files)

    def by_category(self) -> dict[Category, list[FileEntry]]:
        groups: dict[Category, list[FileEntry]] = {}
        for entry in self.files:
            groups.setdefault(entry.category, []).append(entry)
        return groups


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    """Byte-identical files. `keep` is the one that survives a cleanup."""

    files: tuple[FileEntry, ...]
    size: int

    @property
    def keep(self) -> FileEntry:
        """Oldest copy. If two copies differ the newer one was edited more
        recently, so the older one is the safer default to keep."""
        return min(self.files, key=lambda f: f.mtime)

    @property
    def redundant(self) -> tuple[FileEntry, ...]:
        keep = self.keep
        return tuple(f for f in self.files if f != keep)

    @property
    def wasted(self) -> int:
        return self.size * (len(self.files) - 1)
