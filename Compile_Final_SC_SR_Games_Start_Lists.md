# Compile Final SC Senior Games Start Lists

**Purpose:** Generate updated 5K and 10K time trial start lists from the SC Senior Games registration website on race morning (May 7, 2026).

**Website:** https://sc.fusesport.com/competitions.asp?compID=1773561&id=1379

---

## What This Process Does

1. Fetches the main registration page to find all "Registrants" links
2. Follows each link to extract participant names by category and age group
3. Cleans up name casing issues (lowercase, ALL CAPS)
4. Generates two start list CSVs ready to import into the TimeTrial app
5. Cross-references riders against the Greenville Spinners history database

---

## Prerequisites

- Terminal open in `D:\TimeTrial_Refactor`
- Virtual environment available at `.venv\`
- Internet connection

---

## Step 1: Scrape Registrants from Website

Open Claude Code and paste this prompt:

```
Fetch the SC Senior Games cycling time trial registration page at:
https://sc.fusesport.com/competitions.asp?compID=1773561&id=1379

Extract all "Registrants" links from the page. Each link is a relative URL
like drawindividual.asp?id=XXXXXXX&seasonid=1379 with an associated category
(e.g. "Cycling - Womens - 5K Time Trial | 60-64").

Then fetch EVERY registrants link (full URL: https://sc.fusesport.com/drawindividual.asp?id=...&seasonid=1379)
and extract all participant names from each page.

Compile into a single CSV file at D:\TimeTrial_Refactor\sc_senior_games_registrants.csv with columns:
FIRST_NAME,LAST_NAME,EVENT,AGE_GROUP

Clean up name casing:
- Fix all-lowercase names (e.g. "steve" → "Steve")
- Fix ALL CAPS names (e.g. "DAVID" → "David")

Then generate two start list CSVs ready for the TimeTrial app:

For BOTH files, sort order is: Men first (by age group ascending, then alphabetically by last name),
then Women (same sorting). This ensures women are not caught by men during the race.

1. D:\TimeTrial_Refactor\sc_senior_games_5k_start_list.csv
   - Only riders registered for 5K events
   - 7-column format: BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, START_POSITION, FINISH_TIME, RESULT
   - Categories formatted as "Men 55-59", "Women 60-64", etc.
   - Bib numbers sequential starting at 1
   - Start positions at 0.5 increments (30-second intervals)
   - FINISH_TIME and RESULT set to --:--:--.---

2. D:\TimeTrial_Refactor\sc_senior_games_10k_start_list.csv
   - Same format, only riders registered for 10K events

Also cross-reference all riders against the history database at
C:\Users\Timothy\.timetrial\history.db to identify known Greenville Spinners riders.
Show their race count and personal best time.
```

---

## Step 2: Review the Output

Check the generated files:

- `sc_senior_games_registrants.csv` — raw scraped data (all registrations)
- `sc_senior_games_5k_start_list.csv` — ready to import for Race 1
- `sc_senior_games_10k_start_list.csv` — ready to import for Race 2

Verify:
- [ ] Rider count looks reasonable
- [ ] No duplicate riders within a single start list
- [ ] Name casing is clean
- [ ] Men are listed before Women
- [ ] Age groups are in ascending order within each gender
- [ ] Bib numbers are sequential
- [ ] Start positions are 0.5 increments

---

## Step 3: Import into the App

1. Launch the app:
   ```
   D:\TimeTrial_Refactor\.venv\Scripts\python.exe -m timetrial
   ```

2. For the 5K race: Start List tab → Import → select `sc_senior_games_5k_start_list.csv`

3. After the 5K: click New Race → Import → select `sc_senior_games_10k_start_list.csv`

---

## Technical Details

### Website Structure

The main page at `competitions.asp?compID=1773561&id=1379` lists cycling time trial categories with "Registrants" links. Each link points to `drawindividual.asp?id=XXXXXXX&seasonid=1379` which contains the participant names for that category/age group.

### Categories on the Website

| Category | Age Groups |
|----------|-----------|
| Cycling - Womens - 5K Time Trial | 60-64, 65-69, 70-74, 75-79 |
| Cycling - Womens - 10K Time Trial | 60-64, 65-69, 70-74, 75-79 |
| Cycling - Mens - 5K Time Trial | 55-59, 60-64, 65-69, 70-74, 75-79, 80-84, 85-89 |
| Cycling - Mens - 10K Time Trial | 55-59, 60-64, 65-69, 70-74, 75-79, 80-84 |

**Note:** The category IDs in the URLs may change if the website is updated. The scraping process discovers them dynamically from the main page, so it will adapt to any changes.

### Start List CSV Format

The app expects this 7-column format (matching legacy compatibility):

```
BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, START_POSITION, FINISH_TIME, RESULT
1,Burns,Robert,Men 55-59,0.5,--:--:--.---,--:--:--.---
2,Flesher,David,Men 55-59,1,--:--:--.---,--:--:--.---
```

### Start Order Rationale

Men start first, women last. This prevents faster men from catching slower women on the course. Within each gender, riders are ordered by age group (youngest first) then alphabetically. This clusters similar-speed riders together and makes it easier for the starter to manage.

---

## If Claude Code Is Not Available

You can manually scrape the data:

1. Open each "Registrants" link in a browser
2. Copy the names into a spreadsheet
3. Save as CSV with columns: FIRST_NAME, LAST_NAME, EVENT, AGE_GROUP
4. Run the start list generator:

```python
# From D:\TimeTrial_Refactor directory:
# Edit sc_senior_games_registrants.csv with the manual data, then run:

D:\TimeTrial_Refactor\.venv\Scripts\python.exe -c "
import csv

rows = []
with open('sc_senior_games_registrants.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        first = row['FIRST_NAME'].strip()
        last = row['LAST_NAME'].strip()
        if first.islower() or first.isupper():
            first = first.capitalize()
        if last.isupper():
            last = last.title()
        rows.append({'first': first, 'last': last, 'event': row['EVENT'], 'age': row['AGE_GROUP']})

for event_label, event_filter in [('5K', '5K'), ('10K', '10K')]:
    event_rows = [r for r in rows if event_filter in r['event']]
    event_rows.sort(key=lambda r: (1 if 'Womens' in r['event'] else 0, r['age'], r['last'], r['first']))

    filename = f'sc_senior_games_{event_label.lower()}_start_list.csv'
    with open(filename, 'w', newline='') as f:
        f.write('BIB_NUMBER, LAST_NAME, FIRST_NAME, CATEGORY, START_POSITION, FINISH_TIME, RESULT\r\n')
        pos = 0.5
        bib = 1
        for r in event_rows:
            gender = 'Women' if 'Womens' in r['event'] else 'Men'
            f.write(f'{bib},{r[\"last\"]},{r[\"first\"]},{gender} {r[\"age\"]},{pos},--:--:--.---,--:--:--.---\r\n')
            bib += 1
            pos += 0.5
    print(f'{filename}: {len(event_rows)} riders')
"
```
