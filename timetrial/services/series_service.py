"""Multi-event series points calculation and standings."""

from __future__ import annotations

from timetrial.config.settings import AppConfig
from timetrial.models.result import RaceResult
from timetrial.models.series import SeriesEntry


class SeriesService:
    """Awards points per race, maintains cumulative standings."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    # ------------------------------------------------------------------
    # Points award for a single race
    # ------------------------------------------------------------------

    def award_points(
        self,
        category_results: dict[str, list[RaceResult]],
    ) -> list[tuple[RaceResult, int]]:
        """Award series points to top finishers in each category.

        Points are taken from config.series_points (default [5,4,3,2,1]).
        Finishers beyond the points list receive 0.

        Args:
            category_results: Results grouped by category, each sorted fastest-first.

        Returns:
            List of (RaceResult, points_awarded) for every finisher.
        """
        awards: list[tuple[RaceResult, int]] = []
        points_table = self._config.series_points

        for _category, results in category_results.items():
            for i, result in enumerate(results):
                pts = points_table[i] if i < len(points_table) else 0
                awards.append((result, pts))

        return awards

    # ------------------------------------------------------------------
    # Cumulative standings update
    # ------------------------------------------------------------------

    def update_standings(
        self,
        current_standings: list[SeriesEntry],
        category_results: dict[str, list[RaceResult]],
    ) -> list[SeriesEntry]:
        """Merge today's race points into cumulative standings.

        For each finisher:
        - If found in standings (matched by category + display_name): add points.
        - If not found: create a new entry with today's points.

        Args:
            current_standings: Existing cumulative standings (will not be mutated).
            category_results: Today's results grouped by category, sorted fastest-first.

        Returns:
            New list of SeriesEntry with updated totals.
        """
        # Copy standings so we don't mutate the input
        standings = [
            SeriesEntry(e.first_name, e.last_name, e.category, e.total_points)
            for e in current_standings
        ]

        awards = self.award_points(category_results)

        for result, pts in awards:
            if pts == 0:
                continue

            # Look up by category + name
            found = False
            for entry in standings:
                if (entry.category == result.category
                        and entry.first_name == result.first_name
                        and entry.last_name == result.last_name):
                    entry.total_points += pts
                    found = True
                    break

            if not found:
                standings.append(SeriesEntry(
                    first_name=result.first_name,
                    last_name=result.last_name,
                    category=result.category,
                    total_points=pts,
                ))

        return standings

    # ------------------------------------------------------------------
    # HTML generation
    # ------------------------------------------------------------------

    def generate_series_html(self, standings: list[SeriesEntry]) -> str:
        """Generate HTML tables grouped by category, highest points first.

        Replicates the legacy app's format: <h2> category header followed
        by a <table> with Points | Name columns.
        """
        # Sort: by category ascending, then by points descending within category
        sorted_standings = sorted(
            standings,
            key=lambda e: (e.category, -e.total_points, e.last_name, e.first_name),
        )

        parts: list[str] = []
        parts.append("<html><body>")

        current_category = ""
        for entry in sorted_standings:
            if entry.category != current_category:
                if current_category:
                    parts.append("</table>")
                parts.append(f"<h2>{entry.category}</h2>")
                parts.append('<table border=1 cellspacing=0 cellpadding=10>')
                current_category = entry.category

            parts.append(
                f"<tr><td>{entry.total_points}</td>"
                f"<td>{entry.display_name}</td></tr>"
            )

        if current_category:
            parts.append("</table>")

        parts.append("</body></html>")
        return "\n".join(parts) + "\n"
