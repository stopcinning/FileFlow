# Roadmap

Where this is going, and what is deliberately not.

Ordered roughly by how much I expect to work on each. Nothing here is
promised — see [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for what is actually broken
today.

## Next

### Bulk rename dialog

The rename engine works and is tested, but it is only reachable through rules.
A dialog with a pattern field, a live before/after table, and a choice of the
tokens as buttons would make it usable without writing a rule.

This is the most-requested thing from people who have seen the app, and the
largest gap between what the engine can do and what the UI exposes.

### Clean up the quarantine folder

`purge_quarantine` exists and is tested, including the check that refuses to
delete outside the quarantine directory, but nothing in the UI calls it. Needs
a view of what is in quarantine, how much space it is holding, and a confirm
that says plainly that this step cannot be undone.

### Folder templates

Save a set of rules as a named profile and apply one to a folder in a click:
"Photo workflow", "Client handover", "Invoice archive". The rule format is
already JSON, so most of the work is the UI.

### Per-folder rule sets

Right now one rule list applies to whatever folder is open. A file in
`Downloads` and a file in `Photos` want different treatment, and a rule that
moves all images into `Images/Screenshots` should not fire on a photo.

### Watch a folder

Apply rules to files as they land, using the OS filesystem notification API
rather than polling. Genuinely useful, and a good way to get burned: a rule with
a bad destination would run unattended. Would need a per-rule opt-in and a hard
cap on how much it may move per hour.

## Later

### Similar-image detection

Currently duplicates must be byte-identical. Two exports of the same photo are
not, and they are usually what is actually wasting space. Perceptual hashing
would find them. This is a much larger change than it sounds — a false positive
here means suggesting you delete a photo you wanted.

### Export the activity log

CSV and JSON export of the journal, for people who want to see what happened
across a long history rather than the last screenful.

### macOS build

The code is written for it and the packaging is not. Needs someone with a Mac
and a signing identity.

### Rules DSL

A text format for rules, so a set can be committed to a repository alongside the
files it organises. The JSON is already close; the question is whether a
hand-written format is worth it over YAML.

### Undo across sessions, more safely

Undo already survives a restart. What it does not do is notice that the world
changed underneath it. Recording a cheap fingerprint per entry — size and
mtime — would let undo say "this file is not the one I moved" instead of
attempting the reversal and failing.

## Not planned

- **Cloud sync or accounts.** A tool that reads your disk should not need a
  login, and should not need the network at all.
- **Deleting files directly.** The quarantine folder exists so that "remove"
  never means "erase". Purging it is a separate, explicit action.
- **A plugin system.** The rule engine covers the cases I have come across.
  Adding an extension point would mean maintaining a stability guarantee for
  code I have not written.
- **Content-based rules.** Matching on what is inside a file would mean reading
  everything during a preview. See the note in KNOWN_ISSUES.

## Contributing

If something here looks like the wrong priority, open an issue and say why.
The [CONTRIBUTING.md](CONTRIBUTING.md) covers the two rules that constrain
changes: nothing deletes, everything is journalled.
