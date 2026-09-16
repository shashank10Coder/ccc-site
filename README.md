# Chanakya Competition Cracker (CCC) — Website

## HOW TO RUN THIS SITE (first time)

1. Install Python 3.10+ if you don't have it.
2. Open a terminal in this folder and run:
   ```
   pip install -r requirements.txt
   ```
3. Your `.env` file is already created for you (copied from `.env.example`).
   Open `.env` in Notepad and fill in:
   - `ADMIN_PASSWORD` — change this from the default
   - `SMTP_EMAIL` / `SMTP_PASSWORD` — for real OTP emails (Gmail App Password, see comments inside `.env`)
   - Leave `PAYMENTS_ENABLED=false` until you have your Cashfree keys
4. Start the site:
   ```
   python app.py
   ```
5. Open your browser to **http://localhost:5000**

To stop the site, press `CTRL + C` in the terminal.

## HOW TO ADD CONTENT (no coding needed)

Go to **http://localhost:5000/admin** and log in with the `ADMIN_USERNAME` /
`ADMIN_PASSWORD` from your `.env` file. From there you can:
- Upload PDFs (free or paid)
- Write blog posts (free or paid)
- Build MCQ test sets
- View registered students and their questions

Everything you add through the admin panel shows up on the live site immediately.

## IMPORTANT — READ BEFORE YOU LAUNCH PUBLICLY

- **Screenshots / screen recording cannot be blocked by any website.** This is
  an operating-system-level capability, not something HTML/CSS/JS can prevent.
  Nobody can truly stop this — treat any claim otherwise as false.
- **DevTools "closing the site" is not really possible.** Browsers don't allow
  JavaScript to force-close a tab. This site instead blurs the page and shows
  a warning when it detects DevTools opening — a realistic, honest version of
  that protection.
- The current setup uses JSON files as the database, which is great for
  getting started but has limits at real scale (a few thousand records is
  fine; if you grow much larger, consider a real database later).
- **Change `SECRET_KEY` and `ADMIN_PASSWORD` in `.env` before putting this
  anywhere public.** The defaults are not secure.
- This dev server (`python app.py`) is for testing only. For a real public
  launch, deploy behind a production server (e.g. Gunicorn) — ask your
  hosting provider (Hostinger, Render, PythonAnywhere, etc.) how they run
  Flask apps, since this varies by host.

## FOLDER GUIDE

- `app.py` — the entire backend, heavily commented
- `.env` — all your settings and passwords (never share this file)
- `data/*.json` — your database (users, pdfs, blogs, mcqs, questions, purchases)
- `templates/` — all the HTML pages
- `static/css/style.css` — the golden theme styling
- `static/js/` — site behaviour, security script, MCQ quiz engine
- `static/uploads/` — where uploaded PDFs, blog images, and profile pictures are stored

## KNOWN LIMITATION FLAGGED DURING BUILD

While testing, the signup → OTP verification flow was not fully re-confirmed
end-to-end due to a time constraint on this session (the individual pieces —
account creation, OTP generation, and the email-sending function — were each
tested and work correctly in isolation). Before you rely on this for real
users, test the full signup flow yourself once:
1. Go to `/signup`, create an account.
2. Check your terminal window — if SMTP isn't configured yet, the OTP code
   prints there directly (look for `[EMAIL NOT CONFIGURED]`).
3. Enter that code on the verification page and confirm you land on the
   homepage logged in, and that `/profile` loads correctly.

If anything misbehaves in that flow, it's most likely in the `/verify-otp`
route in `app.py` (Section 5) — the code is heavily commented to make this
easy to trace even without much Python back­ground, and you can also paste
the app.py file back to Claude to debug it in a fresh conversation.
