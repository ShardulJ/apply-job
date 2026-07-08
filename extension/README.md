# Apply Job extension

A Chrome extension that scrapes the job posting on the current tab
(LinkedIn, Greenhouse, or Lever) and sends it to the local backend for
analysis: match score, apply/flag/skip decision, tweaked resume bullets,
and any resume style violations.

This talks to the backend at `http://localhost:8000`, so the FastAPI
server (`backend/main.py`) needs to be running first.

## Loading it in Chrome

1. Start the backend:
   ```bash
   cd backend
   python main.py
   ```
2. Open `chrome://extensions` in Chrome.
3. Turn on **Developer mode** (top right toggle).
4. Click **Load unpacked**.
5. Select this `extension/` folder.
6. The "Apply Job" extension should now appear in your extensions list and
   toolbar.

## Using it

1. Open a job posting on LinkedIn (`linkedin.com/jobs/...`), Greenhouse
   (`*.greenhouse.io`), or Lever (`*.lever.co`).
2. Click the Apply Job icon in the Chrome toolbar.
3. Click **Analyze This Job**.

If the page isn't a supported job posting, or the backend isn't running,
the popup shows a plain-language error instead of failing silently.

## Reloading after changes

Chrome caches unpacked extensions. After editing any file in this folder,
go back to `chrome://extensions` and click the refresh icon on the Apply
Job card to pick up the changes.
