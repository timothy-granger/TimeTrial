"""Build the 2026 TT Series Standings from the four race result HTMLs.

Encodes the finishing order (fastest-first) of each category in each race, as
read from the "Category Results" section of:
    results/tt-results-final-2026-05-28.html
    results/tt-results-final-2026-06-25.html
    results/2026.07.30.tt-results.html
    results/2026.08.27.tt-results.html

Scoring: 1st=5, 2nd=4, 3rd=3, 4th=2, 5th=1 (top 5 only), summed across the four
races per category. Ties on total points are broken by the head-to-head Race 4
finish; riders still level are marked "T" (alphabetical by last name) and go to
a push-up contest.

Writes two files from the same computed standings:
    results/tt-series-standings-2026.html   plain <pre> report (print/archive)
    results/standings-2026-web.html         dark, mobile-friendly page for the
                                            GitHub Pages site (matches the live
                                            results theme)
"""

# race key -> {category: [finishers in order, 1st ... last]}
RACES = {
    "may": {  # 2026-05-28
        "Masters 50+ - Men": ["David Hoenicke", "Randy Tyner"],
        "Masters 60+ - Men": ["James Martin", "Mike Askew", "Chip Palmer"],
        "Masters 60+ - Women": ["Michelle Edwards"],
        "Masters 70+ - Men": ["Glynn Clements"],
        "Men (4/5/U)": ["Neil Tabor", "Clint Swofford", "Weston Studer", "Lucas Campbell"],
        "Men (P/1/2/3)": ["Colin Mathern"],
        "Merckx - Men": ["Nathan Race", "Samuel Shimanskiy", "Byron Meinerth", "Jay Patel", "Boyd Owens"],
        "Merckx - Women": ["Tara Miller"],
        "Women (4/U)": ["Kayla Rector"],
    },
    "jun": {  # 2026-06-25
        "Juniors (F)": ["Anna Tabor", "Brooke Tabor"],
        "Masters 50+ - Men": ["David Hoenicke", "Reggie Frye", "Dave McQuaid"],
        "Masters 60+ - Men": ["James Martin", "Kevin Parker", "Mike Askew"],
        "Masters 60+ - Women": ["Michelle Edwards"],
        "Masters 70+ - Men": ["Glynn Clements"],
        "Men (4/5/U)": ["Clint Swofford", "Weston Studer"],
        "Men (P/1/2/3)": ["Colin Mathern", "Coleman Hunt", "Michael Mauhar", "Marcus Jones", "Tyler Clem"],
        "Merckx - Men": ["Matthew Mauhar", "Brock Helms"],
        "Women (4/U)": ["Kayla Rector", "Amanda Pospischil"],
    },
    "jul": {  # 2026-07-30
        "Masters 60+ - Men": ["James Martin", "Bill Radler"],
        "Masters 60+ - Women": ["Michelle Edwards"],
        "Masters 70+ - Men": ["Glynn Clements"],
        "Men (4/5/U)": ["Clint Swofford", "Jerry Brown", "Christopher Octa", "Chris Hartzler"],
        "Men (P/1/2/3)": ["Colin Mathern", "Chris Olson", "Tyler Clem"],
        "Merckx - Men": ["Matthew Mauhar", "Jonathan Pait", "Daniel Leedy", "Ethan Thompson", "Grant Hiriak"],
        "Women (4/U)": ["Kayla Rector"],
    },
    "aug": {  # 2026-08-27
        "Masters 50+ - Men": ["Randy Tyner", "Dave Hiriak"],  # "Randall Tyner" in source = May's Randy Tyner
        "Masters 60+ - Men": ["James Martin"],
        "Masters 60+ - Women": ["Michelle Edwards"],
        "Masters 70+ - Men": ["Glynn Clements"],
        "Men (4/5/U)": ["Neil Tabor", "Chris Hartzler"],
        "Men (P/1/2/3)": ["Tyler Clem"],
        "Merckx - Men": ["Samuel Shimanskiy", "Jonathan Pait", "Ethan Thompson", "Grant Hiriak"],  # "Sam" in source
        "Women (4/U)": ["Kayla Rector"],
    },
}

RACE_ORDER = ["may", "jun", "jul", "aug"]
RACE_LABELS = {"may": "May 28", "jun": "Jun 25", "jul": "Jul 30", "aug": "Aug 27"}  # column headers
RACE_DATES = {"may": "May 28", "jun": "June 25", "jul": "July 30", "aug": "August 27"}  # full-month, intro line
SERIES_RACE_COUNT = 4  # races in the full season
PLACE_POINTS = [5, 4, 3, 2, 1]  # index = place - 1

TITLE = "2026 Greenville Spinners Time Trial Series"


def points_for(place_index):
    return PLACE_POINTS[place_index] if place_index < len(PLACE_POINTS) else 0


# category -> rider -> {race: points}
standings = {}
for race in RACE_ORDER:
    for category, finishers in RACES[race].items():
        cat = standings.setdefault(category, {})
        for i, rider in enumerate(finishers):
            cat.setdefault(rider, {})[race] = points_for(i)


def last_name(name):
    return name.split()[-1].lower()


def ranked_rows(riders):
    """Rank a category's riders and return structured rows.

    riders: {rider: {race: points}}. Ranking key is (total, Race-4 points):
    total decides first, then the head-to-head Race 4 finish breaks ties (in a
    category, more Race 4 points == a higher Race 4 place). Riders equal on BOTH
    stay tied (``tie=True``, marked "T") and go to the push-up contest.

    Returns a list of dicts: {pos, rank, tie, rider, total, cells{race: str}}.
    """
    tiebreak_race = RACE_ORDER[-1]
    rows = []
    for rider, per_race in riders.items():
        total = sum(per_race.values())
        tiebreak = per_race.get(tiebreak_race, 0)
        rows.append((rider, per_race, total, tiebreak))
    # order: total desc, then Race 4 points desc, then last name, then full name
    rows.sort(key=lambda r: (-r[2], -r[3], last_name(r[0]), r[0].lower()))

    scores = [(r[2], r[3]) for r in rows]  # (total, Race-4 points) per rider
    out = []
    for rider, per_race, total, tiebreak in rows:
        score = (total, tiebreak)
        better = sum(1 for s in scores if s > score)
        same = sum(1 for s in scores if s == score)
        rank = better + 1
        tie = same > 1
        out.append({
            "pos": ("T" if tie else "") + str(rank),
            "rank": rank,
            "tie": tie,
            "rider": rider,
            "total": total,
            "cells": {r: ("-" if per_race.get(r) is None else str(per_race[r])) for r in RACE_ORDER},
        })
    return out


def intro_html():
    dates = ", ".join(RACE_DATES[r] for r in RACE_ORDER)
    return (
        f"<b>Final standings</b> &mdash; all {SERIES_RACE_COUNT} races: {dates}, 2026. "
        "Points per race: 1st = 5, 2nd = 4, 3rd = 3, 4th = 2, 5th = 1 "
        "(top 5 in each category). &ldquo;-&rdquo; = did not race that date."
    )


TIE_NOTE = (
    "Ties on total points were broken by the head-to-head <b>Race 4</b> finish. Riders "
    "still level after Race 4 share a position (marked &ldquo;T&rdquo;, listed alphabetically "
    "by last name) and are settled by a <b>push-up contest</b>."
)


# ---------------------------------------------------------------------------
# Plain <pre> report (unchanged format — print/archive)
# ---------------------------------------------------------------------------

def build_table(category, riders):
    lines = []
    race_headers = "  ".join(f"{RACE_LABELS[r]:>6}" for r in RACE_ORDER)
    header = f"{'Pos':>3}  {'Rider':<22}{race_headers}  {'Total':>6}"
    lines.append(header)
    lines.append("-" * len(header))
    for row in ranked_rows(riders):
        race_cells = "  ".join(f"{row['cells'][r]:>6}" for r in RACE_ORDER)
        lines.append(f"{row['pos']:>3}  {row['rider']:<22}{race_cells}  {row['total']:>6}")
    return "\n".join(lines)


def build_plain_report():
    parts = ["<html><body>"]
    parts.append(f"<h1>{TITLE} &mdash; Series Standings</h1>")
    parts.append(f"<p>{intro_html()}</p>")
    parts.append(f"<p>{TIE_NOTE}</p>")
    for category in sorted(standings):
        parts.append(f"<h2>{category}</h2>")
        parts.append("<pre>")
        parts.append(build_table(category, standings[category]))
        parts.append("</pre>")
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Dark, mobile-friendly web page (GitHub Pages — matches live results theme)
# ---------------------------------------------------------------------------

WEB_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  background: #0a0a1a; color: #e8e8f0; min-height: 100vh; padding-bottom: 30px; }
.header { background: linear-gradient(135deg, #16213e 0%, #0f3460 100%); padding: 22px 20px;
  text-align: center; border-bottom: 3px solid #e94560; }
.header h1 { font-size: 20px; font-weight: 700; color: #fff; }
.header .sub { font-size: 12px; color: #a8b8d0; margin-top: 5px; text-transform: uppercase; letter-spacing: 1px; }
.content { padding: 16px; max-width: 900px; margin: 0 auto; }
.intro { font-size: 13px; color: #a8b8d0; margin-bottom: 10px; line-height: 1.5; }
.cat { font-size: 17px; font-weight: 700; color: #e94560; margin: 24px 0 8px;
  padding-bottom: 6px; border-bottom: 1px solid #252540; }
.tablewrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
thead th { text-align: right; padding: 7px 8px; background: #16213e; color: #a0b0d0;
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #0f3460; }
thead th:nth-child(2) { text-align: left; }
tbody td { padding: 7px 8px; border-bottom: 1px solid #1a1a35; text-align: right; }
td.rider { text-align: left; font-weight: 600; white-space: nowrap; }
td.pos { color: #8890a0; width: 44px; }
td.pt { color: #81c784; font-family: 'Consolas','Courier New',monospace; }
td.pt.none { color: #3a4260; }
td.total { color: #64b5f6; font-weight: 700; }
tr.champ td.rider, tr.champ td.pos { color: #ffd700; }
tr.tie td { font-style: italic; color: #b6b6c8; }
.foot { margin-top: 28px; text-align: center; font-size: 12px; color: #5060a0; }
@media (max-width: 600px) {
  .header h1 { font-size: 17px; } table { font-size: 13px; }
  thead th, tbody td { padding: 6px 6px; }
}
"""


def build_web_page():
    p = []
    p.append("<!DOCTYPE html>")
    p.append('<html lang="en"><head>')
    p.append('<meta charset="UTF-8">')
    p.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    p.append(f"<title>{TITLE} — Standings</title>")
    p.append(f"<style>{WEB_CSS}</style>")
    p.append("</head><body>")
    p.append('<div class="header">')
    p.append(f"<h1>{TITLE}</h1>")
    p.append('<div class="sub">Final Series Standings</div>')
    p.append("</div>")
    p.append('<div class="content">')
    p.append(f'<p class="intro">{intro_html()}</p>')
    p.append(f'<p class="intro">{TIE_NOTE}</p>')

    for category in sorted(standings):
        p.append(f'<div class="cat">{category}</div>')
        p.append('<div class="tablewrap"><table>')
        head = "".join(f"<th>{RACE_LABELS[r]}</th>" for r in RACE_ORDER)
        p.append(f"<thead><tr><th>Pos</th><th>Rider</th>{head}<th>Total</th></tr></thead><tbody>")
        for row in ranked_rows(standings[category]):
            champ = row["rank"] == 1 and not row["tie"]
            cls = "champ" if champ else ("tie" if row["tie"] else "")
            trophy = " \U0001F3C6" if champ else ""
            cells = "".join(
                f'<td class="pt{" none" if row["cells"][r] == "-" else ""}">{row["cells"][r]}</td>'
                for r in RACE_ORDER
            )
            p.append(
                f'<tr class="{cls}"><td class="pos">{row["pos"]}</td>'
                f'<td class="rider">{row["rider"]}{trophy}</td>'
                f'{cells}<td class="total">{row["total"]}</td></tr>'
            )
        p.append("</tbody></table></div>")

    p.append('<p class="foot">Greenville Spinners Time Trial Series &middot; Presented by Velo Valets</p>')
    p.append("</div></body></html>")
    return "\n".join(p) + "\n"


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    plain_out = r"D:\TimeTrial_Refactor\results\tt-series-standings-2026.html"
    with open(plain_out, "w", encoding="utf-8") as f:
        f.write(build_plain_report())
    print(f"Wrote {plain_out}")

    web_out = r"D:\TimeTrial_Refactor\results\standings-2026-web.html"
    with open(web_out, "w", encoding="utf-8") as f:
        f.write(build_web_page())
    print(f"Wrote {web_out}")
