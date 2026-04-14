"""EventBus — Qt Signals as domain events for decoupling services from UI."""

from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    """Central event bus. Services emit signals; UI subscribes."""

    # -- Timing events --
    race_started = Signal()
    race_stopped = Signal()
    elapsed_updated = Signal(int)          # elapsed_ms since race start
    countdown_updated = Signal(float)      # seconds remaining until current rider starts
    rider_advanced = Signal(int)           # new current_rider_index
    countdown_sound_trigger = Signal()     # fire once when countdown <= threshold

    # -- Race status display --
    rider_on_ramp = Signal(str, str)       # display_name, bib_number
    rider_on_deck = Signal(str)            # display_name (or empty)
    rider_in_hole = Signal(str)            # display_name (or empty)
    all_riders_started = Signal()          # no more riders to start

    # -- Finish events --
    finish_recorded = Signal(int)          # index into finish_records
    finish_identified = Signal(int, str)   # finish_record index, bib

    # -- Results events --
    results_updated = Signal(str)          # HTML string

    # -- Series events --
    series_updated = Signal(str)           # HTML string
