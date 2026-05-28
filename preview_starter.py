"""Quick preview of the StarterDisplay with simulated race data."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from timetrial.config.settings import load_config
from timetrial.services.event_bus import EventBus
from timetrial.ui.starter_display import StarterDisplay


def main():
    app = QApplication(sys.argv)
    config = load_config()
    bus = EventBus()

    display = StarterDisplay(config, bus)
    display.showMaximized()

    # Simulate race sequence with timed events
    def step1():
        """Race starts, first rider on ramp."""
        bus.race_started.emit()
        bus.rider_on_ramp.emit("John Smith", "101")
        bus.rider_on_deck.emit("Jane Doe")
        bus.elapsed_updated.emit(0)

    def step2():
        """Countdown from 30."""
        bus.countdown_updated.emit(30)

    def step3():
        bus.countdown_updated.emit(20)

    def step4():
        bus.countdown_updated.emit(10)

    def step5():
        bus.countdown_updated.emit(5)

    def step6():
        """Rider started, next rider up."""
        bus.countdown_updated.emit(0)
        bus.rider_on_ramp.emit("Jane Doe", "102")
        bus.rider_on_deck.emit("Bob Johnson")
        bus.elapsed_updated.emit(30000)

    def step7():
        bus.countdown_updated.emit(25)

    def step8():
        bus.countdown_updated.emit(15)

    def step9():
        bus.countdown_updated.emit(5)

    # Schedule the sequence
    QTimer.singleShot(500, step1)    # 0.5s - first rider
    QTimer.singleShot(2000, step2)   # 2s   - countdown 30
    QTimer.singleShot(4000, step3)   # 4s   - countdown 20
    QTimer.singleShot(6000, step4)   # 6s   - countdown 10
    QTimer.singleShot(8000, step5)   # 8s   - countdown 5
    QTimer.singleShot(10000, step6)  # 10s  - next rider
    QTimer.singleShot(12000, step7)  # 12s  - countdown 25
    QTimer.singleShot(14000, step8)  # 14s  - countdown 15
    QTimer.singleShot(16000, step9)  # 16s  - countdown 5

    print("Starter Display preview running — close the window to exit.")
    print("Simulating: rider on ramp -> countdown -> next rider")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
