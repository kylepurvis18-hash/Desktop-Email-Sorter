# Troubleshooting

Real problems hit while setting this up and getting it running end-to-end,
recorded here so future-me (or anyone else trying this) doesn't have to
re-solve them from scratch. Roughly in the order they tend to show up.

## `'pip' is not recognized as an internal or external command`

**Cause:** Python is either not installed, or was installed without the
"Add python.exe to PATH" box checked during setup — a very easy step to
miss.

**Fix:** First confirm Python itself works: `python --version`. If that
returns a version number, use `python -m pip install -r requirements.txt`
instead of bare `pip` — routing through Python directly sidesteps a broken
PATH entry for `pip` specifically. If `python --version` also fails,
reinstall Python from python.org and check "Add python.exe to PATH" on the
very first install screen, then reopen your terminal (PATH changes don't
apply to already-open windows).

## `ERROR: Could not open requirements file: [Errno 2] No such file or directory`

**Cause:** Running `pip install -r requirements.txt` from the wrong
directory — the file only exists inside the project folder.

**Fix:** `cd` into the project folder first (e.g.
`cd Downloads\job_email_sorter` on Windows), confirm with `dir` (Windows)
or `ls` (Mac/Linux) that `requirements.txt` is actually listed, then rerun
the install command.

## `git push` → `remote: Repository not found`

**Cause:** In this case, a typo in the GitHub username used when setting
the remote URL (missing part of the actual username), so the URL pointed
at an account/repo that doesn't exist. The same error also shows up if the
repo hasn't actually been created on GitHub yet, or the repo name doesn't
match exactly.

**Fix:** Check the currently configured remote with `git remote -v`.
Compare it character-for-character against your real GitHub username and
the exact repo name as it appears at github.com/<your-username>. Fix it
with `git remote set-url origin https://github.com/<username>/<repo>.git`
and push again.

## `Missing credentials.json`

**Cause:** The Gmail API / OAuth setup step in the README (Google Cloud
Console → enable Gmail API → configure OAuth consent screen → create a
Desktop app credential → download the JSON) hadn't been done yet. This
file has to come from your own Google account — it can't ship with the
program.

**Fix:** Walk through the Google Cloud Console steps in the main README,
download the OAuth client JSON, and make sure it ends up named exactly
`credentials.json`.

## `credentials.json` "won't go" next to `main.py` / seems to disappear

**Cause:** Windows File Explorer hides known file extensions by default.
Renaming the downloaded file to `credentials.json` can silently produce
`credentials.json.json`, since Explorer re-appends the real extension you
can't see.

**Fix:** In File Explorer, View tab → check **File name extensions**, then
look at the file again. If it reads `credentials.json.json`, remove the
extra `.json`. Same fix applies later when saving `run_sorter.bat` in
Notepad — watch for a hidden `.txt` getting appended.

## Google's "unverified app" warning on first login

**Cause:** Expected, not an error. Since this app is only registered for
personal/testing use (not submitted for Google's full app review), Google
shows a warning any time it isn't a publicly verified app.

**Fix:** Click **Advanced**, then **Go to <app name> (unsafe)**. This is
safe for a personal script only you use — it just means Google hasn't
manually reviewed it, not that anything is actually wrong.

## `Error 403: access_denied` during Google sign-in

**Cause:** The Google account being used to sign in wasn't added as a
**Test user** on the OAuth consent screen (while the app is in "Testing"
publishing status, only explicitly listed accounts can authorize it) — or
there's a typo in the listed email, or a different Google account than
the one added was used to sign in.

**Fix:** Google Cloud Console → APIs & Services → OAuth consent screen →
Test users → confirm the exact Gmail address is listed (add it if not).
When signing in again, make sure the correct Google account is selected if
multiple are signed in in the browser.

## Command prompt looks frozen / won't accept typing

**Cause:** Two different things can cause this. Most common: clicking
inside a Command Prompt window triggers Windows' "QuickEdit" text-selection
mode, which pauses whatever is running. Second possibility: the program is
correctly waiting on the browser-based Google login step and isn't
supposed to accept typed input at that point.

**Fix:** Press **Esc** (or right-click once) to exit QuickEdit mode. If a
browser tab opened for Google sign-in, finish that first — the terminal
resumes on its own once the browser step completes.

## `Gmail API has not been used in project ... or it is disabled` (HTTP 403)

**Cause:** The Gmail API was never actually enabled for the Google Cloud
project, or the Enable click didn't fully register.

**Fix:** Visit the exact URL from the error message (it's
project-specific), click **Enable**, wait a minute or two for it to
propagate, then rerun the program. Since login had already succeeded,
`token.json` was already saved, so the retry skipped straight past the
browser login step.

## Desktop notification fires, but no phone push notification (ntfy / iPhone)

**Cause:** In this case, narrowed down (via publishing a manual test
message directly to the ntfy topic, bypassing the script) to messages
correctly reaching the topic and the app — visible when opening the app —
but iOS not surfacing them as an actual push/banner. This points at
notification delivery settings rather than anything in the script.

**Things checked, roughly in order of how likely they are to be it:**
- iOS Settings → Notifications → ntfy → **Allow Notifications** on, and
  Banners/Lock Screen/Notification Center all enabled.
- iOS Settings → Notifications → ntfy → **Notification Delivery** set to
  **Immediate Delivery**, not **Scheduled Summary** (Scheduled Summary
  batches notifications instead of delivering them right away — matches
  this symptom closely).
- Focus/Do Not Disturb modes not silently blocking the app.
- A full unsubscribe-and-resubscribe of the topic in the app, to force a
  fresh push-registration handshake.
- Deleting and reinstalling the app entirely, to force a completely fresh
  device registration with Apple's push service.

**If none of that resolves it:** ntfy's iOS push relies on a registration
step with Apple's push service that can fail silently in a way none of the
visible settings reveal. A more reliable (but not free) alternative is
Pushover, which is purpose-built for this and doesn't share this failure
mode; swapping it in only touches `notifier.py`.

## Gmail labels visible in the browser, but not all four show up in Outlook desktop

**Cause:** Two separate things, both needed:
1. Gmail only exposes a label over IMAP if **Show in IMAP** is checked for
   it (Gmail Settings → See all settings → Labels tab).
2. Outlook (desktop, IMAP account) still needs you to explicitly subscribe
   to a folder/label after it's created — it doesn't always auto-add ones
   created after the account was first set up.

**Fix:** Check **Show in IMAP** for all four labels (and their parent
label) in Gmail's Labels settings. Then in Outlook, right-click the
account → **IMAP Folders...** (or Account Settings → double-click account
→ More Settings → Advanced → Folder Options) and make sure the four
labels are checked/subscribed. Do a manual Send/Receive afterward.
