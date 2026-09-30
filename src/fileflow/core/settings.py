"""Persisted settings and rule storage.

A single JSON file in the platform data directory. Not a database: settings are
small, a human should be able to read them, and a corrupt file should be
recoverable by deleting it rather than by running a migration.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .journal import data_dir
from .rules import TEMPLATES, Action, ActionKind, Comparison, Field, Matcher, Rule

log = logging.getLogger("fileflow.settings")

SETTINGS_FILE = "settings.json"
RULES_FILE = "rules.json"
SCHEMA_VERSION = 1


@dataclass(slots=True)
class Settings:
    """User preferences. Every field has a default, so a missing or partial
    file still loads."""

    schema_version: int = SCHEMA_VERSION

    # Scanning
    include_hidden: bool = False
    skip_build_dirs: bool = False

    # Cleanup
    stale_days: int = 90
    large_file_mb: int = 1024

    # Behaviour
    confirm_before_quarantine: bool = True
    journal_retention_days: int = 30

    # Appearance
    theme: str = "dark"  # dark | light

    # Session
    last_folder: str = ""
    window_geometry: str = ""
    window_state: str = ""

    recent_folders: list[str] = field(default_factory=list)

    def remember_folder(self, path: Path, *, limit: int = 8) -> None:
        resolved = str(path)
        self.recent_folders = [resolved, *[f for f in self.recent_folders if f != resolved]][:limit]
        self.last_folder = resolved


def _settings_path() -> Path:
    return data_dir() / SETTINGS_FILE


def _rules_path() -> Path:
    return data_dir() / RULES_FILE


def load_settings() -> Settings:
    path = _settings_path()
    if not path.exists():
        return Settings()

    try:
        raw = json.loads(path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        log.warning("settings unreadable, using defaults: %s", error)
        return Settings()

    known = set(Settings.__dataclass_fields__)
    filtered = {k: v for k, v in raw.items() if k in known}

    try:
        return Settings(**filtered)
    except (TypeError, ValueError) as error:
        log.warning("settings invalid, using defaults: %s", error)
        return Settings()


def save_settings(settings: Settings) -> bool:
    path = _settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(settings), indent=2), "utf-8")
        return True
    except OSError as error:
        log.error("could not save settings: %s", error)
        return False


# -- rules ----------------------------------------------------------------


def _matcher_to_dict(matcher: Matcher) -> dict[str, str]:
    return {
        "field": matcher.field.value,
        "comparison": matcher.comparison.value,
        "value": matcher.value,
    }


def _matcher_from_dict(raw: dict[str, Any]) -> Matcher:
    return Matcher(
        field=Field(raw["field"]),
        comparison=Comparison(raw["comparison"]),
        value=str(raw.get("value", "")),
    )


def _action_to_dict(action: Action) -> dict[str, Any]:
    return {
        "kind": action.kind.value,
        "destination": action.destination,
        "pattern": action.pattern,
        "tag": action.tag,
        "create_missing": action.create_missing,
    }


def _action_from_dict(raw: dict[str, Any]) -> Action:
    return Action(
        kind=ActionKind(raw.get("kind", "move")),
        destination=raw.get("destination", ""),
        pattern=raw.get("pattern", ""),
        tag=raw.get("tag", ""),
        create_missing=bool(raw.get("create_missing", True)),
    )


def rule_to_dict(rule: Rule) -> dict[str, Any]:
    return {
        "id": rule.id,
        "name": rule.name,
        "enabled": rule.enabled,
        "priority": rule.priority,
        "run_count": rule.run_count,
        "last_run": rule.last_run.isoformat() if rule.last_run else None,
        "matchers": [_matcher_to_dict(m) for m in rule.matchers],
        "action": _action_to_dict(rule.action),
    }


def rule_from_dict(raw: dict[str, Any]) -> Rule:
    """Rebuild a rule, tolerating anything unrecognised.

    A rule that fails to parse is skipped rather than aborting the load: losing
    one rule is recoverable, refusing to start is not.
    """
    last_run = raw.get("last_run")
    return Rule(
        id=raw.get("id") or uuid.uuid4().hex[:12],
        name=raw.get("name", "Untitled rule"),
        enabled=bool(raw.get("enabled", True)),
        priority=int(raw.get("priority", 100)),
        run_count=int(raw.get("run_count", 0)),
        last_run=datetime.fromisoformat(last_run) if last_run else None,
        matchers=[_matcher_from_dict(m) for m in raw.get("matchers", [])],
        action=_action_from_dict(raw.get("action", {})),
    )


def load_rules() -> list[Rule]:
    path = _rules_path()
    if not path.exists():
        return default_rules()

    try:
        raw = json.loads(path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        log.warning("rules unreadable, restoring defaults: %s", error)
        return default_rules()

    if not isinstance(raw, list):
        return default_rules()

    rules: list[Rule] = []
    for item in raw:
        try:
            rules.append(rule_from_dict(item))
        except (KeyError, TypeError, ValueError):
            log.warning("skipping malformed rule %r", item.get("name") if isinstance(item, dict) else item)
            continue

    return rules or default_rules()


def save_rules(rules: list[Rule]) -> bool:
    path = _rules_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([rule_to_dict(r) for r in rules], indent=2), "utf-8")
        return True
    except OSError as error:
        log.error("could not save rules: %s", error)
        return False


def default_rules() -> list[Rule]:
    """Shipped starting points, rebuilt from TEMPLATES so the two cannot drift."""
    return [
        Rule(
            name=template["name"],
            matchers=list(template["matchers"]),
            action=template["action"],
            priority=index * 10 + 10,
        )
        for index, template in enumerate(TEMPLATES)
        if index < 2  # only the two that are useful out of the box
    ]
