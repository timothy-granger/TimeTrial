"""Add/Edit rider dialog with validation."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QComboBox,
    QDoubleSpinBox, QLabel, QWidget,
)

from timetrial.models.rider import Rider
from timetrial.models.race import Race


class AddRiderDialog(QDialog):
    """Modal dialog for adding or editing a rider."""

    def __init__(
        self,
        categories: list[str],
        race: Race,
        default_position: float = 0.5,
        rider: Optional[Rider] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._race = race
        self._editing = rider  # None = add mode, Rider = edit mode

        if rider:
            self.setWindowTitle("Edit Rider")
        else:
            self.setWindowTitle("Add Rider")

        self.setMinimumWidth(350)
        self._init_ui(categories, default_position, rider)
        self._connect_signals()
        self._validate()

    # -- Public --

    def get_rider(self) -> Rider:
        """Return a Rider from the current field values."""
        return Rider(
            bib_number=self._bib.text().strip(),
            last_name=self._last.text().strip(),
            first_name=self._first.text().strip(),
            category=self._category.currentText(),
            start_position=self._position.value(),
        )

    # -- UI Setup --

    def _init_ui(self, categories: list[str], default_position: float, rider: Optional[Rider]) -> None:
        layout = QFormLayout(self)

        # Bib number
        self._bib = QLineEdit()
        self._bib.setPlaceholderText("Unique bib number")
        layout.addRow("Bib #:", self._bib)

        # Last name
        self._last = QLineEdit()
        layout.addRow("Last Name:", self._last)

        # First name
        self._first = QLineEdit()
        layout.addRow("First Name:", self._first)

        # Category
        self._category = QComboBox()
        self._category.addItems(categories)
        self._category.setEditable(True)  # Allow custom categories
        layout.addRow("Category:", self._category)

        # Start position
        self._position = QDoubleSpinBox()
        self._position.setMinimum(0.5)
        self._position.setMaximum(999.0)
        self._position.setSingleStep(0.5)
        self._position.setDecimals(1)
        self._position.setValue(default_position)
        layout.addRow("Start Position:", self._position)

        # Validation message
        self._status = QLabel()
        self._status.setStyleSheet("color: red")
        layout.addRow(self._status)

        # Buttons
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addRow(self._buttons)

        # Populate if editing
        if rider:
            self._bib.setText(rider.bib_number)
            self._last.setText(rider.last_name)
            self._first.setText(rider.first_name)

            idx = self._category.findText(rider.category)
            if idx >= 0:
                self._category.setCurrentIndex(idx)
            else:
                self._category.setEditText(rider.category)

            self._position.setValue(rider.start_position)

    def _connect_signals(self) -> None:
        self._bib.textChanged.connect(self._validate)
        self._last.textChanged.connect(self._validate)
        self._first.textChanged.connect(self._validate)
        self._position.valueChanged.connect(self._validate)

    # -- Validation --

    def _validate(self) -> None:
        """Enable OK only when all fields are valid."""
        ok = True
        messages: list[str] = []

        bib = self._bib.text().strip()
        last = self._last.text().strip()
        first = self._first.text().strip()
        position = self._position.value()

        # Bib required
        if not bib:
            ok = False
            messages.append("Bib # is required")

        # Bib uniqueness
        exclude = self._editing.bib_number if self._editing else None
        if bib and self._race.is_bib_taken(bib, exclude_bib=exclude):
            ok = False
            messages.append(f"Bib #{bib} is already in use")

        # Names required
        if not last:
            ok = False
            messages.append("Last name is required")
        if not first:
            ok = False
            messages.append("First name is required")

        # Position uniqueness
        if self._race.is_position_taken(position, exclude_bib=exclude):
            ok = False
            messages.append(f"Position {position} is already taken")

        self._status.setText("\n".join(messages))
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)
