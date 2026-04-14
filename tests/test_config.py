"""Tests for configuration loading."""

from pathlib import Path

from timetrial.config.settings import AppConfig, load_config, _deep_merge


class TestDeepMerge:
    def test_simple_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        assert _deep_merge(base, override) == {"a": 1, "b": 3}

    def test_nested_override(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 99}, "b": 3}

    def test_add_new_key(self):
        base = {"a": 1}
        override = {"b": 2}
        assert _deep_merge(base, override) == {"a": 1, "b": 2}

    def test_does_not_mutate_base(self):
        base = {"a": {"x": 1}}
        override = {"a": {"x": 2}}
        _deep_merge(base, override)
        assert base["a"]["x"] == 1


class TestLoadConfig:
    def test_loads_defaults(self):
        config = load_config(user_path=Path("/nonexistent/path/config.toml"))
        assert isinstance(config, AppConfig)
        assert config.timer_interval_ms == 100
        assert config.start_interval_minutes == 0.5
        assert config.countdown_sound_trigger_seconds == 11.0
        assert len(config.categories) > 0
        assert "Men (P/1/2/3)" in config.categories
        assert config.series_points == (5, 4, 3, 2, 1)

    def test_junior_categories_loaded(self):
        config = load_config(user_path=Path("/nonexistent/path/config.toml"))
        assert "10-14 (M)" in config.junior_categories
        assert "15-18 (M)" in config.junior_categories
        assert "10-14 (F)" in config.junior_categories
        assert "15-18 (F)" in config.junior_categories

    def test_config_is_frozen(self):
        config = load_config(user_path=Path("/nonexistent/path/config.toml"))
        import pytest
        with pytest.raises(AttributeError):
            config.timer_interval_ms = 200  # type: ignore

    def test_user_override(self, tmp_path):
        override_file = tmp_path / "config.toml"
        override_file.write_text(
            '[race]\ntimer_interval_ms = 50\n\n[series]\npoints = [10, 8, 6, 4, 2]\n'
        )
        config = load_config(user_path=override_file)
        assert config.timer_interval_ms == 50
        assert config.series_points == (10, 8, 6, 4, 2)
        # Non-overridden values stay at defaults
        assert config.start_interval_minutes == 0.5

    def test_display_fonts_loaded(self):
        config = load_config(user_path=Path("/nonexistent/path/config.toml"))
        assert config.starter_font_rider == 75
        assert config.starter_font_countdown == 400
        assert config.starter_font_clock == 65
        assert config.starter_font_bib == 65

    def test_default_paths_loaded(self):
        config = load_config(user_path=Path("/nonexistent/path/config.toml"))
        assert config.default_start_list == "tt-start-list.csv"
        assert config.default_finish_list == "tt-finish-list.csv"
        assert "start" in config.sound_file
