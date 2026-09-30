"""Bulk rename planning.

Planning is separated from execution on purpose. `plan_*` functions are pure,
return every step *and* every reason a file was skipped, and never touch the
disk. The UI shows that plan for review, and only an approved plan reaches
`operations.apply_renames`. It also means collisions are caught before anything
is written rather than half-way through a batch.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .models import FileEntry

# Characters illegal on Windows or macOS, plus control characters.
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r"\s+")

# Windows refuses these regardless of extension.
_RESERVED_STEMS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)

MAX_NAME_LENGTH = 240

# Single pass, with the literal-brace alternatives first. Order matters: if
# `{token}` were tried before `{{`, the inner braces of `{{name}}` would be
# consumed as a token and the escaping would not work.
_TOKEN = re.compile(
    r"(?P<open>\{\{)"
    r"|(?P<close>\}\})"
    r"|\{(?P<token>name|stem|ext|parent|date|time|year|month|day|index"
    r"|index:\d+|case:lower|case:upper|case:kebab|case:snake|case:title)\}"
)


@dataclass(frozen=True, slots=True)
class RenameStep:
    entry: FileEntry
    source: Path
    target: Path
    before: str
    after: str


@dataclass(frozen=True, slots=True)
class RenameSkip:
    entry: FileEntry
    reason: str


@dataclass(frozen=True, slots=True)
class RenamePlan:
    steps: tuple[RenameStep, ...]
    skipped: tuple[RenameSkip, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.steps)

    def __len__(self) -> int:
        return len(self.steps)

    @property
    def affected_folders(self) -> list[Path]:
        seen: dict[Path, None] = {}
        for step in self.steps:
            seen.setdefault(step.source.parent, None)
        return list(seen)


def sanitise_name(name: str) -> str:
    """Make `name` safe on Windows and macOS.

    Trailing dots and spaces are stripped because Windows removes them
    silently, which would leave the filesystem holding a name that differs
    from the one we recorded in the undo journal.
    """
    cleaned = _WHITESPACE.sub(" ", _ILLEGAL.sub("", name)).strip()

    stem = cleaned.rsplit(".", 1)[0] if "." in cleaned else cleaned
    if stem.upper() in _RESERVED_STEMS:
        cleaned = f"_{cleaned}"

    trimmed = cleaned.rstrip(". ")
    return trimmed[:MAX_NAME_LENGTH]


def _apply_case(style: str, stem: str) -> str:
    if style == "lower":
        return stem.lower()
    if style == "upper":
        return stem.upper()
    if style == "title":
        return re.sub(r"\w\S*", lambda m: m.group()[0].upper() + m.group()[1:].lower(), stem)
    if style == "kebab":
        return re.sub(
            r"-+", "-", re.sub(r"[\s_]+", "-", re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", stem))
        ).strip("-").lower()
    if style == "snake":
        return re.sub(
            r"_+", "_", re.sub(r"[\s-]+", "_", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", stem))
        ).strip("_").lower()
    return stem


def expand_pattern(
    pattern: str,
    entry: FileEntry,
    *,
    index: int = 0,
    width: int = 3,
) -> str:
    """Expand a rename pattern for one file.

    Tokens:
      {name} {stem} {ext} {parent}
      {date} {time} {year} {month} {day}
      {index} {index:N}   1-based, zero-padded to N (or to `width`)
      {case:lower|upper|kebab|snake|title}   transforms the stem only

    `{ext}` includes the leading dot, so `{stem}{ext}` reassembles the original
    name. Write `{{` and `}}` for literal braces.
    """
    modified = datetime.fromtimestamp(entry.mtime)
    stem = entry.path.stem
    suffix = entry.path.suffix

    values = {
        "name": entry.name,
        "stem": stem,
        # With the dot. `{stem}{ext}` is the natural way to write a pattern and
        # it has to round-trip, so `{ext}` is ".txt" and not "txt".
        "ext": suffix,
        "parent": entry.parent.name,
        "date": modified.strftime("%Y-%m-%d"),
        "time": modified.strftime("%H%M"),
        "year": modified.strftime("%Y"),
        "month": modified.strftime("%m"),
        "day": modified.strftime("%d"),
        "index": str(index + 1).zfill(width),
    }

    def replace(match: re.Match[str]) -> str:
        if match.group("open"):
            return "{"
        if match.group("close"):
            return "}"

        token = match.group("token")

        if token.startswith("case:"):
            # Applied to the stem, not the full name: lowercasing someone's
            # extension reads as a bug.
            return _apply_case(token.split(":", 1)[1], stem)

        if token.startswith("index:"):
            return str(index + 1).zfill(int(token.split(":", 1)[1]))

        return values.get(token, match.group(0))

    return _TOKEN.sub(replace, pattern)


def _name_exists_elsewhere(source: Path, target: Path) -> bool:
    """True if `target` is occupied by something other than `source`.

    Compares case-insensitively because Windows and macOS both do, so a
    rename that only changes case can otherwise appear to succeed and silently
    do nothing.
    """
    try:
        resolved = target.resolve()
    except OSError:
        resolved = target

    try:
        if resolved == source.resolve():
            return False
    except OSError:
        pass

    # A case-only rename: the path "exists" as itself on a case-insensitive
    # filesystem, which the resolve comparison above already handled.
    return target.exists()


def plan_rename(
    files: Sequence[FileEntry],
    pattern: str,
    *,
    start_index: int = 0,
    width: int = 3,
) -> RenamePlan:
    """Plan a pattern rename across `files`."""
    targets: list[tuple[FileEntry, str]] = []
    skipped: list[RenameSkip] = []

    for offset, entry in enumerate(files):
        if entry.is_locked:
            skipped.append(RenameSkip(entry, "Office lock file"))
            continue

        proposed = sanitise_name(
            expand_pattern(pattern, entry, index=start_index + offset, width=width)
        )
        if not proposed:
            skipped.append(RenameSkip(entry, "pattern produced an empty name"))
            continue

        if proposed == entry.name:
            skipped.append(RenameSkip(entry, "name unchanged"))
            continue

        targets.append((entry, proposed))

    return _build_plan(targets, skipped)


def plan_find_replace(
    files: Sequence[FileEntry],
    find: str,
    replace: str,
    *,
    regex: bool = False,
    flags: re.RegexFlag = re.IGNORECASE,
) -> RenamePlan:
    """Plan a find-and-replace across filenames, leaving extensions alone."""
    if not find:
        return RenamePlan((), (RenameSkip(e, "find string is empty") for e in files))

    try:
        pattern = re.compile(find, flags) if regex else None
    except re.error as error:
        return RenamePlan((), (RenameSkip(e, f"invalid pattern: {error}") for e in files))

    targets: list[tuple[FileEntry, str]] = []
    skipped: list[RenameSkip] = []

    for entry in files:
        if entry.is_locked:
            skipped.append(RenameSkip(entry, "Office lock file"))
            continue

        stem, suffix = entry.path.stem, entry.path.suffix
        new_stem = pattern.sub(replace, stem) if pattern else stem.replace(find, replace)

        if new_stem == stem:
            skipped.append(RenameSkip(entry, "no match"))
            continue

        targets.append((entry, sanitise_name(f"{new_stem}{suffix}")))

    return _build_plan(targets, skipped)


def _build_plan(
    targets: list[tuple[FileEntry, str]],
    skipped: list[RenameSkip],
) -> RenamePlan:
    """Turn proposed names into steps, rejecting anything that would collide.

    Two distinct collisions are checked, and they need different messages:
    a name already on disk, and a name another file in this same batch is
    also claiming.
    """
    steps: list[RenameStep] = []
    claimed: dict[str, FileEntry] = {}

    for entry, proposed in targets:
        target = entry.parent / proposed
        key = str(target).casefold()

        if key in claimed:
            skipped.append(
                RenameSkip(
                    entry,
                    f'"{proposed}" is also claimed by {claimed[key].name} in this batch',
                )
            )
            continue

        if _name_exists_elsewhere(entry.path, target):
            skipped.append(RenameSkip(entry, f'"{proposed}" already exists'))
            continue

        claimed[key] = entry
        steps.append(
            RenameStep(
                entry=entry,
                source=entry.path,
                target=target,
                before=entry.name,
                after=proposed,
            )
        )

    return RenamePlan(tuple(steps), tuple(skipped))


def execute_renames(
    steps: Iterable[RenameStep],
) -> tuple[list[RenameStep], list[RenameSkip]]:
    """Apply a plan. Returns what actually moved and what failed.

    Deliberately not transactional: a batch rename that fails halfway is
    recoverable through the undo journal, and pretending otherwise would hide
    real filesystem errors. Callers journal each successful step as it lands.
    """
    applied: list[RenameStep] = []
    failed: list[RenameSkip] = []

    for step in steps:
        try:
            os.rename(step.source, step.target)
            applied.append(step)
        except OSError as error:
            failed.append(RenameSkip(step.entry, f"{error.strerror or error}"))

    return applied, failed
