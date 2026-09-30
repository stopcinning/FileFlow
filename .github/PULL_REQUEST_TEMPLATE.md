## What this changes

<!-- One or two sentences. What does this do, and why? -->

## Why

<!-- The problem it solves. If it fixes an issue, say "Fixes #123". -->

## Safety

- [ ] Nothing deletes files; anything removed goes to the quarantine folder
- [ ] Every filesystem change is journalled before it happens
- [ ] Partial failures are reported per file, not raised out of a batch

## Checks

- [ ] `python -m pytest` passes
- [ ] `python -m ruff check src tests scripts` passes
- [ ] `python tests/smoke_ui.py` passes, if this touched `ui/`
- [ ] `python tests/screenshot.py` re-run, if this changed the UI visibly

## Notes

<!-- Anything a reviewer would want to know. Screenshots, before/after, the
     reasoning behind a trade-off. -->
