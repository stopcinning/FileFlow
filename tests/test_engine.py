"""End-to-end checks against a real temporary directory.

These deliberately touch the filesystem. A file organiser whose undo journal is
only tested against mocks is not tested at all.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from fileflow.core import operations
from fileflow.core.cleanup import find_cleanup_candidates, find_stale_archives
from fileflow.core.duplicates import find_duplicates, find_name_variants
from fileflow.core.journal import Journal, OperationKind
from fileflow.core.models import Category
from fileflow.core.renamer import (
    expand_pattern,
    plan_find_replace,
    plan_rename,
    sanitise_name,
)
from fileflow.core.rules import (
    Action,
    ActionKind,
    Comparison,
    Field,
    Matcher,
    Rule,
    RuleEngine,
)
from fileflow.core.scanner import scan


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A small folder with duplicates, clutter and a subdirectory."""
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("hello")  # byte-identical to a.txt
    (tmp_path / "sub" / "c.txt").write_text("hello")  # identical, nested
    (tmp_path / "unique.txt").write_text("different content")
    (tmp_path / "build.log").write_text("x" * 100)
    (tmp_path / "cache.tmp").write_text("temp")
    (tmp_path / "photo.jpg").write_bytes(b"\xff\xd8\xff" + b"0" * 500)
    return tmp_path


@pytest.fixture
def journal(tmp_path_factory: pytest.TempPathFactory) -> Journal:
    # Deliberately outside the scanned tree: a journal.db inside tmp_path would
    # be picked up by the scanner and show up in size totals.
    path = tmp_path_factory.mktemp("journal") / "journal.db"
    with Journal(path) as j:
        yield j


# -- scanning -------------------------------------------------------------


def test_scan_finds_nested_files_and_skips_hidden(tree: Path) -> None:
    (tree / ".secret").write_text("hidden")

    result = scan(tree)

    names = {f.name for f in result.files}
    assert {"a.txt", "b.txt", "c.txt", "unique.txt", "photo.jpg"} <= names
    assert ".secret" not in names
    assert result.directories >= 1


def test_scan_categorises_by_extension(tree: Path) -> None:
    result = scan(tree)
    photo = next(f for f in result.files if f.name == "photo.jpg")
    assert photo.category is Category.IMAGES


def test_scan_survives_unreadable_subdirectory(tree: Path) -> None:
    locked = tree / "locked"
    locked.mkdir()
    (locked / "x.txt").write_text("nope")

    original_scandir = os.scandir

    def guarded(path, *args, **kwargs):
        if str(path).endswith("locked"):
            raise PermissionError(13, "Permission denied")
        return original_scandir(path, *args, **kwargs)

    os.scandir = guarded
    try:
        result = scan(tree)
    finally:
        os.scandir = original_scandir

    assert any("permission denied" in s.reason for s in result.skipped)
    assert any(f.name == "a.txt" for f in result.files), "scan should continue past failures"


# -- duplicates -----------------------------------------------------------


def test_duplicates_found_across_directories(tree: Path) -> None:
    result = scan(tree)
    report = find_duplicates(result.files)

    assert len(report.groups) == 1
    group = report.groups[0]
    assert {f.name for f in group.files} == {"a.txt", "b.txt", "c.txt"}
    assert group.keep.name == "a.txt", "oldest copy is kept"
    assert len(group.redundant) == 2
    assert report.reclaimable > 0


def test_unique_sizes_are_never_hashed(tree: Path) -> None:
    result = scan(tree)
    report = find_duplicates(result.files)

    # Only a.txt, b.txt, c.txt share a size; unique.txt and photo.jpg do not.
    assert report.hashed == 3


def test_empty_files_are_not_reported_as_duplicates(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "b.txt").write_text("")

    report = find_duplicates(scan(tmp_path).files)
    assert report.groups == ()


def test_name_variants_distinguished_from_true_duplicates(tmp_path: Path) -> None:
    (tmp_path / "report (1).pdf").write_text("a")
    (tmp_path / "report (2).pdf").write_text("bb")

    result = scan(tmp_path)
    assert find_duplicates(result.files).groups == ()

    variants = find_name_variants(result.files)
    assert len(variants) == 1
    assert len(variants[0].variants) == 2


# -- renaming -------------------------------------------------------------


def test_expand_pattern_tokens(tmp_path: Path) -> None:
    (tmp_path / "My Report.txt").write_text("x")
    entry = scan(tmp_path).files[0]

    assert expand_pattern("{stem}{ext}", entry) == "My Report.txt"
    assert expand_pattern("{case:kebab}{ext}", entry) == "my-report.txt"
    assert expand_pattern("{index:3}", entry, index=4) == "005"
    assert expand_pattern("{name} {name}", entry) == "My Report.txt My Report.txt"


def test_doubled_braces_are_literal(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")
    entry = scan(tmp_path).files[0]
    assert expand_pattern("{{name}}", entry) == "{name}"
    assert expand_pattern("{{{stem}}}", entry) == "{a}"


def test_sanitise_name_strips_illegal_characters() -> None:
    assert sanitise_name('a<b>c:d"e/f\\g|h?i*j') == "abcdefghij"
    assert sanitise_name("trailing dots...") == "trailing dots"
    assert sanitise_name("CON") == "_CON", "reserved Windows device name"
    assert sanitise_name("normal name.pdf") == "normal name.pdf"


def test_rename_skips_rather_than_overwriting(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("2")

    result = scan(tmp_path)
    # Every file becomes the same name: only one can win, the rest are skipped.
    plan = plan_rename(result.files, "same{ext}")

    assert len(plan.steps) == 1
    assert len(plan.skipped) == 1
    assert "already exists" in plan.skipped[0].reason or "batch" in plan.skipped[0].reason


def test_find_replace_leaves_extension_alone(tmp_path: Path) -> None:
    (tmp_path / "draft.txt").write_text("x")
    entry = scan(tmp_path).files[0]

    plan = plan_find_replace([entry], "draft", "final")
    assert plan.steps[0].after == "final.txt"


def test_find_replace_ignores_extension(tmp_path: Path) -> None:
    (tmp_path / "draft.txt").write_text("x")
    entry = scan(tmp_path).files[0]

    plan = plan_find_replace([entry], "txt", "md")
    assert plan.steps == (), "the extension should not be rewritten"
    assert plan.skipped[0].reason == "no match"


def test_rename_actually_moves_and_is_reversible(tmp_path: Path, journal: Journal) -> None:
    (tmp_path / "before.txt").write_text("payload")
    entry = scan(tmp_path).files[0]

    plan = plan_rename([entry], "after{ext}")
    result = operations.apply_renames(plan.steps, journal)

    assert result.applied == 1
    assert (tmp_path / "after.txt").exists()
    assert not (tmp_path / "before.txt").exists()

    reverted, errors = journal.undo_batch(result.batch)
    assert reverted == 1, errors
    assert (tmp_path / "before.txt").exists()
    assert not (tmp_path / "after.txt").exists()


# -- rules ----------------------------------------------------------------


def test_rule_matches_and_plans_without_touching_disk(tmp_path: Path) -> None:
    (tmp_path / "Screenshot 2026-01-01.png").write_text("x")
    (tmp_path / "notes.txt").write_text("y")

    engine = RuleEngine(
        [
            Rule(
                name="Date-prefix screenshots",
                matchers=[Matcher(Field.NAME, Comparison.STARTS_WITH, "Screenshot")],
                action=Action(ActionKind.RENAME, pattern="{date}_{stem}{ext}"),
            )
        ]
    )

    result = scan(tmp_path)
    before = sorted(p.name for p in tmp_path.iterdir())

    plan = engine.plan(result.files, root=tmp_path)

    screenshot = next(f for f in result.files if f.name.startswith("Screenshot"))

    assert len(plan) == 1
    # {date} is the file's modified date, not a date read out of its name.
    assert plan.changes[0].target == f"{screenshot.modified:%Y-%m-%d}_{screenshot.name}"
    assert plan.unmatched == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == before, "planning must not write"


def test_matchers_are_anded(tmp_path: Path) -> None:
    (tmp_path / "big.mp4").write_bytes(b"x" * 4096)  # 4 KB, over the threshold
    (tmp_path / "small.mp4").write_bytes(b"x" * 16)  # under it

    engine = RuleEngine(
        [
            Rule(
                name="Large video only",
                matchers=[
                    Matcher(Field.EXTENSION, Comparison.IN, "mp4"),
                    Matcher(Field.SIZE, Comparison.GREATER_THAN, "1 KB"),
                ],
                action=Action(ActionKind.MOVE, destination="Video/Large"),
            )
        ]
    )

    plan = engine.plan(scan(tmp_path).files, root=str(tmp_path))
    assert len(plan) == 1, "only the file satisfying both conditions should match"
    assert plan.changes[0].entry.name == "big.mp4"


def test_size_comparison_accepts_units() -> None:
    assert expand_pattern  # keep the import meaningful for linters
    from fileflow.core.rules import _parse_size

    assert _parse_size("500") == 500
    assert _parse_size("1kb") == 1024
    assert _parse_size("1.5 GB") == int(1.5 * 1024**3)
    assert _parse_size("nonsense") is None


def test_first_match_wins_by_default(tmp_path: Path) -> None:
    for name in ("a.png", "b.png"):
        (tmp_path / name).write_text("x")

    move = Rule(
        name="move",
        matchers=[Matcher(Field.EXTENSION, Comparison.EQUALS, "png")],
        action=Action(ActionKind.MOVE, destination="Images"),
        priority=1,
    )
    rename = Rule(
        name="rename",
        matchers=[Matcher(Field.EXTENSION, Comparison.EQUALS, "png")],
        action=Action(ActionKind.RENAME, pattern="x{ext}"),
        priority=2,
    )

    plan = RuleEngine([move, rename]).plan(scan(tmp_path).files, root=str(tmp_path))
    assert len(plan) == 2
    assert all(c.rule.id == move.id for c in plan.changes)


def test_rule_plan_applies_and_undoes(tmp_path: Path, journal: Journal) -> None:
    (tmp_path / "notes.txt").write_text("x")

    engine = RuleEngine(
        [
            Rule(
                name="Sort by type",
                matchers=[Matcher(Field.EXTENSION, Comparison.EQUALS, "txt")],
                action=Action(ActionKind.MOVE, destination="{category}"),
            )
        ]
    )

    result = scan(tmp_path)
    plan = engine.plan(result.files, root=str(tmp_path))
    applied = operations.apply_rule_plan(plan.changes, journal, root=tmp_path)

    assert applied.applied == 1
    assert (tmp_path / "Documents" / "notes.txt").exists()

    reverted, errors = journal.undo_batch(applied.batch)
    assert reverted == 1, errors
    assert (tmp_path / "notes.txt").exists()


# -- cleanup --------------------------------------------------------------


def test_cleanup_classifies_clutter(tmp_path: Path) -> None:
    (tmp_path / "cache.tmp").write_text("x")
    (tmp_path / "Thumbs.db").write_text("x")
    (tmp_path / "keep.txt").write_text("x")

    candidates = find_cleanup_candidates(scan(tmp_path).files)
    transient = next(c for c in candidates if c.kind.value == "transient")

    assert transient.count == 2
    assert transient.confidence == "certain"


def test_cleanup_finds_build_output(tmp_path: Path) -> None:
    node_modules = tmp_path / "node_modules" / "left-pad"
    node_modules.mkdir(parents=True)
    (node_modules / "index.js").write_text("x" * 50)

    candidates = find_cleanup_candidates(scan(tmp_path).files)
    regenerable = next((c for c in candidates if c.kind.value == "regenerable"), None)

    assert regenerable is not None, "build output must be visible to the cleanup view"
    assert regenerable.label == "node_modules/"


def test_skip_build_dirs_hides_them_from_the_scan(tmp_path: Path) -> None:
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "big.js").write_text("x" * 100)
    (tmp_path / "app.js").write_text("x")

    assert len(scan(tmp_path).files) == 2
    assert len(scan(tmp_path, skip_build_dirs=True).files) == 1


def test_stale_archives_only_when_old(tmp_path: Path) -> None:
    old = tmp_path / "old.zip"
    old.write_text("x")
    fresh = tmp_path / "new.zip"
    fresh.write_text("x")

    stale_time = (datetime.now() - timedelta(days=400)).timestamp()
    os.utime(old, (stale_time, stale_time))

    found = find_stale_archives(scan(tmp_path).files, older_than_days=180)
    assert [a.file.name for a in found] == ["old.zip"]


# -- quarantine and safety ------------------------------------------------


def test_quarantine_moves_rather_than_deletes(tmp_path: Path, journal: Journal) -> None:
    (tmp_path / "junk.txt").write_text("x")
    result = scan(tmp_path)

    applied = operations.quarantine(result.files, journal, root=tmp_path, reason="test")

    assert applied.applied == 1
    assert not (tmp_path / "junk.txt").exists()
    assert list((tmp_path / "_FileFlow Quarantine").iterdir())

    reverted, _ = journal.undo_batch(applied.batch)
    assert reverted == 1
    assert (tmp_path / "junk.txt").read_text() == "x"


def test_purge_refuses_to_delete_outside_quarantine(tmp_path: Path, journal: Journal) -> None:
    precious = tmp_path / "important.txt"
    precious.write_text("do not delete")

    entries = [f for f in scan(tmp_path).files if f.name == "important.txt"]
    applied = operations.purge_quarantine(entries, journal, root=tmp_path)

    assert applied.applied == 0
    assert applied.failed == 1
    assert "refusing" in applied.errors[0]
    assert precious.exists(), "the safety check must actually protect the file"


def test_purge_deletes_inside_quarantine(tmp_path: Path, journal: Journal) -> None:
    (tmp_path / "junk.txt").write_text("x")
    operations.quarantine(scan(tmp_path).files, journal, root=tmp_path)

    quarantined = list((tmp_path / "_FileFlow Quarantine").iterdir())
    assert len(quarantined) == 1

    applied = operations.purge_quarantine(
        [f for f in scan(tmp_path).files if "Quarantine" in str(f.path)], journal, root=tmp_path
    )

    assert applied.applied == 1
    assert list((tmp_path / "_FileFlow Quarantine").iterdir()) == []


def test_quarantine_rejects_files_outside_the_root(
    tmp_path: Path, journal: Journal
) -> None:
    """A stale entry from another folder must be reported, not raise.

    Regression: this used to raise ValueError out of the per-file loop and
    abandon the whole batch.
    """
    inside = tmp_path / "inside"
    inside.mkdir()
    (inside / "good.txt").write_text("x")

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "stranger.txt").write_text("y")

    entries = scan(inside).files + scan(elsewhere).files

    applied = operations.quarantine(entries, journal, root=inside)

    assert applied.applied == 1, "the in-root file should still be processed"
    assert applied.failed == 1
    assert "outside the open folder" in applied.errors[0]
    assert (elsewhere / "stranger.txt").exists(), "must not touch files elsewhere"


def test_journal_records_before_it_acts(tmp_path: Path, journal: Journal) -> None:
    batch = journal.new_batch()
    journal.record(
        OperationKind.MOVE,
        "test",
        {"from": str(tmp_path / "a"), "to": str(tmp_path / "b")},
        batch=batch,
    )

    entries = journal.entries_for_batch(batch)
    assert len(entries) == 1
    assert entries[0].kind is OperationKind.MOVE


def test_undo_of_missing_batch_is_reported_not_raised(journal: Journal) -> None:
    reverted, errors = journal.undo_batch("does-not-exist")
    assert reverted == 0
    assert errors == ["nothing to undo"]


def test_undo_is_idempotent(tmp_path: Path, journal: Journal) -> None:
    (tmp_path / "x.txt").write_text("1")
    result = operations.apply_renames(
        plan_rename(scan(tmp_path).files, "y{ext}").steps, journal
    )

    assert journal.undo_batch(result.batch)[0] == 1
    assert journal.undo_batch(result.batch)[0] == 0, "second undo should be a no-op"
    assert (tmp_path / "x.txt").exists()
