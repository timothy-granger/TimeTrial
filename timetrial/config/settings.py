"""Application configuration — loads from TOML with user overrides."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "default_config.toml"
_USER_CONFIG_PATH = Path.home() / ".timetrial" / "config.toml"


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration."""

    # Race timing
    timer_interval_ms: int = 100
    start_interval_minutes: float = 0.5
    countdown_sound_trigger_seconds: float = 16.0
    time_format: str = "hh:mm:ss.zzz"

    # Categories
    categories: tuple[str, ...] = ()
    junior_categories: tuple[str, ...] = ()

    # Series scoring
    series_points: tuple[int, ...] = (5, 4, 3, 2, 1)

    # Starter display fonts
    starter_font_rider: int = 75
    starter_font_countdown: int = 400
    starter_font_clock: int = 65
    starter_font_bib: int = 65
    starter_font_title: int = 40

    # Starter display branding
    race_title: str = ""
    race_subtitle: str = ""
    event_info: str = ""
    logo_image: str = ""
    logo_image_left: str = ""

    # Default file paths
    default_start_list: str = "tt-start-list.csv"
    default_finish_list: str = "tt-finish-list.csv"
    default_results: str = "tt-results.html"
    sound_file: str = "start.mp3"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _parse_toml(path: Path) -> dict:
    """Read and parse a TOML file."""
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_config(user_path: Optional[Path] = None) -> AppConfig:
    """Load configuration from default TOML, overlaid with user overrides.

    Args:
        user_path: Explicit path to user config. If None, uses ~/.timetrial/config.toml.
    """
    # Load shipped defaults
    data = _parse_toml(_DEFAULT_CONFIG_PATH)

    # Overlay user config if it exists
    override_path = user_path or _USER_CONFIG_PATH
    if override_path.exists():
        user_data = _parse_toml(override_path)
        data = _deep_merge(data, user_data)

    race = data.get("race", {})
    categories = data.get("categories", {})
    series = data.get("series", {})
    display = data.get("display", {})
    paths = data.get("paths", {})

    return AppConfig(
        timer_interval_ms=race.get("timer_interval_ms", 100),
        start_interval_minutes=race.get("start_interval_minutes", 0.5),
        countdown_sound_trigger_seconds=race.get("countdown_sound_trigger_seconds", 16.0),
        time_format=race.get("time_format", "hh:mm:ss.zzz"),
        categories=tuple(categories.get("names", [])),
        junior_categories=tuple(categories.get("junior_categories", [])),
        series_points=tuple(series.get("points", [5, 4, 3, 2, 1])),
        starter_font_rider=display.get("starter_font_rider", 75),
        starter_font_countdown=display.get("starter_font_countdown", 400),
        starter_font_clock=display.get("starter_font_clock", 65),
        starter_font_bib=display.get("starter_font_bib", 65),
        starter_font_title=display.get("starter_font_title", 40),
        race_title=display.get("race_title", ""),
        race_subtitle=display.get("race_subtitle", ""),
        event_info=display.get("event_info", ""),
        logo_image=display.get("logo_image", ""),
        logo_image_left=display.get("logo_image_left", ""),
        default_start_list=paths.get("default_start_list", "tt-start-list.csv"),
        default_finish_list=paths.get("default_finish_list", "tt-finish-list.csv"),
        default_results=paths.get("default_results", "tt-results.html"),
        sound_file=paths.get("sound_file", "start.mp3"),
    )
