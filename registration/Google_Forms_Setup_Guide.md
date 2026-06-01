# Google Forms Setup — Greenville Spinners Time Trial Registration

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
   - **Title:** `Greenville Spinners Time Trial — Race 1 — May 28, 2026`
   - **Description:**
     ```
     Free registration for the Greenville Spinners community time trial.
     Please register by the day before the race so we can prepare the start list.
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
     - `Men (P/1/2/3)`
     - `Men (4/5/U)`
     - `Women (P/1/2/3)`
     - `Women (4/U)`
     - `Masters 50+ - Men`
     - `Masters 50+ - Women`
     - `Masters 60+ - Men`
     - `Masters 60+ - Women`
     - `Masters 70+ - Men`
     - `Masters 70+ - Women`
     - `Merckx - Men`
     - `Merckx - Women`
     - `Juniors (M)`
     - `Juniors (F)`
     - `Hand Cycle (M)`


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
   - Name it: `TT Race 1 Registrations — 2026-05-28`

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
