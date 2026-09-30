# Changelog

All notable changes to FileFlow are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [0.1.0] — 2026-09-30

First public release. This is a complete rewrite: the previous version was a
browser app that displayed hardcoded numbers and could not touch a real disk.

### Added

- Recursive folder scan with size, type and modified time, filtering by name,
  folder and type
- Duplicate detection: groups by exact size, then compares SHA-256 of contents
  for files that share one. The oldest copy in a group is kept
- Separate detection of name variants (`report (1).pdf` / `report (2).pdf`) that
  differ in content, since the right response to those is rename, not delete
- Bulk rename with pattern tokens (`{date}`, `{stem}`, `{index:3}`,
  `{case:kebab}`, …) and find-and-replace, both planned before anything is
  written
- Collision detection on rename: a batch never overwrites an existing file, and
  two files in the same batch never resolve to the same name
- Rules engine: conditions on name, extension, path, size and modified date, with
  move, rename, combined and tag actions. Always previewed before applying
- Cleanup suggestions: temporary files, build directories, files untouched for
  N days, files over a size threshold, and stale archives
- Undo journal in SQLite, written before each change, with per-batch reversal
- Quarantine folder instead of deletion, so undo is a move rather than a rescue
- Activity view listing every batch, selectable for undo
- Backup a selection to another folder (copy, not move)
- Dark and light themes
- Command-line entry point: `fileflow [folder]`
- Windows executable via PyInstaller

### Safety

- Nothing is deleted while organising. "Remove" moves to `_FileFlow Quarantine/`
- The journal is written to the app data directory, never inside the folder
  being organised
- Purging the quarantine folder refuses to delete any path outside it
- Rules and renames are planned as pure functions and previewed before applying
- Partial failures are reported per file rather than aborting a batch

### Known limitations

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

[Unreleased]: https://github.com/stopcinning/FileFlow/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/stopcinning/FileFlow/releases/tag/v0.1.0
