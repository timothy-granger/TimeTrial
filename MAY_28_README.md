# Greenville Spinners 2026 Time Trial #1 — May 28, 2026 Race Day Instructions

## Event: Community Time Trial
**Location:** TBD
**Start Time:** 6:00 PM
**Expected Riders:** ~60 (bibs 1-100 available)
**Registration:** Google Forms → [Registration Link](https://docs.google.com/forms/d/e/1FAIpQLSf2RbjFp_8K9AC3_NCr1A293IkLuuUj2OF5zPB_NLUfMafOPw/viewform)
**Live Results:** https://timothy-granger.github.io/tt-live-results/

---

## Night Before (May 27)

### Close Registration and Build Start List

1. Open the linked Google Sheet (TT Race 1 Registrations — May 28 2026)
2. **File → Download → Comma Separated Values (.csv)** — save to a known location
3. Open a terminal and run the conversion tool:
   ```
   cd D:\TimeTrial_Refactor
   .venv\Scripts\python.exe -m timetrial.tools.registration_import "path\to\downloaded.csv"
   ```
4. Review the output — riders are grouped by preferred start window (Early/Middle/Late), then by category
5. The tool creates `tt-start-list.csv` in the same folder as the input CSV
6. Copy or move the generated `tt-start-list.csv` to `D:\TimeTrial_Refactor\` if needed
7. Open the CSV and make any manual adjustments (e.g. swap two riders' positions if needed)

---

## Race Day — Noon

### Publish Start List to GitHub Pages

1. Open a terminal and run:
   ```
   cd D:\TimeTrial_Refactor
   .venv\Scripts\python.exe -m timetrial.tools.registration_import "path\to\downloaded.csv" --publish
   ```
   - This pushes the start list to GitHub Pages
   - The tool reads the race name and date from `C:\Users\Timothy\.timetrial\config.toml`
   - Riders can view their bib number, category, and start time at:
     **https://timothy-granger.github.io/tt-live-results/**
2. If you already generated the start list the night before and only need to publish:
   - Re-run the same command with `--publish` — it will regenerate and push

### Verify Config

Check that `C:\Users\Timothy\.timetrial\config.toml` has the correct race info:
```toml
[display]
race_title = "Greenville Spinners 2026 Time Trial #1"
event_info = "May 28, 2026"
```
Both the published start list and live race results use these values.

---

## Race Day — 5:30 PM Setup

### Launch the App

1. Open a terminal:
   ```
   D:\TimeTrial_Refactor\.venv\Scripts\python.exe -m timetrial
   ```

2. If prompted "Recover previous race?" → click **No** (unless recovering from a crash)

### Load Start List

1. Go to the **Start List** tab
2. Click **Import** → select `D:\TimeTrial_Refactor\tt-start-list.csv`
3. Verify riders are loaded with correct bibs, categories, and start positions
4. Start order follows preferred windows:
   - **Bibs 1-N:** Early window riders (6:00 - 6:15) grouped by category
   - **Next bibs:** Middle window riders (6:16 - 6:30) grouped by category
   - **Last bibs:** Late window riders (6:31 - 6:45) grouped by category

### Open Starter Display

- Press **Ctrl+S** to open the starter display window
- Drag it to the secondary monitor facing the start line
- Shows: race title, rider name, countdown, bib number, race clock

---

## Race Day — 6:00 PM

### Start the Race

1. Click **Start Race** when the first rider should go
2. Riders depart every 30 seconds
3. The countdown and start sound trigger automatically
4. Live results publish to GitHub Pages automatically (batched every 30 seconds)
   - The website automatically switches from showing the start list to showing live results once finishers are recorded

### Record Finishes

1. As each rider crosses the finish line, press **Ctrl+T**
   - This captures the exact timestamp
   - The cursor jumps to the Bib # field
2. Type the rider's **bib number** and press **Enter**
   - Name, category, and elapsed time auto-populate
   - If you enter a wrong bib, just retype — it will re-lookup
   - Unknown bibs show "(not found)" — no crash
3. You can record finishes from any tab — **Ctrl+T** works globally
4. Check the **Results** tab to see live category and overall standings

### Late Arrivals

Someone shows up at 6:35 wanting to race? No problem:
1. Go to the **Start List** tab
2. Click **Add Rider**
3. Enter their name, category, assign next available bib and start position
4. They're in the race — record their finish with Ctrl+T like everyone else

---

## After the Race

### Export Results

1. Go to **Start List** tab → click **Export** → save as `tt_race1_results.csv`
2. Go to **Finish Times** tab → click **Export** → save as `tt_race1_finish_list.csv`
3. Click **Stop Race**

### Clear Web Results

After you've exported everything and results are final:
1. Click **Clear Web Results** in the Race Control bar
2. Confirm when prompted — this clears the GitHub Pages site back to "Waiting for start list..."

---

## Categories (15)

| # | Category |
|---|----------|
| 1 | Men (P/1/2/3) |
| 2 | Men (4/5/U) |
| 3 | Women (P/1/2/3) |
| 4 | Women (4/U) |
| 5 | Masters 50+ - Men |
| 6 | Masters 50+ - Women |
| 7 | Masters 60+ - Men |
| 8 | Masters 60+ - Women |
| 9 | Masters 70+ - Men |
| 10 | Masters 70+ - Women |
| 11 | Merckx - Men |
| 12 | Merckx - Women |
| 13 | Juniors (M) |
| 14 | Juniors (F) |
| 15 | Hand Cycle (M) |

---

## Quick Reference

| Action | How |
|--------|-----|
| Record a finish | **Ctrl+T** then type bib number |
| Open starter display | **Ctrl+S** |
| Start race timer | Click **Start Race** |
| Stop race timer | Click **Stop Race** |
| Reset for next race | Click **New Race** |
| Import start list | Start List tab → **Import** |
| Export results | Start List tab → **Export** |
| Add late arrival | Start List tab → **Add Rider** |
| Clear web results | Race Control → **Clear Web Results** |

---

## Key File Locations

| File | Path |
|------|------|
| App launch | `D:\TimeTrial_Refactor\.venv\Scripts\python.exe -m timetrial` |
| Conversion tool | `.venv\Scripts\python.exe -m timetrial.tools.registration_import` |
| User config | `C:\Users\Timothy\.timetrial\config.toml` |
| Default config | `D:\TimeTrial_Refactor\timetrial\config\default_config.toml` |
| Start list template | `D:\TimeTrial_Refactor\tt-start-list.csv` |
| Sound file | `D:\TimeTrial_Refactor\distro\start.m4a` |
| Live results repo | `D:\tt-live-results` |
| Form setup guide | `D:\TimeTrial_Refactor\registration\Google_Forms_Setup_Guide.md` |

---

## Troubleshooting

**App won't start:**
- Make sure you're using the venv Python: `D:\TimeTrial_Refactor\.venv\Scripts\python.exe -m timetrial`

**No sound on countdown:**
- Check that `distro\start.m4a` exists
- Check `default_config.toml` → `sound_file` path is correct

**Starter display shows no clock:**
- Open the starter display (Ctrl+S) before or after starting the race — both work

**Wrong bib entered:**
- Just retype the correct bib number in the same row — it will re-lookup

**App crashes mid-race:**
- Relaunch the app — it will ask "Recover previous race?" → click Yes
- All riders and finish times recorded up to the crash point are restored

**Need to edit a finish time:**
- Go to Finish Times tab, double-click the finish time cell, adjust in the dialog

**Conversion tool shows warnings:**
- "Unknown category" — rider entered a category not in the dropdown (e.g. form was edited). Fix in the CSV or add them manually in the app
- "Missing name" — blank row in the Google Sheet, skipped automatically

**Start list not showing on website:**
- Make sure you ran with `--publish` flag
- Check that `D:\tt-live-results` repo exists and git push succeeded
- GitHub Pages can take 1-2 minutes to update

**Live results not updating during race:**
- Check the status bar at the bottom of the app for publish errors
- Verify internet connection
- Results batch every 30 seconds — there's a brief delay

---

## Preparing for Race #2

1. Update `C:\Users\Timothy\.timetrial\config.toml`:
   ```toml
   [display]
   race_title = "Greenville Spinners 2026 Time Trial #2"
   event_info = "TBD"
   ```
2. Create a new Google Form (follow `registration\Google_Forms_Setup_Guide.md`)
3. Share the new form link with the club
4. Repeat this workflow
