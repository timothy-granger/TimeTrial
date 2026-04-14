"""Audio playback for countdown start signal."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, QObject
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from timetrial.config.settings import AppConfig
from timetrial.services.event_bus import EventBus


class AudioService(QObject):
    """Plays the start sound when the countdown reaches the trigger threshold."""

    def __init__(
        self,
        config: AppConfig,
        event_bus: EventBus,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._bus = event_bus

        self._player: QMediaPlayer | None = None
        self._audio_output: QAudioOutput | None = None

        self._init_player()
        self._bus.countdown_sound_trigger.connect(self._on_trigger)

    def _init_player(self) -> None:
        """Set up the media player if the sound file exists."""
        sound_path = Path(self._config.sound_file)
        if not sound_path.exists():
            return

        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(0.5)

        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_output)
        self._player.setSource(QUrl.fromLocalFile(str(sound_path.resolve())))

    def _on_trigger(self) -> None:
        """Play the start sound."""
        if self._player is None:
            return

        # Rewind and play
        self._player.setPosition(0)
        self._player.play()
