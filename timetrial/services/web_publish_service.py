"""Publish live results to GitHub Pages via git push.

Uses a batching timer: collects result changes and pushes at most once
every PUBLISH_INTERVAL seconds. This prevents push pile-ups when multiple
finishers are recorded in quick succession.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from timetrial.config.settings import AppConfig
from timetrial.models.race import Race
from timetrial.services.event_bus import EventBus
from timetrial.services.results_service import ResultsService

PUBLISH_INTERVAL_MS = 30_000  # 30 seconds


class WebPublishService(QObject):
    """Pushes results.json to a GitHub Pages repo on a batched timer.

    When results change, a 30-second timer starts (or restarts). When the
    timer fires, the latest results are pushed. If a push is already in
    progress, the next push is queued for when it finishes.
    """

    publish_success = Signal(int)    # number of results published
    publish_error = Signal(str)

    def __init__(
        self,
        race: Race,
        config: AppConfig,
        event_bus: EventBus,
        results_svc: ResultsService,
        repo_path: Path,
        race_name: str = "Live Race Results",
        event_info: str = "",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._race = race
        self._config = config
        self._bus = event_bus
        self._results_svc = results_svc
        self._repo_path = repo_path
        self._race_name = race_name
        self._event_info = event_info
        self._enabled = True

        self._start_list_model = None
        self._push_in_progress = False
        self._push_pending = False  # another push needed after current one finishes

        # Batch timer — single-shot, restarts on each result change
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(PUBLISH_INTERVAL_MS)
        self._timer.timeout.connect(self._do_publish)

        self._bus.results_updated.connect(self._on_results_updated)

    def set_start_list_model(self, model) -> None:
        self._start_list_model = model

    def set_race_info(self, race_name: str, event_info: str) -> None:
        self._race_name = race_name
        self._event_info = event_info

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def publish_now(self) -> None:
        """Force an immediate publish (e.g. when race stops)."""
        self._timer.stop()
        self._do_publish()

    def _on_results_updated(self, html: str) -> None:
        """Results changed — start/restart the batch timer."""
        if not self._enabled or self._start_list_model is None:
            return

        # If a push is in progress, just mark that we need another one
        if self._push_in_progress:
            self._push_pending = True
            return

        # Start (or restart) the batch timer
        self._timer.start()

    def _do_publish(self) -> None:
        """Build the JSON and push in a background thread."""
        if self._start_list_model is None:
            return

        if self._push_in_progress:
            self._push_pending = True
            return

        # Compute structured results
        results = self._results_svc.compute_all_results(
            self._race,
            self._start_list_model.finish_times,
            self._start_list_model.results,
        )

        data = {
            "race_name": self._race_name,
            "event_info": self._event_info,
            "updated_at": datetime.now().isoformat(),
            "results": [
                {
                    "bib": r.bib_number,
                    "first_name": r.first_name,
                    "last_name": r.last_name,
                    "category": r.category,
                    "finish_time": r.finish_time_str,
                    "result_time": r.result_time_str,
                    "result_ms": r.result_ms,
                }
                for r in results
                if r.has_result
            ],
        }

        self._push_in_progress = True
        self._worker = _PushWorker(self._repo_path, data)
        self._worker.success.connect(self._on_push_done)
        self._worker.error.connect(self._on_push_error)
        self._worker.start()

    def _on_push_done(self, count: int) -> None:
        """Push completed successfully."""
        self._push_in_progress = False
        self.publish_success.emit(count)

        # If results changed while we were pushing, push again immediately
        if self._push_pending:
            self._push_pending = False
            self._do_publish()

    def _on_push_error(self, msg: str) -> None:
        """Push failed."""
        self._push_in_progress = False
        self.publish_error.emit(msg)

        # Still try the pending push if there is one
        if self._push_pending:
            self._push_pending = False
            self._do_publish()


class _PushWorker(QThread):
    """Background thread that writes results.json and git pushes."""

    success = Signal(int)   # number of results
    error = Signal(str)

    def __init__(self, repo_path: Path, data: dict) -> None:
        super().__init__()
        self._repo_path = repo_path
        self._data = data

    def run(self) -> None:
        try:
            json_path = self._repo_path / "results.json"
            json_path.write_text(
                json.dumps(self._data, indent=2),
                encoding="utf-8",
            )

            self._git("add", "results.json")
            self._git(
                "commit", "-m",
                f"Update results: {len(self._data['results'])} finishers",
            )
            self._git("push")

            self.success.emit(len(self._data["results"]))

        except Exception as e:
            self.error.emit(str(e))

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git"] + list(args),
            cwd=str(self._repo_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                return result.stdout
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout
