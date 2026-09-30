"""The rule engine.

A rule is a matcher (which files) plus an action (what to do with them).
Matching is pure and side-effect free: `RuleEngine.plan()` returns what *would*
happen, and nothing is written until a caller hands an approved plan to
`operations.apply_rule_plan`. That split is the whole reason this is safe to
point at a real folder.
"""

from __future__ import annotations

import enum
import re
import uuid
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .models import FileEntry
from .renamer import expand_pattern, sanitise_name


class Field(enum.StrEnum):
    """The part of a file a matcher looks at."""

    NAME = "name"
    EXTENSION = "extension"
    SIZE = "size"
    MODIFIED = "modified"
    PATH = "path"


class Comparison(enum.StrEnum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    OLDER_THAN_DAYS = "older_than_days"
    NEWER_THAN_DAYS = "newer_than_days"
    MATCHES = "matches"  # regex


@dataclass(frozen=True, slots=True)
class Matcher:
    field: Field
    comparison: Comparison
    value: str

    def describe(self) -> str:
        symbols = {
            Comparison.GREATER_THAN: ">",
            Comparison.LESS_THAN: "<",
            Comparison.OLDER_THAN_DAYS: "older than",
            Comparison.NEWER_THAN_DAYS: "newer than",
            Comparison.IN: "in",
            Comparison.MATCHES: "matches",
        }
        if self.comparison in symbols:
            return f"{self.field.value} {symbols[self.comparison]} {self.value}"
        return f"{self.field.value} {self.comparison.value.replace('_', ' ')} {self.value}"

    def test(self, entry: FileEntry, now: datetime | None = None) -> bool:
        reference = now or datetime.now()

        if self.field is Field.NAME:
            return _compare_text(entry.name, self.comparison, self.value)
        if self.field is Field.EXTENSION:
            return _compare_text(entry.extension, self.comparison, self.value)
        if self.field is Field.PATH:
            return _compare_text(str(entry.path), self.comparison, self.value)
        if self.field is Field.SIZE:
            return _compare_number(entry.size, self.comparison, self.value)
        if self.field is Field.MODIFIED:
            return _compare_date(entry, self.comparison, self.value, reference)

        return False


def _compare_text(actual: str, comparison: Comparison, expected: str) -> bool:
    left, right = actual.lower(), expected.strip().lower()

    match comparison:
        case Comparison.EQUALS:
            return left == right
        case Comparison.NOT_EQUALS:
            return left != right
        case Comparison.CONTAINS:
            return right in left
        case Comparison.STARTS_WITH:
            return left.startswith(right)
        case Comparison.ENDS_WITH:
            return left.endswith(right)
        case Comparison.IN:
            return left in _split_list(expected)
        case Comparison.MATCHES:
            try:
                return re.search(expected, actual, re.IGNORECASE) is not None
            except re.error:
                return False
        case _:
            return False


def _split_list(value: str) -> set[str]:
    return {part.strip().lower() for part in re.split(r"[,\n]", value) if part.strip()}


def _parse_size(value: str) -> int | None:
    """Accepts `500`, `500kb`, `1.5 GB`, `2m`."""
    match = re.fullmatch(r"\s*([\d.]+)\s*([kmgt]?b?)\s*", value, re.IGNORECASE)
    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2).lower().rstrip("b") or ""

    multipliers = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3, "t": 1024**4}
    return int(number * multipliers.get(unit, 1))


def _compare_number(actual: int, comparison: Comparison, expected: str) -> bool:
    target = _parse_size(expected)
    if target is None:
        return False

    match comparison:
        case Comparison.EQUALS:
            return actual == target
        case Comparison.NOT_EQUALS:
            return actual != target
        case Comparison.GREATER_THAN:
            return actual > target
        case Comparison.LESS_THAN:
            return actual < target
        case _:
            return False


def _compare_date(
    entry: FileEntry, comparison: Comparison, expected: str, now: datetime
) -> bool:
    try:
        days = int(re.sub(r"[^\d]", "", expected) or "0")
    except ValueError:
        return False

    delta = now - entry.modified

    match comparison:
        case Comparison.OLDER_THAN_DAYS:
            return delta > timedelta(days=days)
        case Comparison.NEWER_THAN_DAYS:
            return delta < timedelta(days=days)
        case Comparison.GREATER_THAN:
            return delta > timedelta(days=days)
        case _:
            return False


class ActionKind(enum.StrEnum):
    MOVE = "move"
    RENAME = "rename"
    RENAME_AND_MOVE = "rename_and_move"
    TAG = "tag"  # recorded in the activity log; does not touch the filesystem


@dataclass(frozen=True, slots=True)
class Action:
    kind: ActionKind
    #: Destination folder for MOVE. Supports `{category}`, `{year}`, `{month}`,
    #: `{day}`, `{name}` and `{parent}`.
    destination: str = ""
    #: Rename pattern for RENAME.
    pattern: str = ""
    #: Tag name for TAG.
    tag: str = ""
    #: Create the destination folder if it is missing.
    create_missing: bool = True

    def describe(self) -> str:
        match self.kind:
            case ActionKind.MOVE:
                return f"move to {self.destination or '(no destination)'}"
            case ActionKind.RENAME:
                return f"rename to {self.pattern or '(no pattern)'}"
            case ActionKind.RENAME_AND_MOVE:
                return f"rename to {self.pattern} and move to {self.destination}"
            case ActionKind.TAG:
                return f"tag as {self.tag}"
            case _:
                return "no action"


@dataclass(slots=True)
class Rule:
    name: str
    matchers: list[Matcher]
    action: Action
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    enabled: bool = True
    priority: int = 100  # lower runs first
    run_count: int = 0
    last_run: datetime | None = None

    def matches(self, entry: FileEntry, now: datetime | None = None) -> bool:
        """All matchers must agree. There is deliberately no OR: a rule that
        can be loosened per-matcher is a rule nobody can reason about."""
        if not self.matchers:
            return False
        return all(m.test(entry, now) for m in self.matchers)

    def describe(self) -> str:
        conditions = " and ".join(m.describe() for m in self.matchers) or "(no conditions)"
        return f"if {conditions} then {self.action.describe()}"


@dataclass(frozen=True, slots=True)
class PlannedChange:
    """One file, one intended outcome. Nothing has happened yet."""

    entry: FileEntry
    rule: Rule
    source: str
    target: str | None
    kind: ActionKind
    note: str = ""


@dataclass(frozen=True, slots=True)
class RulePlan:
    changes: tuple[PlannedChange, ...]
    unmatched: int
    skipped: int
    rule_hits: dict[str, int]

    def __bool__(self) -> bool:
        return bool(self.changes)

    def __len__(self) -> int:
        return len(self.changes)

    @property
    def by_kind(self) -> dict[ActionKind, list[PlannedChange]]:
        groups: dict[ActionKind, list[PlannedChange]] = {}
        for change in self.changes:
            groups.setdefault(change.kind, []).append(change)
        return groups


ProgressFn = Callable[[int, int], None]


class RuleEngine:
    """Evaluates rules against a set of files."""

    def __init__(self, rules: Iterable[Rule] | None = None) -> None:
        self.rules: list[Rule] = sorted(rules or [], key=lambda r: (r.priority, r.name))

    def add(self, rule: Rule) -> None:
        self.rules.append(rule)
        self.rules.sort(key=lambda r: (r.priority, r.name))

    def remove(self, rule_id: str) -> bool:
        before = len(self.rules)
        self.rules = [r for r in self.rules if r.id != rule_id]
        return len(self.rules) != before

    def get(self, rule_id: str) -> Rule | None:
        return next((r for r in self.rules if r.id == rule_id), None)

    def plan(
        self,
        files: Sequence[FileEntry],
        *,
        root: str | Path = "",
        now: datetime | None = None,
        first_match_wins: bool = True,
        progress: ProgressFn | None = None,
    ) -> RulePlan:
        """Work out what the rules would do. Pure — writes nothing.

        `first_match_wins` is the default because the usual case is one file
        landing in one place. Turning it off lets several rules contribute,
        which is occasionally what you want and usually a mess.
        """
        root_path = Path(root) if root else Path()
        active = [r for r in self.rules if r.enabled]
        changes: list[PlannedChange] = []
        rule_hits: dict[str, int] = {r.id: 0 for r in active}
        unmatched = 0
        skipped = 0

        total = len(files)
        for position, entry in enumerate(files):
            if progress and position % 200 == 0:
                progress(position, total)

            matched_any = False

            for rule in active:
                if not rule.matches(entry, now):
                    continue

                matched_any = True
                rule_hits[rule.id] += 1

                change = self._build_change(rule, entry, root_path)
                if change is None:
                    skipped += 1
                    continue

                changes.append(change)

                if first_match_wins:
                    break

            if not matched_any:
                unmatched += 1

        if progress:
            progress(total, total)

        return RulePlan(
            changes=tuple(changes),
            unmatched=unmatched,
            skipped=skipped,
            rule_hits=rule_hits,
        )

    def _build_change(
        self, rule: Rule, entry: FileEntry, root: Path
    ) -> PlannedChange | None:
        if entry.is_locked:
            return None

        action = rule.action

        if action.kind is ActionKind.TAG:
            return PlannedChange(
                entry=entry, rule=rule, source=entry.name, target=None, kind=action.kind
            )

        new_name: str | None = None

        if action.kind in (ActionKind.RENAME, ActionKind.RENAME_AND_MOVE):
            if not action.pattern:
                return None
            expanded = sanitise_name(expand_pattern(action.pattern, entry))
            if not expanded or expanded == entry.name:
                return None
            new_name = expanded

        target: str | None = None

        if action.kind is ActionKind.RENAME:
            # A pure rename stays in its own folder, expressed relative to the
            # scan root. Without this, rename-only rules plan no destination and
            # silently never fire; using entry.parent.name instead would leak
            # the root's own folder name into the path.
            target = str(Path(_relative_parent(entry, root)) / new_name)

        elif action.kind in (ActionKind.MOVE, ActionKind.RENAME_AND_MOVE):
            folder = _expand_destination(action.destination, entry)
            if not folder:
                return None
            target = f"{folder}/{new_name or entry.name}"

        return PlannedChange(
            entry=entry,
            rule=rule,
            source=entry.name,
            target=target,
            kind=action.kind,
            note=new_name or "",
        )


def _relative_parent(entry: FileEntry, root: Path) -> str:
    """The file's folder relative to the scan root, or '' when it sits at the
    root. Windows-safe: `relative_to` rather than string surgery."""
    try:
        return str(entry.parent.relative_to(root))
    except ValueError:
        return entry.parent.name


def _expand_destination(template: str, entry: FileEntry) -> str:
    if not template:
        return ""

    values = {
        "category": entry.category.value,
        "year": entry.modified.strftime("%Y"),
        "month": entry.modified.strftime("%m"),
        "day": entry.modified.strftime("%d"),
        "name": entry.path.stem,
        "parent": entry.parent.name,
    }

    def replace(match: re.Match[str]) -> str:
        return values.get(match.group(1), match.group(0))

    expanded = re.sub(r"\{(\w+)\}", replace, template)
    return expanded.strip().replace("\\", "/").strip("/")


# Sensible starting points. Not clever — just the four people actually ask for.
TEMPLATES: tuple[dict, ...] = (
    {
        "name": "Sort downloads by type",
        "matchers": [Matcher(Field.PATH, Comparison.CONTAINS, "Downloads")],
        "action": Action(ActionKind.MOVE, destination="{category}", create_missing=True),
    },
    {
        "name": "Date-prefix screenshots",
        "matchers": [Matcher(Field.NAME, Comparison.STARTS_WITH, "Screenshot")],
        "action": Action(ActionKind.RENAME, pattern="{date}_{stem}{ext}"),
    },
    {
        "name": "Archive large videos",
        "matchers": [
            Matcher(Field.EXTENSION, Comparison.IN, "mp4, mov, mkv"),
            Matcher(Field.SIZE, Comparison.GREATER_THAN, "1 GB"),
        ],
        "action": Action(ActionKind.MOVE, destination="Video/Large"),
    },
    {
        "name": "Flag files untouched for a year",
        "matchers": [Matcher(Field.MODIFIED, Comparison.OLDER_THAN_DAYS, "365")],
        "action": Action(ActionKind.TAG, tag="stale"),
    },
    {
        "name": "Kebab-case everything",
        "matchers": [Matcher(Field.NAME, Comparison.MATCHES, r"[A-Z]")],
        "action": Action(ActionKind.RENAME, pattern="{case:kebab}{ext}"),
    },
)
