"""Build the 2026 TT Series Standings report from the three race result HTMLs.

Encodes the finishing order (fastest-first) of each category in each race, as
read from:
    results/tt-results-final-2026-05-28.html
    results/tt-results-final-2026-06-25.html
    results/2026.07.30.tt-results.html

Scoring: 1st=5, 2nd=4, 3rd=3, 4th=2, 5th=1 (top 5 only). Totals are summed
across the three races per category. Ties are left tied (shared position,
marked "T"); tied riders are listed alphabetically by last name. Ties are
broken by Race 4, then a push-up contest.
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


def build_table(category, riders):
    # riders: {rider: {race: points}}
    # Ranking key is (total, Race-4 points): total decides first, then the
    # head-to-head Race 4 finish breaks ties (in a category, more Race 4 points
    # == a higher Race 4 finish). Riders equal on BOTH remain tied ("T") and go
    # to the push-up contest.
    tiebreak_race = RACE_ORDER[-1]
    rows = []
    for rider, per_race in riders.items():
        total = sum(per_race.values())
        tiebreak = per_race.get(tiebreak_race, 0)
        rows.append((rider, per_race, total, tiebreak))
    # order: total desc, then Race 4 points desc, then last name, then full name
    rows.sort(key=lambda r: (-r[2], -r[3], last_name(r[0]), r[0].lower()))

    scores = [(r[2], r[3]) for r in rows]  # (total, Race-4 points) per rider
    lines = []
    race_headers = "  ".join(f"{RACE_LABELS[r]:>6}" for r in RACE_ORDER)
    header = f"{'Pos':>3}  {'Rider':<22}{race_headers}  {'Total':>6}"
    lines.append(header)
    lines.append("-" * len(header))
    for rider, per_race, total, tiebreak in rows:
        score = (total, tiebreak)
        better = sum(1 for s in scores if s > score)
        same = sum(1 for s in scores if s == score)
        rank = better + 1
        pos = ("T" if same > 1 else "") + str(rank)
        cells = []
        for race in RACE_ORDER:
            v = per_race.get(race)
            cells.append("-" if v is None else str(v))
        race_cells = "  ".join(f"{c:>6}" for c in cells)
        lines.append(
            f"{pos:>3}  {rider:<22}{race_cells}  {total:>6}"
        )
    return "\n".join(lines)


parts = []
parts.append("<html><body>")
parts.append("<h1>2026 Greenville Spinners Time Trial Series &mdash; Series Standings</h1>")
race_dates_text = ", ".join(RACE_DATES[r] for r in RACE_ORDER)
parts.append(
    f"<p><b>Final standings</b> &mdash; all {SERIES_RACE_COUNT} races: {race_dates_text}, 2026. "
    "Points per race: 1st = 5, 2nd = 4, 3rd = 3, 4th = 2, 5th = 1 "
    "(top 5 in each category). &ldquo;-&rdquo; = did not race that date.</p>"
)
parts.append(
    "<p>Ties on total points were broken by the head-to-head <b>Race 4</b> finish. Riders "
    "still level after Race 4 share a position (marked &ldquo;T&rdquo;, listed alphabetically "
    "by last name) and are settled by a <b>push-up contest</b>.</p>")

for category in sorted(standings):
    parts.append(f"<h2>{category}</h2>")
    parts.append("<pre>")
    parts.append(build_table(category, standings[category]))
    parts.append("</pre>")

parts.append("</body></html>")

out_path = r"D:\TimeTrial_Refactor\results\tt-series-standings-2026.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(parts) + "\n")

print(f"Wrote {out_path}")
