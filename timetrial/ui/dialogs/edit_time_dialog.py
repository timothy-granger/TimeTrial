"""Dialog for editing a finish time or race start time."""

from __future__ import annotations

from datetime import datetime, time
from typing import Optional

from PySide6.QtCore import QDate, QDateTime, QTime, Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QDateTimeEdit, QLabel, QWidget,
)


class EditTimeDialog(QDialog):
    """QDateTimeEdit dialog for correcting a time value."""

    def __init__(
        self,
        current_time_str: str,
        race_start: Optional[datetime] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Time")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Adjust the time:"))

        self._edit = QDateTimeEdit()
        self._edit.setDisplayFormat("hh:mm:ss.zzz")
        self._edit.setCalendarPopup(False)

        # Parse current time
        qt_time = self._parse_time(current_time_str)
        if race_start:
            qdate = QDate(race_start.year, race_start.month, race_start.day)
            qdt = QDateTime(qdate, qt_time)
            self._edit.setDateTime(qdt)
        else:
            self._edit.setTime(qt_time)

        layout.addWidget(self._edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_time_str(self) -> str:
        """Return the edited time as 'hh:mm:ss.zzz'."""
        t = self._edit.time()
        return f"{t.hour():02d}:{t.minute():02d}:{t.second():02d}.{t.msec():03d}"

    @staticmethod
    def _parse_time(time_str: str) -> QTime:
        """Parse 'hh:mm:ss.zzz' to QTime."""
        try:
            parts = time_str.split(".")
            base = parts[0]
            ms_str = parts[1] if len(parts) > 1 else "000"
            ms_str = ms_str.ljust(3, "0")[:3]

            time_parts = base.split(":")
            h = int(time_parts[0])
            m = int(time_parts[1])
            s = int(time_parts[2])
            return QTime(h, m, s, int(ms_str))
        except (ValueError, IndexError):
            return QTime(0, 0, 0, 0)
