"""Generate Google Forms setup instructions and test data for club TT events.

Creates:
    1. A step-by-step guide for creating the Google Form
    2. A sample CSV matching the Google Forms export format for testing

Usage:
    python -m timetrial.tools.create_registration_forms [output_dir]

    output_dir  Directory for generated files (default: registration/)
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

from timetrial.tools.registration_import import CLUB_CATEGORIES, WINDOW_ORDER


# ---------------------------------------------------------------------------
# Event schedule
# ---------------------------------------------------------------------------

EVENTS = [
    {"number": 1, "date": "2026-05-28", "label": "Race 1 — May 28, 2026"},
    {"number": 2, "date": "2026-06-25", "label": "Race 2 — June 25, 2026"},
    {"number": 3, "date": "2026-07-30", "label": "Race 3 — July 30, 2026"},
    {"number": 4, "date": "2026-08-27", "label": "Race 4 — August 27, 2026"},
]

WINDOW_LABELS = list(WINDOW_ORDER.keys())


# ---------------------------------------------------------------------------
# Google Form setup guide
# ---------------------------------------------------------------------------

FORM_GUIDE = """# Google Forms Setup — Greenville Spinners Time Trial Registration

## Create One Form Per Race

You'll create **4 separate Google Forms**, one for each race date.
The steps below are for one form — repeat for each event.

**Faster for races 2-4:** once Race 1's form exists, open it and use the
**⋮ menu → Make a copy** instead of building from scratch. The copy keeps every
field, all categories, and the settings — you only change the title/description
(Step 2) and link a fresh response spreadsheet (Step 5).

---

## Step-by-Step: Creating the Form

### 1. Go to Google Forms
   - Visit **forms.google.com** (sign in with your Google account)
   - Click **Blank form** (the + icon)

### 2. Set the Title and Description
   - **Title:** `Greenville Spinners Time Trial — {race_label}`
   - **Description:**
     ```
     Free registration for the Greenville Spinners community time trial.
     Please register by {deadline} so we can prepare the start list.
     You may edit your response after submitting.
     ```

### 3. Add Fields

   **Field 1: First Name**
   - Type: **Short answer**
   - Required: **Yes**

   **Field 2: Last Name**
   - Type: **Short answer**
   - Required: **Yes**

   **Field 3: Category**
   - Type: **Dropdown**
   - Required: **Yes**
   - Options (copy/paste each as a separate choice):
{category_list}

   **Field 4: Preferred Start Window**
   - Type: **Multiple choice**
   - Required: **Yes**
   - Options:
     - `Early (6:00 - 6:15)`
     - `Middle (6:16 - 6:30)`
     - `Late (6:31 - 6:45)`

### 4. Configure Form Settings
   - Click the **gear icon** (Settings) at the top
   - Under **Responses**:
     - Toggle ON: **Allow response editing** (lets riders change their category)
     - Toggle ON: **Collect email addresses** (optional — useful for announcements)
     - Toggle OFF: **Limit to 1 response** (leave OFF unless you want email-verified uniqueness)
   - Under **Presentation**:
     - Confirmation message: `You're registered! See you at the start line.`

### 5. Link to Google Sheets
   - Click the **Responses** tab at the top of the form
   - Click the **green Sheets icon** (Create Spreadsheet)
   - Choose **Create a new spreadsheet**
   - Name it: `TT Race {number} Registrations — {date}`

### 6. Share the Form
   - Click **Send** (top right)
   - Copy the link to share via email, social media, club website
   - The link will look like: `https://forms.gle/xxxxx`

---

## Before Race Day: Export the Start List

1. Open the linked Google Sheet
2. **File → Download → Comma Separated Values (.csv)**
3. Run the conversion tool:
   ```
   .venv/Scripts/python.exe -m timetrial.tools.registration_import registration.csv
   ```
4. Review the generated `tt-start-list.csv`
5. Import into the TimeTrial app: **Start List → Import**

---

## Editing Categories After the Form is Live

- Open the form in edit mode
- Click on the **Category** dropdown question
- Add, rename, or remove choices — existing responses are preserved
- New submissions will see the updated list

---

## Race Day Late Arrivals

Late arrivals are handled directly in the TimeTrial app:
- Click **Add Rider** in the Start List panel
- Assign the next available bib and start position
- No need to go back to the Google Form

---

## Event Schedule

| Race | Date | Form | Sheet |
|------|------|------|-------|
| 1 | May 28, 2026 | Create form | Link sheet |
| 2 | June 25, 2026 | Create form | Link sheet |
| 3 | July 30, 2026 | Create form | Link sheet |
| 4 | August 27, 2026 | Create form | Link sheet |

Fill in the Form and Sheet links as you create them.
"""


# ---------------------------------------------------------------------------
# Test data generation
# ---------------------------------------------------------------------------

SAMPLE_RIDERS = [
    ("Smith", "John"), ("Johnson", "Mike"), ("Williams", "David"),
    ("Brown", "Chris"), ("Jones", "Sarah"), ("Garcia", "Maria"),
    ("Miller", "James"), ("Davis", "Robert"), ("Rodriguez", "Ana"),
    ("Martinez", "Carlos"), ("Anderson", "Tom"), ("Taylor", "Lisa"),
    ("Thomas", "Mark"), ("Jackson", "Kevin"), ("White", "Amy"),
    ("Harris", "Brian"), ("Martin", "Susan"), ("Thompson", "Paul"),
    ("Moore", "Jennifer"), ("Clark", "Steve"), ("Lewis", "Karen"),
    ("Robinson", "Jeff"), ("Walker", "Laura"), ("Young", "Dan"),
    ("Allen", "Nancy"), ("King", "Greg"), ("Wright", "Michelle"),
    ("Scott", "Tim"), ("Green", "Rachel"), ("Baker", "Phil"),
    ("Adams", "Emily"), ("Nelson", "Rick"), ("Hill", "Donna"),
    ("Ramirez", "Luis"), ("Campbell", "Betty"), ("Mitchell", "Joe"),
    ("Roberts", "Linda"), ("Carter", "Frank"), ("Phillips", "Carol"),
    ("Evans", "Scott"), ("Turner", "Mary"), ("Torres", "Miguel"),
    ("Parker", "Diana"), ("Collins", "Ray"), ("Edwards", "Pam"),
]


def generate_test_csv(path: Path, num_riders: int = 45) -> None:
    """Generate a sample Google Forms CSV export for testing."""
    riders = SAMPLE_RIDERS[:num_riders]

    # Weight categories to match realistic distribution
    weighted_categories = (
        ["Merckx - Men"] * 12 +
        ["Merckx - Women"] * 5 +
        ["Men (4/5/U)"] * 8 +
        ["Men (P/1/2/3)"] * 5 +
        ["Women (4/U)"] * 3 +
        ["Women (P/1/2/3)"] * 1 +
        ["Masters 50+ - Men"] * 5 +
        ["Masters 50+ - Women"] * 2 +
        ["Masters 60+ - Men"] * 4 +
        ["Masters 60+ - Women"] * 1 +
        ["Masters 70+ - Men"] * 1 +
        ["Juniors (M)"] * 2 +
        ["Hand Cycle (M)"] * 1
    )

    # Weight windows: most want early, some middle, few late
    weighted_windows = (
        [WINDOW_LABELS[0]] * 5 +
        [WINDOW_LABELS[1]] * 3 +
        [WINDOW_LABELS[2]] * 2
    )

    random.seed(42)  # Reproducible output

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Timestamp", "Last Name", "First Name",
            "Category", "Preferred Start Window"
        ])

        for last, first in riders:
            cat = random.choice(weighted_categories)
            window = random.choice(weighted_windows)
            timestamp = "5/15/2026 10:30:00"  # Placeholder
            writer.writerow([timestamp, last, first, cat, window])

    print(f"  Test CSV written: {path} ({num_riders} riders)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("registration")
    output_dir.mkdir(exist_ok=True)

    # Build category list for the guide
    cat_lines = ""
    for cat in CLUB_CATEGORIES:
        cat_lines += f"     - `{cat}`\n"

    # Write the setup guide
    guide_text = FORM_GUIDE.format(
        race_label=EVENTS[0]["label"],
        deadline="the day before the race",
        number=1,
        date=EVENTS[0]["date"],
        category_list=cat_lines,
    )
    guide_path = output_dir / "Google_Forms_Setup_Guide.md"
    guide_path.write_text(guide_text, encoding="utf-8")
    print(f"  Setup guide written: {guide_path}")

    # Generate test CSV
    test_csv_path = output_dir / "test_registration_export.csv"
    generate_test_csv(test_csv_path)

    # Run a quick conversion preview
    print(f"\n--- Test conversion preview ---")
    from timetrial.tools.registration_import import (
        parse_registrations, build_start_list, print_start_list, print_summary
    )
    regs = parse_registrations(test_csv_path)
    riders = build_start_list(regs)
    print_start_list(riders)
    print_summary(riders)

    print(f"\n--- Files created in {output_dir}/ ---")
    print(f"  1. {guide_path.name}  — Step-by-step Google Form creation guide")
    print(f"  2. {test_csv_path.name}  — Sample CSV for testing the conversion tool")
    print(f"\nNext steps:")
    print(f"  1. Follow the guide to create your first Google Form")
    print(f"  2. Test the conversion tool:")
    print(f"     .venv/Scripts/python.exe -m timetrial.tools.registration_import {test_csv_path}")


if __name__ == "__main__":
    main()
