"""The undo journal.

Every filesystem change FileFlow makes is written here first, with enough
information to reverse it. The journal is a SQLite file in the user's data
directory, not in the folder being organised, because the folder being
organised is exactly what gets moved around.

Deliberately not a trash bin. Restoring means putting a file back where it was,
which requires having recorded where that was. Anything FileFlow removes goes
to a quarantine folder and is recorded, so undo is a move rather than a
recovery from the Recycle Bin.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

SCHEMA_VERSION = 1
QUARANTINE_DIR = "_FileFlow Quarantine"


class OperationKind(StrEnum):
    MOVE = "move"
    RENAME = "rename"
    QUARANTINE = "quarantine"
    RESTORE = "restore"


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """One reversible change. `payload` holds the kind-specific detail."""

    id: str
    kind: OperationKind
    timestamp: float
    summary: str
    payload: dict
    undone: bool = False
    batch: str | None = None

    @property
    def when(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)

    def paths(self) -> list[Path]:
        """Every path this entry touched, for the UI to display."""
        found: list[Path] = []
        for value in self.payload.values():
            if isinstance(value, str):
                found.append(Path(value))
            elif isinstance(value, (list, tuple)):
                found.extend(Path(v) for v in value)
        return found


class Journal:
    """Append-only log of reversible operations."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._connection: sqlite3.Connection | None = None
        self._connect()

    # -- lifecycle ---------------------------------------------------------

    def _connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.db_path, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._migrate()

    def _migrate(self) -> None:
        assert self._connection is not None
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS entries (
                id        TEXT PRIMARY KEY,
                kind      TEXT NOT NULL,
                timestamp REAL NOT NULL,
                summary   TEXT NOT NULL,
                payload   TEXT NOT NULL,
                undone    INTEGER NOT NULL DEFAULT 0,
                batch     TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_entries_timestamp
                ON entries (timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_entries_batch
                ON entries (batch);
            """
        )
        self._connection.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> Journal:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- writing -----------------------------------------------------------

    def record(
        self,
        kind: OperationKind,
        summary: str,
        payload: dict,
        *,
        batch: str | None = None,
        entry_id: str | None = None,
    ) -> str:
        assert self._connection is not None
        identifier = entry_id or uuid.uuid4().hex[:16]

        self._connection.execute(
            """
            INSERT INTO entries (id, kind, timestamp, summary, payload, undone, batch)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            """,
            (
                identifier,
                kind.value,
                time.time(),
                summary,
                json.dumps(payload, default=str),
                batch,
            ),
        )
        return identifier

    def new_batch(self) -> str:
        return uuid.uuid4().hex[:12]

    # -- reading -----------------------------------------------------------

    def recent(self, *, limit: int = 100, include_undone: bool = False) -> list[JournalEntry]:
        assert self._connection is not None
        query = "SELECT * FROM entries"
        if not include_undone:
            query += " WHERE undone = 0"
        query += " ORDER BY timestamp DESC LIMIT ?"

        return [self._row_to_entry(row) for row in self._connection.execute(query, (limit,))]

    def batches(self, *, limit: int = 50) -> list[tuple[str, int, float, str]]:
        """One row per batch: (batch_id, change_count, timestamp, first_summary).
        Used for 'Undo last action' in the UI."""
        assert self._connection is not None
        rows = self._connection.execute(
            """
            SELECT batch, COUNT(*) AS n, MAX(timestamp) AS ts, MIN(summary) AS label
            FROM entries
            WHERE undone = 0 AND batch IS NOT NULL
            GROUP BY batch
            ORDER BY ts DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [(r["batch"], r["n"], r["ts"], r["label"]) for r in rows]

    def get(self, entry_id: str) -> JournalEntry | None:
        assert self._connection is not None
        row = self._connection.execute(
            "SELECT * FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def entries_for_batch(self, batch: str) -> list[JournalEntry]:
        """Oldest first. Undo replays in reverse chronological order."""
        assert self._connection is not None
        rows = self._connection.execute(
            "SELECT * FROM entries WHERE batch = ? AND undone = 0 ORDER BY timestamp ASC",
            (batch,),
        )
        return [self._row_to_entry(row) for row in rows]

    def _row_to_entry(self, row: sqlite3.Row) -> JournalEntry:
        try:
            payload = json.loads(row["payload"])
        except json.JSONDecodeError:
            payload = {}

        return JournalEntry(
            id=row["id"],
            kind=OperationKind(row["kind"]),
            timestamp=row["timestamp"],
            summary=row["summary"],
            payload=payload,
            undone=bool(row["undone"]),
            batch=row["batch"],
        )

    def mark_undone(self, entry_ids: Iterable[str]) -> None:
        assert self._connection is not None
        ids = list(entry_ids)
        if not ids:
            return
        placeholders = ",".join("?" * len(ids))
        self._connection.execute(
            f"UPDATE entries SET undone = 1 WHERE id IN ({placeholders})", ids
        )

    # -- reversing ---------------------------------------------------------

    def undo_batch(self, batch: str) -> tuple[int, list[str]]:
        """Reverse every change in a batch. Returns (reverted, errors).

        Entries that fail to reverse stay marked as done rather than being
        retried forever: a file the user has since moved by hand is a permanent
        condition, not a transient one.
        """
        entries = self.entries_for_batch(batch)
        if not entries:
            return 0, ["nothing to undo"]

        reverted: list[str] = []
        errors: list[str] = []
        ids: list[str] = []

        for entry in reversed(entries):  # newest first
            try:
                self._reverse(entry)
                ids.append(entry.id)
                reverted.append(entry.summary)
            except OSError as error:
                errors.append(f"{entry.summary}: {error.strerror or error}")
                ids.append(entry.id)  # do not leave it claiming to be undoable

        self.mark_undone(ids)
        return len(reverted), errors

    def undo_entry(self, entry_id: str) -> None:
        entry = self.get(entry_id)
        if entry is None:
            raise KeyError(f"no journal entry {entry_id}")
        self._reverse(entry)
        self.mark_undone([entry_id])

    def _reverse(self, entry: JournalEntry) -> None:
        # Move, rename and quarantine are all "put it back where it was"; only
        # the wording in the history differs. They share a payload shape.
        match entry.kind:
            case OperationKind.MOVE | OperationKind.RENAME | OperationKind.QUARANTINE:
                source = Path(entry.payload["from"])
                destination = Path(entry.payload["to"])
                _ensure_parent(source)
                os.rename(destination, source)
            case _:
                raise ValueError(f"cannot reverse {entry.kind}")

    # -- maintenance -------------------------------------------------------

    def prune(self, *, keep_days: int = 30) -> int:
        """Drop entries old enough that reversing them is no longer realistic."""
        assert self._connection is not None
        cutoff = time.time() - keep_days * 86_400
        cursor = self._connection.execute("DELETE FROM entries WHERE timestamp < ?", (cutoff,))
        return cursor.rowcount

    def count(self, *, include_undone: bool = False) -> int:
        assert self._connection is not None
        query = "SELECT COUNT(*) FROM entries"
        if not include_undone:
            query += " WHERE undone = 0"
        return self._connection.execute(query).fetchone()[0]

    def __iter__(self) -> Iterator[JournalEntry]:
        return iter(self.recent(limit=1000, include_undone=True))


def _ensure_parent(path: Path) -> None:
    parent = path.parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


def default_journal_path() -> Path:
    """Where the journal lives, per-platform.

    Never inside the folder being organised: that folder is subject to being
    moved, renamed, or emptied by the very operations we are recording.
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))

    return base / "FileFlow" / "journal.db"


def data_dir() -> Path:
    path = default_journal_path().parent
    path.mkdir(parents=True, exist_ok=True)
    return path
