# Rules reference

A rule is a set of **conditions** and one **action**. A file is affected by a
rule only when *every* condition is true.

Rules are evaluated in priority order, lowest number first. By default a file is
affected by the first rule that matches it, and later rules are not consulted.

## Conditions

Each condition tests one field with one comparison.

### Fields

| Field | Matches against |
|---|---|
| Name | the filename, extension included |
| Extension | the extension only, no dot, lowercased |
| Path | the full path on disk |
| Size | in bytes |
| Last modified | how long ago it was last written |

### Comparisons

Not every comparison is offered for every field. The combinations that make
sense:

| Field | Available |
|---|---|
| Name | is, is not, contains, starts with, ends with, matches regex |
| Extension | is, is one of |
| Size | is larger than, is smaller than, is exactly |
| Last modified | days ago or more, days ago or fewer |
| Path | contains, starts with |

Comparisons are case-insensitive. "pdf" and "PDF" are the same thing.

### Values

**Sizes** accept units. All of these mean the same thing:

```
500
500B
500 KB
0.5MB
1.5 GB
```

Units are binary — 1 KB is 1024 bytes — so they match what Windows reports.

**"is one of"** takes a comma-separated list:

```
pdf, docx, txt
```

Newlines work too, if you are editing `rules.json` by hand.

**Regex** is Python's `re` module, case-insensitive. Invalid patterns make that
condition always false rather than raising, so a typo quietly stops the rule
matching. Worth a second look if a rule seems inert.

**Modified dates** are a number of days, not a date:

```
90       older than 90 days
365      older than a year
```

## Actions

| Action | What it does |
|---|---|
| Move | moves the file to a destination folder |
| Rename | renames it in place |
| Rename and move | both, as a single reversible step |
| Tag | records a label in the activity log. Touches nothing on disk. |

A move creates its destination folder if it does not exist.

## Tokens

### In rename patterns

| Token | Becomes |
|---|---|
| `{name}` | `report final.docx` |
| `{stem}` | `report final` |
| `{ext}` | `.docx` — includes the dot, so `{stem}{ext}` round-trips |
| `{parent}` | name of the containing folder |
| `{date}` | `2026-09-30` |
| `{year}` `{month}` `{day}` | `2026`, `09`, `30` |
| `{time}` | `2214` |
| `{index}` | position in the batch, zero-padded to 3: `001` |
| `{index:5}` | the same, zero-padded to 5 |
| `{case:lower}` | the stem, lowercased |
| `{case:upper}` | the stem, uppercased |
| `{case:kebab}` | `report-final` |
| `{case:snake}` | `report_final` |
| `{case:title}` | `Report Final` |

Dates come from the file's **last modified** time, not from anything parsed out
of its name. `{date}` on a file last written in March gives March, whatever its
filename says.

`{case:…}` transforms the stem only, never the extension. Lowercasing someone's
`.DOCX` reads as a bug, and it is one.

Write `{{` and `}}` for literal braces.

### In move destinations

| Token | Becomes |
|---|---|
| `{category}` | `Documents`, `Images`, `Video`, … |
| `{year}` `{month}` `{day}` | parts of the last modified date |
| `{name}` | the filename without its extension |
| `{parent}` | name of the containing folder |

Destinations are relative to the folder you opened, not to the file. A rule with
destination `Archive/{year}` puts everything in `Archive/2026/`, wherever the
file started.

## Worked examples

**File screenshots as they arrive**

```
when  name starts with "Screenshot"
then  rename to {date}_{stem}{ext}

Screenshot 2026-09-30 at 09.18.42.png
  ->  2026-09-30_Screenshot 2026-09-30 at 09.18.42.png
```

**Sort downloads, leave everything else alone**

```
when  path contains "Downloads"
then  move to {category}

invoice.pdf  ->  Downloads/Documents/invoice.pdf
clip.mp4     ->  Downloads/Video/clip.mp4
```

**Big videos somewhere sensible**

```
when  extension is one of "mp4, mov, mkv"
and   size is larger than 1 GB
then  move to Video/Large
```

Both conditions must hold. A 200 MB `.mp4` does not move.

**Consistent names across a folder**

```
when  name matches "[A-Z]"
then  rename to {case:kebab}{ext}

Q3 Financial Report v4.pdf  ->  q3-financial-report-v4.pdf
notes.txt                   ->  untouched, already matches
```

## Previewing

**Preview rules** shows every file that would change, its current name, and
where it would go. Nothing moves until you press Apply.

Files that no rule matches are counted in the summary but not listed. If you
expected a match and did not get one, the usual cause is the condition
comparing against the extension with a dot (`name is ".pdf"` rather than
`extension is "pdf"`), or a regex that is not matching the way you expect.

## Storing rules

Rules live in `rules.json` in your data folder and are readable. The format is
one object per rule:

```json
[
  {
    "id": "a1b2c3d4e5f6",
    "name": "Sort downloads by type",
    "enabled": true,
    "priority": 10,
    "run_count": 1284,
    "last_run": "2026-09-30T14:21:00",
    "matchers": [
      { "field": "path", "comparison": "contains", "value": "Downloads" }
    ],
    "action": {
      "kind": "move",
      "destination": "{category}",
      "pattern": "",
      "tag": "",
      "create_missing": true
    }
  }
]
```

A rule that fails to parse is skipped rather than stopping the rest from
loading. The log says which one and why.
