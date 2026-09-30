"""Rules: build matchers and actions, preview what they would do, then apply."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core import operations
from ...core.models import ScanResult
from ...core.rules import (
    TEMPLATES,
    Action,
    ActionKind,
    Comparison,
    Field,
    Matcher,
    Rule,
)
from ..widgets import EmptyState, format_count, horizontal_line, row

log = logging.getLogger("fileflow.rules")

FIELDS = (
    (Field.NAME, "Name"),
    (Field.EXTENSION, "Extension"),
    (Field.SIZE, "Size"),
    (Field.MODIFIED, "Last modified"),
    (Field.PATH, "Path"),
)

# Only the comparisons that mean something for the selected field. Offering
# `name older_than_days` would be a bug waiting to happen.
COMPARISONS: dict[Field, tuple[tuple[Comparison, str], ...]] = {
    Field.NAME: (
        (Comparison.EQUALS, "is"),
        (Comparison.NOT_EQUALS, "is not"),
        (Comparison.CONTAINS, "contains"),
        (Comparison.STARTS_WITH, "starts with"),
        (Comparison.ENDS_WITH, "ends with"),
        (Comparison.MATCHES, "matches regex"),
    ),
    Field.EXTENSION: (
        (Comparison.EQUALS, "is"),
        (Comparison.IN, "is one of"),
    ),
    Field.SIZE: (
        (Comparison.GREATER_THAN, "is larger than"),
        (Comparison.LESS_THAN, "is smaller than"),
        (Comparison.EQUALS, "is exactly"),
    ),
    Field.MODIFIED: (
        (Comparison.OLDER_THAN_DAYS, "days ago or more"),
        (Comparison.NEWER_THAN_DAYS, "days ago or fewer"),
    ),
    Field.PATH: (
        (Comparison.CONTAINS, "contains"),
        (Comparison.STARTS_WITH, "starts with"),
    ),
}

COMPARISON_HINTS = {
    Comparison.IN: "Comma separated, e.g. pdf, docx, txt",
    Comparison.MATCHES: r"Regular expression, e.g. ^IMG_\d+",
    Comparison.GREATER_THAN: "Accepts units, e.g. 500MB, 1.5 GB",
    Comparison.LESS_THAN: "Accepts units, e.g. 500MB, 1.5 GB",
}

ACTION_HINTS = {
    ActionKind.MOVE: "Folder relative to the scanned folder. "
    "Tokens: {category} {year} {month} {day} {name} {parent}",
    ActionKind.RENAME: "Tokens: {name} {stem} {ext} {date} {time} {year} {month} {day} "
    "{index} {index:3} {case:lower|upper|kebab|snake|title}",
    ActionKind.RENAME_AND_MOVE: "Rename and move in one step. Uses both sets of tokens.",
    ActionKind.TAG: "Recorded in Activity. Does not touch the filesystem.",
}


class TitledGroup(QWidget):
    """A labelled group of widgets without QGroupBox's frame quirks."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        label = QLabel(title.upper())
        label.setObjectName("Muted")
        self._layout.addWidget(label)

    def inner(self) -> QVBoxLayout:
        return self._layout


class RuleDialog(QDialog):
    """Editor for a single rule."""

    def __init__(self, rule: Rule | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit rule" if rule else "New rule")
        self.setMinimumWidth(520)

        self._rule = rule

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self.name_input = QLineEdit(rule.name if rule else "")
        self.name_input.setPlaceholderText("Screenshots into Images")

        self.priority = QSpinBox()
        self.priority.setRange(1, 999)
        self.priority.setValue(rule.priority if rule else 100)

        self.enabled = QCheckBox("Enabled")
        self.enabled.setChecked(rule.enabled if rule else True)

        form.addRow("Name", self.name_input)
        form.addRow("Priority", self.priority)
        form.addRow("", self.enabled)

        layout.addLayout(form)
        layout.addWidget(self._build_matchers(rule))
        layout.addWidget(self._build_action(rule))
        layout.addWidget(horizontal_line())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_matchers(self, rule: Rule | None) -> QWidget:
        box = TitledGroup("When all of these are true")
        layout = box.inner()

        self.matcher_list = QListWidget()
        self.matcher_list.setMaximumHeight(120)

        self.field_combo = QComboBox()
        for value, label in FIELDS:
            self.field_combo.addItem(label, value)
        self.field_combo.currentIndexChanged.connect(self._sync_comparisons)

        self.comparison_combo = QComboBox()

        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("value")

        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_matcher)
        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(self._remove_matcher)

        add_row = row(
            self.field_combo, self.comparison_combo, self.value_input, add_button, remove_button
        )

        layout.addWidget(self.matcher_list)
        layout.addLayout(add_row)

        self._sync_comparisons()

        if rule:
            for matcher in rule.matchers:
                self._append_matcher(matcher)
        else:
            self._append_matcher(Matcher(Field.EXTENSION, Comparison.IN, "pdf, docx"))

        return box

    def _build_action(self, rule: Rule | None) -> QWidget:
        box = TitledGroup("Then do this")
        layout = box.inner()

        self.action_combo = QComboBox()
        for kind in ActionKind:
            self.action_combo.addItem(kind.value.replace("_", " ").title(), kind)
        self.action_combo.currentIndexChanged.connect(self._sync_action_fields)

        self.destination = QLineEdit()
        self.destination.setPlaceholderText("Images/{category}")

        self.pattern = QLineEdit()
        self.pattern.setPlaceholderText("{date}_{stem}{ext}")

        self.tag = QLineEdit()
        self.tag.setPlaceholderText("stale")

        self.create_missing = QCheckBox("Create the destination folder if missing")
        self.create_missing.setChecked(True)

        self.action_hint = QLabel()
        self.action_hint.setObjectName("Muted")
        self.action_hint.setWordWrap(True)

        layout.addWidget(self.action_combo)
        layout.addWidget(self.destination)
        layout.addWidget(self.pattern)
        layout.addWidget(self.tag)
        layout.addWidget(self.create_missing)
        layout.addWidget(self.action_hint)

        if rule:
            self.action_combo.setCurrentIndex(
                [k.value for k in ActionKind].index(rule.action.kind.value)
            )
            self.destination.setText(rule.action.destination)
            self.pattern.setText(rule.action.pattern)
            self.tag.setText(rule.action.tag)
            self.create_missing.setChecked(rule.action.create_missing)

        self._sync_action_fields()
        return box

    # -- field syncing -----------------------------------------------------

    def _sync_comparisons(self) -> None:
        field = self.field_combo.currentData()
        previous = self.comparison_combo.currentData()

        self.comparison_combo.blockSignals(True)
        self.comparison_combo.clear()
        for value, label in COMPARISONS.get(field, ()):
            self.comparison_combo.addItem(label, value)

        # Keep the user's choice when the new field also supports it.
        for index in range(self.comparison_combo.count()):
            if self.comparison_combo.itemData(index) == previous:
                self.comparison_combo.setCurrentIndex(index)
                break
        self.comparison_combo.blockSignals(False)

        self._sync_hint()

    def _sync_hint(self) -> None:
        comparison = self.comparison_combo.currentData()
        self.value_input.setPlaceholderText(COMPARISON_HINTS.get(comparison, "value"))

    def _sync_action_fields(self) -> None:
        kind = self.action_combo.currentData()
        self.destination.setVisible(kind in (ActionKind.MOVE, ActionKind.RENAME_AND_MOVE))
        self.pattern.setVisible(kind in (ActionKind.RENAME, ActionKind.RENAME_AND_MOVE))
        self.tag.setVisible(kind is ActionKind.TAG)
        self.create_missing.setVisible(kind in (ActionKind.MOVE, ActionKind.RENAME_AND_MOVE))
        self.action_hint.setText(ACTION_HINTS.get(kind, ""))

    # -- matchers ----------------------------------------------------------

    def _append_matcher(self, matcher: Matcher) -> None:
        item = QListWidgetItem(matcher.describe())
        item.setData(Qt.ItemDataRole.UserRole, matcher)
        self.matcher_list.addItem(item)

    def _add_matcher(self) -> None:
        value = self.value_input.text().strip()
        if not value:
            return

        matcher = Matcher(
            self.field_combo.currentData(),
            self.comparison_combo.currentData(),
            value,
        )

        # A duplicate condition is almost always a mistake, and silently
        # narrows nothing.
        if any(m.describe() == matcher.describe() for m in self.matchers()):
            return

        self._append_matcher(matcher)
        self.value_input.clear()

    def _remove_matcher(self) -> None:
        for item in self.matcher_list.selectedItems():
            self.matcher_list.takeItem(self.matcher_list.row(item))

    def matchers(self) -> list[Matcher]:
        return [
            self.matcher_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.matcher_list.count())
        ]

    # -- result ------------------------------------------------------------

    def build_rule(self) -> Rule:
        action = Action(
            kind=self.action_combo.currentData(),
            destination=self.destination.text().strip(),
            pattern=self.pattern.text().strip(),
            tag=self.tag.text().strip(),
            create_missing=self.create_missing.isChecked(),
        )

        existing = self._rule
        return Rule(
            id=existing.id if existing else uuid.uuid4().hex[:12],
            name=self.name_input.text().strip() or "Untitled rule",
            matchers=self.matchers(),
            action=action,
            enabled=self.enabled.isChecked(),
            priority=self.priority.value(),
            run_count=existing.run_count if existing else 0,
            last_run=existing.last_run if existing else None,
        )


class RulesPage(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.root: Path | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        layout.addLayout(self._build_header())
        layout.addWidget(horizontal_line())
        layout.addWidget(self._build_body(), 1)

    def _build_header(self):
        box = QVBoxLayout()
        box.setSpacing(2)

        title = QLabel("Rules")
        title.setObjectName("PageTitle")

        self.subtitle = QLabel("Matchers and actions that file your folders for you.")
        self.subtitle.setObjectName("PageSubtitle")

        box.addWidget(title)
        box.addWidget(self.subtitle)

        self.new_button = QPushButton("New rule")
        self.new_button.clicked.connect(lambda: self._edit_rule(None))

        self.template_button = QPushButton("From template…")
        self.template_button.clicked.connect(self._add_from_template)

        self.run_button = QPushButton("Preview rules")
        self.run_button.setObjectName("Primary")
        self.run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_button.setToolTip(
            "Show what the active rules would do, without changing anything"
        )
        self.run_button.clicked.connect(self.preview)
        self.run_button.setEnabled(False)

        return row(box, None, self.template_button, self.new_button, self.run_button, spacing=10)

    def _build_body(self) -> QWidget:
        self.stack = QStackedWidget()

        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.list.itemDoubleClicked.connect(self._on_edit_requested)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context)

        self.stack.addWidget(self.list)

        self.empty = EmptyState(
            "No rules yet",
            "A rule is a condition and an action: when a file matches this, do that. "
            "You can always preview before anything moves.",
            "Create a rule",
        )
        self.empty.clicked.connect(lambda: self._edit_rule(None))
        self.stack.addWidget(self.empty)

        self._refresh()
        return self.stack

    def set_scan(self, result: ScanResult, root: Path | None) -> None:
        self.root = root
        self.run_button.setEnabled(bool(result.files))
        self._refresh()

    def _refresh(self) -> None:
        rules = self.window.engine.rules
        self.stack.setCurrentIndex(0 if rules else 1)

        self.list.clear()
        for rule in rules:
            item = QListWidgetItem(
                f"{'●' if rule.enabled else '○'}  {rule.name}\n     {rule.describe()}"
            )
            item.setData(Qt.ItemDataRole.UserRole, rule)
            self.list.addItem(item)

        active = sum(1 for r in rules if r.enabled)
        self.subtitle.setText(f"{len(rules)} rules, {active} enabled.")

    # -- editing -----------------------------------------------------------

    def _edit_rule(self, rule: Rule | None) -> None:
        dialog = RuleDialog(rule, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        built = dialog.build_rule()
        if not built.matchers:
            QMessageBox.warning(self, "Rule needs a condition", "Add at least one condition.")
            return

        if rule is None:
            self.window.engine.add(built)
        else:
            rules = self.window.engine.rules
            index = next((i for i, r in enumerate(rules) if r.id == rule.id), -1)
            if index >= 0:
                rules[index] = built
            else:
                self.window.engine.add(built)

        self.window.persist_rules()
        self._refresh()

    def _on_edit_requested(self, item: QListWidgetItem) -> None:
        rule = item.data(Qt.ItemDataRole.UserRole)
        if rule:
            self._edit_rule(rule)

    def _add_from_template(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Add from template")
        dialog.setMinimumWidth(420)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Pick a starting point. You can edit it afterwards."))

        listing = QListWidget()
        for template in TEMPLATES:
            matchers = " and ".join(m.describe() for m in template["matchers"])
            listing.addItem(QListWidgetItem(f"{template['name']}\n     when {matchers}"))
        layout.addWidget(listing, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted or listing.currentRow() < 0:
            return

        template = TEMPLATES[listing.currentRow()]
        self.window.engine.add(
            Rule(
                name=template["name"],
                matchers=list(template["matchers"]),
                action=template["action"],
            )
        )
        self.window.persist_rules()
        self._refresh()

    def _on_context(self, position) -> None:
        item = self.list.itemAt(position)
        if item is None:
            return

        rule = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        toggle = menu.addAction("Disable" if rule.enabled else "Enable")
        toggle.triggered.connect(lambda: self._toggle(rule))

        menu.addAction("Edit…").triggered.connect(lambda: self._edit_rule(rule))

        if rule.run_count:
            menu.addAction("Reset run count").triggered.connect(lambda: self._reset_count(rule))

        menu.addSeparator()
        menu.addAction("Delete").triggered.connect(lambda: self._delete(rule))
        menu.exec(self.list.viewport().mapToGlobal(position))

    def _toggle(self, rule: Rule) -> None:
        rule.enabled = not rule.enabled
        self.window.persist_rules()
        self._refresh()

    def _reset_count(self, rule: Rule) -> None:
        rule.run_count = 0
        rule.last_run = None
        self.window.persist_rules()
        self._refresh()

    def _delete(self, rule: Rule) -> None:
        answer = QMessageBox.question(
            self, "Delete rule", f"Delete “{rule.name}”?", QMessageBox.StandardButton.Yes
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.window.engine.remove(rule.id)
            self.window.persist_rules()
            self._refresh()

    # -- preview and apply -------------------------------------------------

    def preview(self) -> None:
        if self.window.scan is None or self.root is None:
            return

        plan = self.window.engine.plan(self.window.scan.files, root=self.root)

        if not plan:
            QMessageBox.information(
                self, "Nothing to do", "No active rule matches anything in this folder."
            )
            return

        self._show_plan(plan)

    def _show_plan(self, plan) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Preview")
        dialog.resize(720, 520)

        layout = QVBoxLayout(dialog)

        summary = QLabel(
            f"{format_count(len(plan))} files would change · "
            f"{format_count(plan.unmatched)} unmatched · {plan.skipped} skipped"
        )
        summary.setObjectName("Muted")
        layout.addWidget(summary)

        view = QTextEdit()
        view.setReadOnly(True)
        view.setPlainText(
            "\n".join(
                f"{change.entry.name}\n    {change.source}  →  "
                f"{change.target or '(tag only)'}"
                for change in plan.changes[:400]
            )
            + ("\n\n… and more" if len(plan.changes) > 400 else "")
        )
        layout.addWidget(view, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Apply")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted or self.root is None:
            return

        result = operations.apply_rule_plan(plan.changes, self.window.journal, root=self.root)

        if result.errors:
            QMessageBox.warning(
                self,
                "Finished with errors",
                result.summary() + "\n\n" + "\n".join(result.errors[:10]),
            )

        for rule in self.window.engine.rules:
            hits = plan.rule_hits.get(rule.id, 0)
            if hits:
                rule.run_count += hits
                rule.last_run = datetime.now()

        self.window.persist_rules()
        self.window._set_status(result.summary())
        self.window._refresh_undo_state()
        self._refresh()
        self.window.rescan()
