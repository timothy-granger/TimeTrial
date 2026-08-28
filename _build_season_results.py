"""Build the 2026 season-results archive page for the GitHub Pages site.

Parses the four race result HTMLs (each has a "Category Results" and an
"Overall Results" <pre> section with finish times) and emits a single dark,
mobile-friendly page showing all four races, newest first, with two tabs:
Overall and By Category. A link to the series standings sits at the bottom.

    python _build_season_results.py   ->  results/season-index.html

Copy the output to the tt-live-results repo as index.html to publish.
"""

import html
import re
from pathlib import Path

# newest first
RACE_FILES = [
    ("Aug 27, 2026", "results/2026.08.27.tt-results.html"),
    ("Jul 30, 2026", "results/2026.07.30.tt-results.html"),
    ("Jun 25, 2026", "results/tt-results-final-2026-06-25.html"),
    ("May 28, 2026", "results/tt-results-final-2026-05-28.html"),
]

TITLE = "2026 Time Trial Series"
STANDINGS_URL = "https://timothy-granger.github.io/tt-live-results/standings-2026.html"

TIME_RE = re.compile(r"\d\d:\d\d:\d\d\.\d")
CAT_LINE_RE = re.compile(r"^(.*?)\s+(\d\d:\d\d:\d\d\.\d)\s+(.*)$")
OVERALL_LINE_RE = re.compile(r"^\s*(\d+)\)\s+(\d\d:\d\d:\d\d\.\d)\s+(.*?)\s{2,}(.*)$")


def fix_name(name):
    """Title-case any ALL-CAPS surname (e.g. 'SHIMANSKIY' -> 'Shimanskiy')."""
    return " ".join(w.capitalize() if w.isupper() else w for w in name.split())


def fix_time(t):
    """Drop a leading '00:' hours field for readability (21:31.2)."""
    return t[3:] if t.startswith("00:") else t


def section(text, heading):
    """Return the <pre> body under a given <h2> heading, or ''."""
    m = re.search(re.escape(f"<h2>{heading}</h2>") + r"\s*<pre>\n(.*?)</pre>", text, re.S)
    return m.group(1) if m else ""


def parse_race(path):
    text = Path(path).read_text(encoding="utf-8")

    overall = []
    for line in section(text, "Overall Results").splitlines():
        m = OVERALL_LINE_RE.match(line)
        if m:
            place, t, name, cat = m.groups()
            overall.append({
                "place": int(place), "time": fix_time(t),
                "name": fix_name(name.strip()), "category": cat.strip(),
            })

    # Category section: group consecutive lines by category, preserving order
    categories = []  # list of (category, [ {time, name} ])
    by_cat = {}
    for line in section(text, "Category Results").splitlines():
        m = CAT_LINE_RE.match(line)
        if not m:
            continue
        cat, t, name = m.group(1).strip(), m.group(2), m.group(3).strip()
        if cat not in by_cat:
            by_cat[cat] = []
            categories.append((cat, by_cat[cat]))
        by_cat[cat].append({"time": fix_time(t), "name": fix_name(name)})

    return {"overall": overall, "categories": categories}


def esc(s):
    return html.escape(s)


def place_class(n):
    return {1: "p1", 2: "p2", 3: "p3"}.get(n, "")


def render_overall(races):
    out = ['<div id="overall" class="view">']
    for label, race in races:
        rows = race["overall"]
        out.append(f'<div class="race-title">{esc(label)} <span class="count">{len(rows)} finishers</span></div>')
        out.append('<div class="tablewrap"><table>')
        out.append("<thead><tr><th>#</th><th>Time</th><th>Rider</th><th>Category</th></tr></thead><tbody>")
        for r in rows:
            pc = place_class(r["place"])
            out.append(
                f'<tr><td class="pos {pc}">{r["place"]}</td>'
                f'<td class="time">{esc(r["time"])}</td>'
                f'<td class="rider {pc}">{esc(r["name"])}</td>'
                f'<td class="cat-cell">{esc(r["category"])}</td></tr>'
            )
        out.append("</tbody></table></div>")
    out.append("</div>")
    return "\n".join(out)


def render_categories(races):
    out = ['<div id="category" class="view" style="display:none">']
    for label, race in races:
        out.append(f'<div class="race-title">{esc(label)}</div>')
        for cat, riders in race["categories"]:
            out.append(f'<div class="cat">{esc(cat)}</div>')
            out.append('<div class="tablewrap"><table>')
            out.append("<thead><tr><th>#</th><th>Time</th><th>Rider</th></tr></thead><tbody>")
            for i, r in enumerate(riders, start=1):
                pc = place_class(i)
                out.append(
                    f'<tr><td class="pos {pc}">{i}</td>'
                    f'<td class="time">{esc(r["time"])}</td>'
                    f'<td class="rider {pc}">{esc(r["name"])}</td></tr>'
                )
            out.append("</tbody></table></div>")
    out.append("</div>")
    return "\n".join(out)


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  background: #0a0a1a; color: #e8e8f0; min-height: 100vh; }
.header { background: linear-gradient(135deg, #16213e 0%, #0f3460 100%); padding: 22px 20px;
  text-align: center; border-bottom: 3px solid #e94560; }
.header h1 { font-size: 21px; font-weight: 700; color: #fff; }
.header .sub { font-size: 12px; color: #a8b8d0; margin-top: 5px; text-transform: uppercase; letter-spacing: 1px; }
.tabs { display: flex; background: #111128; border-bottom: 1px solid #252540; position: sticky; top: 0; z-index: 5; }
.tab { flex: 1; padding: 13px 10px; cursor: pointer; font-size: 14px; font-weight: 600; color: #6070a0;
  text-align: center; border-bottom: 3px solid transparent; transition: all 0.2s; }
.tab:hover { color: #a0b0d0; }
.tab.active { color: #fff; border-bottom-color: #e94560; }
.content { padding: 16px; max-width: 900px; margin: 0 auto; }
.race-title { font-size: 18px; font-weight: 700; color: #e94560; margin: 26px 0 10px;
  padding-bottom: 6px; border-bottom: 2px solid #252540; }
.race-title:first-child { margin-top: 4px; }
.race-title .count { font-size: 12px; font-weight: 600; color: #8890a0; background: #16213e;
  padding: 2px 8px; border-radius: 10px; margin-left: 6px; }
.cat { font-size: 14px; font-weight: 700; color: #a0b0d0; margin: 16px 0 4px; }
.tablewrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 6px; }
thead th { text-align: left; padding: 7px 8px; background: #16213e; color: #a0b0d0; font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #0f3460; }
tbody td { padding: 7px 8px; border-bottom: 1px solid #1a1a35; }
td.pos { color: #8890a0; width: 34px; }
td.time { font-family: 'Consolas','Courier New',monospace; color: #81c784; white-space: nowrap; }
td.rider { font-weight: 600; }
td.cat-cell { color: #a0b0d0; font-size: 13px; }
.p1 { color: #ffd700 !important; font-weight: 700; }
.p2 { color: #c0c0c0 !important; font-weight: 600; }
.p3 { color: #cd7f32 !important; font-weight: 600; }
.standings-link { display: block; max-width: 900px; margin: 30px auto 40px; text-align: center; }
.standings-link a { display: inline-block; background: linear-gradient(135deg, #16213e 0%, #0f3460 100%);
  color: #ffd700; text-decoration: none; font-weight: 700; font-size: 15px; padding: 14px 22px;
  border-radius: 10px; border: 1px solid #e94560; }
.standings-link a:hover { background: #1a3a5c; }
@media (max-width: 600px) {
  .header h1 { font-size: 18px; } table { font-size: 13px; }
  thead th, tbody td { padding: 6px 6px; } td.cat-cell { font-size: 12px; }
}
"""

JS = """
document.querySelectorAll('.tab').forEach(function (t) {
  t.addEventListener('click', function () {
    document.querySelectorAll('.tab').forEach(function (x) { x.classList.remove('active'); });
    t.classList.add('active');
    var view = t.dataset.view;
    document.getElementById('overall').style.display = (view === 'overall') ? '' : 'none';
    document.getElementById('category').style.display = (view === 'category') ? '' : 'none';
  });
});
"""


def build_page():
    races = [(label, parse_race(path)) for label, path in RACE_FILES]

    p = []
    p.append("<!DOCTYPE html>")
    p.append('<html lang="en"><head>')
    p.append('<meta charset="UTF-8">')
    p.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    p.append(f"<title>{esc(TITLE)} — Season Results</title>")
    p.append(f"<style>{CSS}</style>")
    p.append("</head><body>")
    p.append('<div class="header">')
    p.append(f"<h1>{esc(TITLE)}</h1>")
    p.append('<div class="sub">Season Results &middot; All 4 Races</div>')
    p.append("</div>")
    p.append('<div class="tabs">')
    p.append('<div class="tab active" data-view="overall">Overall</div>')
    p.append('<div class="tab" data-view="category">By Category</div>')
    p.append("</div>")
    p.append('<div class="content">')
    p.append(render_overall(races))
    p.append(render_categories(races))
    p.append("</div>")
    p.append('<div class="standings-link">')
    p.append(f'<a href="{STANDINGS_URL}">🏆 View 2026 Series Standings →</a>')
    p.append("</div>")
    p.append(f"<script>{JS}</script>")
    p.append("</body></html>")
    return "\n".join(p) + "\n", races


if __name__ == "__main__":
    page, races = build_page()
    out = Path("results/season-index.html")
    out.write_text(page, encoding="utf-8")
    print(f"Wrote {out}")
    for (label, _), (_, race) in zip(RACE_FILES, races):
        print(f"  {label}: {len(race['overall'])} overall, {len(race['categories'])} categories")
