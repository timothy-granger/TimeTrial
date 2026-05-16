"""Application entry point and dependency wiring."""

import sys
from pathlib import Path


def main() -> None:
    from PySide6.QtWidgets import QApplication, QMessageBox

    from timetrial.config.settings import load_config
    from timetrial.models.race import Race, RaceState
    from timetrial.services.event_bus import EventBus
    from timetrial.services.timing_service import TimingService
    from timetrial.services.results_service import ResultsService
    from timetrial.services.series_service import SeriesService
    from timetrial.services.import_export_service import ImportExportService
    from timetrial.services.audio_service import AudioService
    from timetrial.services.persistence_service import PersistenceService
    from timetrial.services.web_publish_service import WebPublishService
    from timetrial.ui.main_window import MainWindow

    app = QApplication(sys.argv)

    config = load_config()
    race = Race()
    event_bus = EventBus()

    timing_svc = TimingService(race, config, event_bus)
    results_svc = ResultsService(config)
    series_svc = SeriesService(config)
    io_svc = ImportExportService(config)
    audio_svc = AudioService(config, event_bus)

    # Persistence
    db_path = Path.home() / ".timetrial" / "races.db"
    persistence_svc = PersistenceService(db_path)
    persistence_svc.open()

    # Web publishing (GitHub Pages)
    repo_path = Path("D:/tt-live-results")
    web_publish_svc = None
    if repo_path.exists():
        web_publish_svc = WebPublishService(
            race, config, event_bus, results_svc,
            repo_path=repo_path,
            race_name=config.race_title or "Greenville Spinners Time Trial",
            event_info=config.event_info,
        )

    # Check for recoverable race
    recoverable_id = persistence_svc.find_recoverable_race()
    if recoverable_id is not None:
        reply = QMessageBox.question(
            None, "Recover Race",
            "A previous race was not completed.\nWould you like to recover it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            snapshot = persistence_svc.load_race(recoverable_id)
            race.start_time = snapshot["start_time"]
            race.state = RaceState.STOPPED
            race.riders = snapshot["riders"]
            race.current_rider_index = len(race.riders)

    main_window = MainWindow(
        race, config, event_bus,
        timing_svc, results_svc, series_svc, io_svc,
        persistence_svc,
    )

    # Wire web publish service to start list model
    if web_publish_svc:
        web_publish_svc.set_start_list_model(main_window._start_list.model)
        web_publish_svc.publish_success.connect(
            lambda n: main_window.statusBar().showMessage(f"Results published to web ({n} finishers)", 3000)
        )
        web_publish_svc.publish_error.connect(
            lambda e: main_window.statusBar().showMessage(f"Publish error: {e}", 5000)
        )
        main_window._web_publish_svc = web_publish_svc
        main_window._race_control.enable_clear_web_results(True)

    # Load recovered finish records into the UI after MainWindow is built
    if recoverable_id is not None and reply == QMessageBox.StandardButton.Yes:
        main_window.load_recovered_data(snapshot)

    main_window.show()

    # Keep references alive for app lifetime
    main_window._audio_svc = audio_svc

    ret = app.exec()
    persistence_svc.close()
    sys.exit(ret)
