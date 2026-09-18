# Job Email Sorter

A small program that watches your Gmail inbox, uses Claude to figure out
which emails are about job applications you've sent, and automatically
files them into Gmail labels (which work like folders):

- **Job Applications/Application Received** — "thank you for applying" type confirmations
- **Job Applications/Action Needed** — they want more documents, a pre-screening, an assessment, etc. *(notifies you)*
- **Job Applications/Not Moving Forward** — rejections / declines
- **Job Applications/Interview - Moving Forward** — interview requests, "moving forward," offers *(notifies you)*

Everything else in your inbox is left alone.

The two time-sensitive categories (Action Needed, Interview) trigger both a
desktop popup on your computer and, optionally, a push notification straight
to your phone via [ntfy.sh](https://ntfy.sh) — no dedicated cloud server or
app store account required.

It runs on your own computer (Windows, macOS, or Linux) — nothing is
uploaded anywhere except: (1) to Google, to read/label your Gmail via
Google's own official API, (2) to Anthropic, to classify each email's text
with Claude, and (3) to ntfy.sh, only for the two notify-worthy categories,
if you set up phone push notifications.

---

## One-time setup (about 10–15 minutes)

You need two things: **Gmail API access** and a **Claude API key**.

### 1. Enable the Gmail API and get `credentials.json`

1. Go to https://console.cloud.google.com/ and sign in with the Google
   account for the Gmail inbox you want sorted.
2. Click the project dropdown at the top → **New Project**. Name it
   anything (e.g. "Email Sorter") → **Create**.
3. With that project selected, go to **APIs & Services → Library**, search
   for **Gmail API**, and click **Enable**.
4. Go to **APIs & Services → OAuth consent screen**.
   - User Type: **External** → Create.
   - Fill in an app name (e.g. "Email Sorter"), your email for the support
     email and developer contact fields → Save and Continue through the
     remaining steps (you can leave scopes/test users default and click
     through).
   - On the **Test users** step, click **Add users** and add your own
     Gmail address. (While the app is in "testing" mode, only accounts you
     list here can use it — that's fine, it's just you.)
5. Go to **APIs & Services → Credentials → Create Credentials → OAuth
   client ID**.
   - Application type: **Desktop app**.
   - Name it anything → **Create**.
   - Click **Download JSON** on the credential you just created.
6. Rename the downloaded file to exactly `credentials.json` and put it in
   this same folder, next to `main.py`.

You will NOT need to touch the Google Cloud Console again after this.

### 2. Get a Claude API key

1. Go to https://console.anthropic.com/settings/keys and sign in
   (or create an account).
2. Create a new API key and copy it.
3. Anthropic API usage is billed pay-as-you-go separately from any Claude
   subscription you may have; you'll need to add a small amount of credit
   at https://console.anthropic.com/settings/billing. Classifying emails
   this way is very cheap — typically a fraction of a cent per email, so
   normal job-search email volume should cost well under a dollar a month.

### 3. (Optional) Set up phone push notifications via ntfy.sh

Skip this step if you only want the desktop popup — push notifications are
fully optional and controlled by one setting.

1. Install the **ntfy** app on your phone: [iOS](https://apps.apple.com/us/app/ntfy/id1625396347) / [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy).
2. Pick a "topic" name — this acts like a private channel name. Anyone who
   knows it can send to (and read) it, since public ntfy.sh topics aren't
   password-protected, so make it long and hard to guess rather than
   something like `kyle-jobs`. For example:
   `kyle-job-alerts-7f3ma91qz2`.
3. In the ntfy app, tap **+** (Subscribe to topic) and enter that exact
   topic name.
4. You'll fill this topic name into your `.env` file in the next step.

(If you'd rather self-host ntfy or use Pushover/Telegram instead down the
line, ask me — the notifier is written so swapping the push service later
is a small, contained change.)

### 4. Configure the program

1. In this folder, copy `.env.example` to a new file named exactly `.env`.
2. Open `.env` and paste your Claude API key in for `ANTHROPIC_API_KEY`.
3. If you set up ntfy above, paste your topic name into `NTFY_TOPIC`.
   Leave it blank to skip phone push notifications.
4. (Optional) Adjust `POLL_INTERVAL_SECONDS` (how often it checks your
   inbox) or the other settings — the defaults are reasonable.

### 5. Install Python dependencies

You need Python 3.9+ installed (check with `python3 --version`; on
Windows use `python --version`). Then, in this folder, run:

```
pip install -r requirements.txt
```

(On macOS/Linux you may need `pip3` instead of `pip`.)

### 6. First run

```
python main.py
```

The first time you run it, a browser window will open asking you to log in
to Google and approve access. Since the app is in "testing" mode, Google
will show an "unverified app" warning — click **Advanced → Go to Email
Sorter (unsafe)**. This is expected for a personal script only you use; it
just means Google hasn't manually reviewed the app, not that anything is
actually wrong. After you approve, it saves a `token.json` file so you
won't need to log in again.

It will then create the four labels in your Gmail automatically and start
watching your inbox, printing what it's doing to the terminal:

```
Watching your inbox every 300 seconds. Press Ctrl+C to stop.

[2026-09-18 09:00:00] Checking inbox...
  Checking 3 new email(s)...
  - Filed as [confirmation] -> Job Applications/Application Received: Thank you for applying to...
  - Filed as [interview] -> Job Applications/Interview - Moving Forward: Let's schedule a call!
  - Skipping (not job-related): Your weekly newsletter
```

Leave the terminal window open and it will keep checking on the interval
you set. Press `Ctrl+C` to stop it.

**Note on the first run specifically:** to avoid reclassifying your entire
email history the very first time, it only looks back `INITIAL_LOOKBACK_DAYS`
(14, by default — change this in `.env`) days. Every run after that checks
everything new since the last check.

---

## Running it continuously without keeping a terminal open

The simplest option is `python main.py` in a terminal you leave running.
If you'd rather it run in the background automatically:

**Windows:** Use Task Scheduler to run
`pythonw.exe C:\path\to\this\folder\main.py --once` on a repeating trigger
(e.g. every 5–10 minutes) — `--once` checks the inbox one time and exits,
which suits a scheduler better than the continuous loop. Set "Start in"
to this folder so it can find its files.

**macOS:** Use `launchd`. Create a file at
`~/Library/LaunchAgents/com.you.emailsorter.plist` that runs
`/usr/bin/python3 /path/to/this/folder/main.py --once` on an interval
(`StartInterval` in seconds), then load it with
`launchctl load ~/Library/LaunchAgents/com.you.emailsorter.plist`.

**Linux:** Add a cron entry, e.g. `crontab -e` and add:
```
*/5 * * * * cd /path/to/this/folder && /usr/bin/python3 main.py --once >> sorter.log 2>&1
```

Ask me if you'd like exact, filled-in commands/files for whichever OS
you're using — I can write the scheduler file for you directly.

---

## Files in this folder

| File | Purpose |
|---|---|
| `main.py` | Entry point — run this |
| `config.py` | Loads settings from `.env` |
| `gmail_auth.py` | Handles Google sign-in |
| `gmail_actions.py` | Reads emails, creates labels, files messages |
| `classifier.py` | Asks Claude to categorize each email |
| `notifier.py` | Desktop popups + optional ntfy.sh phone push notifications |
| `state.py` | Remembers which emails were already checked |
| `requirements.txt` | Python dependencies |
| `.env.example` | Template for your settings — copy to `.env` |
| `credentials.json` | **You provide this** (Gmail OAuth credentials, step 1 above) |
| `token.json` | Auto-created after your first login |
| `processed_state.json` | Auto-created; tracks which emails were seen |

## Privacy & safety notes

- This only requests Gmail's `readonly` and `modify` scopes — it can read
  mail and apply/remove labels, but it cannot delete anything or send
  email as you.
- `credentials.json` and `token.json` are effectively passwords to your
  Gmail account (scoped to read/label only) — don't share this folder or
  commit it to a public GitHub repo.
- The subject, sender, and a truncated portion of each email's body is
  sent to Anthropic's API for classification. Don't run this on an inbox
  containing anything you wouldn't want processed by an AI model.
- If a category classification looks wrong for a particular email, it's
  easy to move it back in Gmail — filing is just a label change, not a
  delete.
- If you set up phone push notifications, the notification title and body
  (which include the sender and subject line of Action Needed / Interview
  emails) are sent unencrypted to ntfy.sh's public server unless you
  self-host it. Use a long, random topic name so it can't be guessed, and
  don't put anything you consider highly sensitive in mind — it's the
  same trust level as an unlisted YouTube link.
