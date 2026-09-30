# Contributing

Pull requests are welcome, including small ones.

## Getting set up

Needs Python 3.11 or newer.

```bash
git clone https://github.com/stopcinning/FileFlow.git
cd FileFlow
python -m venv .venv
.venv\Scripts\activate          # . .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"
```

Run it:

```bash
python -m fileflow
python -m fileflow path\to\folder
```

Check your work before opening a PR:

```bash
python -m pytest
python -m ruff check src tests scripts
```

Both need to pass. They run in about a second.

## Layout

```
src/fileflow/
  core/            No Qt imports anywhere in here. Pure filesystem logic.
    models.py        FileEntry, Category, ScanResult, DuplicateGroup
    categories.py    extension -> category table
    scanner.py       recursive walk, cancellable, survives partial failure
    duplicates.py    size bucketing, then streamed SHA-256
    renamer.py       pattern expansion and collision-safe planning
    cleanup.py       classifying what could be reclaimed
    rules.py         matchers, actions, and pure planning
    journal.py       SQLite undo log
    operations.py    the only module that mutates the filesystem
    settings.py      persisted preferences and rules
  ui/              Everything Qt lives here.
    theme.py          one stylesheet, dark and light
    widgets.py        shared widgets and the file table model
    main_window.py    state that more than one page needs
    pages/            one module per tab
```

The split matters: `core` can be tested without a display, which is why the
test suite runs in under a second and needs no windowing system.

## Two rules

These are not negotiable, and a PR that breaks either will be asked to change.

**1. Nothing deletes.**

There is exactly one function in the codebase that calls `unlink`, and it is
`purge_quarantine`, which refuses to touch any path outside the quarantine
directory. Everything else moves files. If you need to remove something for a
user, move it to `_FileFlow Quarantine/` and write a journal entry.

**2. Everything is journalled.**

Any function in `core/operations.py` that changes a file must write a journal
entry first, and the entry must contain enough to reverse the change. The
ordering is deliberate — journal, then act. A crash between the two leaves a
reversible record of something that did not happen, which is recoverable. The
other order leaves a moved file with no way back.

## Conventions

- Type hints on public functions. `core` is importable and typed; `ui` is looser
  because Qt's signals make precise annotations awkward.
- Comments should explain *why*, not restate the code. If a line needs a
  comment to say what it does, rename something instead.
- Docstrings on modules and non-obvious functions. Skip them on `__init__`
  methods that are obviously initialisers.
- Errors that affect one file are collected and reported, not raised. A batch
  that fails on the third of fifty files should still do the other forty-nine.
- No new runtime dependencies without discussion. PySide6 is the only one.

## Tests

`tests/test_engine.py` runs against real temporary directories — real files,
real renames, real undos. Please keep it that way. A file organiser whose undo
journal is only tested against mocks is not tested at all.

Two scripts are not part of the pytest run:

- `tests/smoke_ui.py` builds the real window headless and drives it. Run it
  after changing anything in `ui/`.
- `tests/screenshot.py` regenerates the README images. Run it when the UI
  changes visibly.

Both need a real Qt platform. Set `FILEFLOW_OFFSCREEN=1` for the offscreen
plugin, but note it exposes no fonts on Windows, so screenshots come out blank.

## Reporting bugs

Include your Windows version, what you expected, what happened, and the
relevant part of `fileflow.log` from your data folder if there is one. The log
is at `%APPDATA%\FileFlow\fileflow.log` on Windows.

If a file was moved somewhere unexpected, say so in the issue. That is a bug
worth prioritising over a crash.
