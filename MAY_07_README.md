# SC Senior Games — May 7, 2026 Race Day Instructions

## Event: Cycling Time Trial — 5K and 10K
**Location:** TBD
**Start Lists:** Pre-loaded from SC Senior Games registration (sc.fusesport.com)

---

## Pre-Race Setup

1. Open a terminal and launch the app:
   ```
   D:\TimeTrial_Refactor\.venv\Scripts\python.exe -m timetrial
   ```

2. Verify the starter display settings in `timetrial\config\default_config.toml`:
   - `race_title` — update if needed for Senior Games branding
   - `logo_image` — update path if using a different logo
   - `countdown_sound_trigger_seconds = 11` — sound plays 11 seconds before each start

---

## Race 1: 5K Time Trial (41 riders)

### Load Start List
1. Go to **Start List** tab
2. Click **Import** → select `D:\TimeTrial_Refactor\sc_senior_games_5k_start_list.csv`
3. Verify riders are loaded — 41 riders, men first then women
4. Start order:
   - Bibs 1-7: Men 55-59
   - Bibs 8-13: Men 60-64
   - Bibs 14-18: Men 65-69
   - Bibs 19-24: Men 70-74
   - Bibs 25-30: Men 75-79
   - Bibs 31-33: Men 80-84
   - Bib 34: Men 85-89
   - Bibs 35-36: Women 60-64
   - Bib 37: Women 65-69
   - Bibs 38-39: Women 70-74
   - Bibs 40-41: Women 75-79

### Open Starter Display
- Press **Ctrl+S** to open the starter display window
- Drag it to the secondary monitor facing the start line
- Shows: race title, rider name, countdown, bib number, race clock

### Start the Race
1. Click **Start Race** (or have everything ready and click when the first rider should go)
2. Riders depart every 30 seconds
3. The countdown and sound will trigger automatically
4. Total start time: ~20.5 minutes for all 41 riders

### Record Finishes
1. As each rider crosses the finish line, press **Ctrl+T**
   - This captures the exact timestamp
   - The cursor jumps to the Bib # field
2. Type the rider's **bib number** and press **Enter**
   - Name, category, and elapsed time auto-populate
   - If you enter a wrong bib, just retype — it will re-lookup
   - Unknown bibs show "(not found)" — no crash
3. You can record finishes from any tab — Ctrl+T works globally
4. Check the **Results** tab to see live category and overall standings

### Export 5K Results
1. Go to **Start List** tab → click **Export** → save as `sc_senior_games_5k_results.csv`
2. Go to **Finish Times** tab → click **Export** → save as `sc_senior_games_5k_finish_list.csv`
3. Click **Stop Race**

---

## Race 2: 10K Time Trial (38 riders)

### Reset for New Race
1. Click **New Race** button (next to Start/Stop in the Race Control bar)
2. Confirm when prompted — this clears all 5K data from the app
3. App switches to the Start List tab, ready for import

### Load 10K Start List
1. Click **Import** → select `D:\TimeTrial_Refactor\sc_senior_games_10k_start_list.csv`
2. Verify 38 riders loaded
3. Start order:
   - Bibs 1-7: Men 55-59
   - Bibs 8-13: Men 60-64
   - Bibs 14-18: Men 65-69
   - Bibs 19-24: Men 70-74
   - Bibs 25-29: Men 75-79
   - Bibs 30-32: Men 80-84
   - Bibs 33-34: Women 60-64
   - Bib 35: Women 65-69
   - Bib 36: Women 70-74
   - Bibs 37-38: Women 75-79

### Run the 10K
1. Press **Ctrl+S** if the starter display was closed (otherwise it's still open)
2. Click **Start Race**
3. Record finishes with **Ctrl+T** + bib number (same as 5K)
4. Total start time: ~19 minutes for all 38 riders

### Export 10K Results
1. **Start List** tab → **Export** → save as `sc_senior_games_10k_results.csv`
2. **Finish Times** tab → **Export** → save as `sc_senior_games_10k_finish_list.csv`
3. Click **Stop Race**

---

## Known Riders from Greenville Spinners History

Five registered riders have raced in Greenville Spinners time trials:

| Rider | Age Group | GS Races | GS Personal Best |
|-------|-----------|----------|-----------------|
| James Martin | 65-69 | 16 | 00:22:49 |
| Bill Radler | 65-69 | 15 | 00:23:45 |
| James Taylor | 70-74 | 8 | 00:30:01 |
| Alan Lesage | 70-74 | 5 | 00:25:59 |
| Colton Keasler | 60-64 | 1 | 00:32:52 |

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
