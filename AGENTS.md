# AGENTS.md

Guidance for AI coding agents working on this repository. Human contributors
should read [CONTRIBUTING.md](CONTRIBUTING.md) instead — it is the real
document. This file is a summary for agents.

## What this is

FileFlow is a Windows desktop application for organising folders. Python, PySide6,
no network access, no accounts, no telemetry. It reads a real folder on disk and
moves files in it.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Run: `python -m fileflow` or `python -m fileflow path\to\folder`

## Before finishing any change

```bash
python -m pytest
python -m ruff check src tests scripts
```

If you touched `ui/`, also run `python tests/smoke_ui.py`. If you changed
anything visible, re-run `python tests/screenshot.py` to keep the README images
current.

## Layout

- `src/fileflow/core/` — all filesystem logic. **No Qt imports may appear here.**
  This is what makes the engine testable without a display.
- `src/fileflow/ui/` — all Qt. One module per tab under `ui/pages/`.
- `src/fileflow/ui/theme.py` — the single stylesheet. Add colours there, not
  inline.
- `tests/test_engine.py` — real temporary directories, real files, real undos.
- `packaging/` — PyInstaller spec and Windows version resource.
- `scripts/build.py` — builds the executable.

## Two rules that constrain everything

1. **Nothing deletes.** The only `unlink` call in the codebase is in
   `operations.purge_quarantine`, which refuses any path outside the quarantine
   directory. Removing something for the user means moving it to
   `_FileFlow Quarantine/`.
2. **Everything is journalled.** Any change to the filesystem writes a SQLite
   journal entry *before* acting, containing enough to reverse it. Journal first,
   then act — a crash in between leaves a recoverable record rather than an
   unrecoverable change.

## Conventions

- Comments explain *why*. Do not restate the code.
- Per-file errors are collected and reported, never raised. One bad file must not
  abandon the other forty-nine in a batch.
- Planning is pure. `plan_rename` and `RuleEngine.plan` do not touch the disk and
  return the reasons anything was skipped. Only `core/operations.py` writes.
- Match surrounding style. The codebase uses `StrEnum`, `match` statements,
  frozen dataclasses with `slots=True`, and full type hints on core functions.
- No new runtime dependencies without raising it first. PySide6 is the only one.
