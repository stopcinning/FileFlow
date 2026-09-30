# Known issues

Genuine limitations, not a wish list. Ordered by how likely you are to hit them.

## Windows only

The application is built and tested on Windows. The core is plain Python and
`pathlib`, and the macOS and Linux code paths are written but untested —
`reveal_in_explorer` falls back to `open` and `xdg-open`, and the release
pipeline is Windows-only. Treat macOS and Linux as unsupported until there is a
release for them.

## Files over 8 GB are skipped by duplicate detection

Duplicate detection hashes file contents, read in 1 MiB chunks. Files larger
than 8 GB are not hashed, and the count of skipped files is reported in the
Duplicates tab rather than hidden. The reasoning: a folder containing two 12 GB
ISOs is rare, and making everyone wait through a hash of both to find out is
worse than saying so.

Raise `MAX_HASH_BYTES` in `core/duplicates.py` if you want the limit gone. There
is a test for the skip path, so changing it will tell you what broke.

## Scanning stops at 250,000 files

A hard cap, to stop a runaway walk on a symlink loop or a pathological tree. The
status bar says so explicitly when it is hit, and the results are partial rather
than silently wrong. Raise `MAX_ENTRIES` in `core/scanner.py` if you need more.

## Undo is best-effort

Undo puts files back where they were. If you have since moved or deleted a file
by hand, that entry cannot be reversed — undo reports the failure rather than
silently marking itself done, but it cannot invent the missing file.

Entries that fail to reverse are still marked as handled, so they are not
retried on every undo. If a file reappears later, the record of it is gone.

## The journal grows

Every change is an insert into a SQLite database in your app data folder. It is
small — a few hundred bytes per operation — but it is never pruned
automatically. **Activity → Prune old entries** drops entries past the
retention window, which also makes those changes permanently unundoable.

## Rules match on the file's own metadata, not its contents

There is no content-based matching. A rule cannot ask "does this PDF contain an
invoice", only things like name, extension, size and date. This is deliberate:
content matching would mean reading every file during a preview.

## No undo history in the rules preview

The rules preview is read-only. There is no "apply, watch, undo" loop inside the
dialog — you either apply the whole plan or none of it. Undo after applying goes
through the Activity tab, one batch at a time.

## The executable is unsigned

Windows SmartScreen warns on first run. Click *More info* → *Run anyway*. There
is no code-signing certificate behind it, so the warning cannot be suppressed
honestly.

## Build output is scanned by default

`node_modules`, `dist`, `.venv` and similar directories are walked unless you
turn on **Settings → Skip dependency and build folders**. That default is
deliberate: the cleanup suggestions cannot offer to reclaim 3 GB of
`node_modules` if the scan never looks inside it. The trade-off is slower scans
on large projects.

## Single-folder at a time

There is no multi-folder or whole-drive mode, and no scheduled or automatic
runs. You point it at one folder and press the button.

## Not tested on a fresh Windows install

Development was done on one machine. The application has no installer, so
registry and shell-integration issues do not apply, but a first run on a clean
profile is untested.

## Screenshots

The images in the README are generated from the current code by
`tests/screenshot.py`, so they cannot drift out of date — but they show a
synthetic folder, not real data.
