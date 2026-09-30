# Architecture

Short version: `core` does the work and knows nothing about Qt, `ui` draws
pictures and does no work, and only one module is allowed to touch the disk.

```
                ┌──────────────────────────────────────────┐
   ui/          │  main_window   owns folder, scan, rules  │
                │  ├── pages/    one per tab                │
                │  ├── widgets   table model, formatting    │
                │  └── theme     the only stylesheet        │
                └───────────────────┬──────────────────────┘
                                    │ calls, passes results
                ┌───────────────────▼──────────────────────┐
   core/        │  scanner   duplicates   renamer   rules  │
                │  cleanup   settings     journal          │
                │                                          │
                │  operations.py  ← the only module that   │
                │                   writes to the disk     │
                └───────────────────┬──────────────────────┘
                                    │
                              the filesystem
```

## Why the split

`core` has no Qt imports. That is not tidiness for its own sake — it means the
whole engine runs under plain `pytest` with no display, no event loop and no
windowing system, and the suite finishes in under a second.

The cost is passing plain data across the boundary: frozen dataclasses from
`core/models.py`, never Qt objects. In exchange, the parts that can lose your
files are testable against real temporary directories.

## Planning versus doing

The most important structural decision, and it runs through everything.

```python
plan = engine.plan(files, root=root)   # pure. touches nothing.
result = operations.apply_rule_plan(plan.changes, journal, root=root)
```

`plan_rename`, `plan_find_replace` and `RuleEngine.plan` are pure functions.
They read, they decide, and they return both what they would do *and why they
skipped each thing they did not do*. Nothing is written until a caller hands an
approved plan to `operations`.

This is not only about safety. It is what lets the UI show a real preview, and
it is what catches collisions — a batch rename that would have two files
resolving to the same name is caught before the first rename, not halfway
through.

`core/operations.py` is the only module permitted to mutate the filesystem. If
you are adding a feature that moves files, it belongs there, not in the page
that triggers it.

## The journal

Every change is written to SQLite before it happens.

```python
entry = journal.record(kind, summary, {"from": ..., "to": ...}, batch=batch)
os.replace(source, destination)
```

**Journal first, then act.** The ordering is deliberate:

| Order | Crash between the two | Result |
|---|---|---|
| journal → act | yes | a record of something that did not happen. Recoverable. |
| act → journal | yes | a moved file with no way back. Not recoverable. |

The wrong order is the one that loses data, so it is not the one used.

A change that fails is marked undone rather than left behind, so the journal
never claims a move it did not perform.

The journal lives in the platform data directory, **never inside the folder
being organised**. That folder is the thing being moved around; storing the log
of its own rearrangement inside it would mean tidying the folder could destroy
the record of what happened.

## Undo

Undo replays a batch in reverse order, newest change first, because a rename
that moved a file out of a folder has to be reversed after whatever moved it
*into* that folder.

```python
reverted, errors = journal.undo_batch(batch_id)
```

Failures are collected and reported. An entry that cannot be reversed is still
marked handled — a file the user has since moved by hand is a permanent
condition, and retrying it on every undo would be noise.

## Quarantine

Removing a file means moving it to `_FileFlow Quarantine/` inside the open
folder. Not deleting it.

```python
destination = quarantine_root / f"{date}_{safe_name}"
```

The flat, date-prefixed naming means two files called `report.pdf` from different
folders cannot overwrite each other in quarantine.

`purge_quarantine` is the only function in the codebase that calls `unlink`. It
resolves each path and refuses anything not under the quarantine directory, so a
bug elsewhere cannot turn "remove from the view" into "erase from disk".

## Scanning

`os.scandir` rather than `pathlib.rglob`, for three reasons:

- `scandir` is lazy and gives `is_dir` without a second stat
- the walk is iterative, so a deep tree cannot overflow the stack
- a permission error on one subtree is caught and recorded, and the walk
  continues, rather than abandoning 40,000 files because of one locked folder

Scans run on a worker thread. The UI polls with a **generation counter**: each
`rescan()` increments it, and a poll whose generation is stale returns without
touching state. Without that, switching folders mid-scan leaves `root` pointing
at the new folder while `scan` holds results from the old one.

## Duplicate detection

Two passes, and the order is the whole trick:

1. Group by exact byte size. Free — no file is read.
2. Hash with SHA-256, in 1 MiB chunks, only within groups that had a collision.

On a typical folder step 2 reads a small fraction of the files. Hashing is
streamed so a 4 GB video does not become 4 GB of resident memory.

Files over 8 GB are skipped and the skip is reported, not hidden.

The oldest copy in a group is kept. If two copies differ in any way, the newer
one was edited more recently, and that is the one people usually want.

## Failure handling

A batch that fails on the third of fifty files does the other forty-nine.

`OperationResult` carries counts and a tuple of error strings. Nothing is raised
out of a per-file loop, because a single locked file should not abandon the
batch — and because raising would lose the record of the forty-nine that worked.

Errors are shown to the user, not logged and forgotten.
