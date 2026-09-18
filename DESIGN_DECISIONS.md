# Design Decisions

This documents the reasoning behind how Job Email Sorter is built — not just
what it does, but why it was built this way instead of the alternatives that
were on the table. Written mainly so the choices stay explainable later
(including in an interview), not just "it worked."

## Architecture, at a glance

```
        every POLL_INTERVAL_SECONDS
                   │
                   ▼
        ┌─────────────────────┐
        │  Gmail API: list     │  "what's new in my inbox
        │  recent inbox msgs   │   since I last checked?"
        └─────────┬────────────┘
                   │ message IDs
                   ▼
        ┌─────────────────────┐
        │  skip IDs already    │  processed_state.json
        │  seen before         │  (local, on disk)
        └─────────┬────────────┘
                   │ new messages only
                   ▼
        ┌─────────────────────┐
        │  Gmail API: fetch    │  subject / sender / body
        │  full message        │
        └─────────┬────────────┘
                   ▼
        ┌─────────────────────┐
        │  Claude API:         │  "which of these 5 categories
        │  classify             │   is this email?"
        └─────────┬────────────┘
                   ▼
        ┌─────────────────────┐
        │  Gmail API: apply    │  label = the "folder"
        │  label, remove INBOX │  removing INBOX = the "move"
        └─────────┬────────────┘
                   ▼
        ┌─────────────────────┐
        │  if Action Needed /  │  desktop popup (plyer)
        │  Interview: notify   │  + phone push (ntfy.sh)
        └─────────────────────┘
```

## Why Python instead of Java (or a compiled desktop app)

Java was the first option raised, since "a downloadable program" often
implies something compiled. But the actual requirements here — call a REST
API (Gmail), call another REST API (Claude), do a small amount of text
processing, run on a timer — are exactly what Python's ecosystem is built
for, with almost no boilerplate:

- Google publishes an official, well-maintained Python client for Gmail
  (`google-api-python-client`) with the OAuth flow largely handled for you.
  The Java equivalent exists but needs considerably more setup code for the
  same result.
- No compilation step, no build system, easy to read/modify line by line —
  useful for a project meant to be understood, not just run.
- If a "no Python installed" download is ever wanted, `pyinstaller` can
  bundle this into a single `.exe`/binary later without changing any code.

## Why Gmail labels instead of real folders

Gmail doesn't actually have folders — every "folder" you see in the Gmail
UI (including the built-in ones like Inbox) is a *label* under the hood.
So "file this into a folder" is implemented as: apply the category label,
then remove the `INBOX` label. That combination is what makes an email
disappear from the inbox and show up under the label in the sidebar,
which is the actual user-visible behavior being asked for.

Labels are also nestable (`Job Applications/Interview`), which is what
gives the sidebar its folder-with-subfolders look.

## Why polling on a timer instead of real-time push

Gmail *does* support real-time push notifications for new mail, but only
through Google Cloud Pub/Sub — which requires a publicly reachable HTTPS
endpoint (i.e., a server) to receive the webhook, plus additional Google
Cloud configuration and a renewal process (the push subscription expires
every 7 days and has to be re-registered). That's a reasonable trade for a
hosted service; it's a lot of extra moving parts for a personal script
running on a laptop with no public IP.

Polling every few minutes gets effectively the same result for this use
case — job application emails aren't sub-second time-critical — with a
fraction of the infrastructure. `POLL_INTERVAL_SECONDS` in `.env` controls
the trade-off between "how fresh" and "how many API calls" directly.

## Why an AI model instead of keyword rules

An earlier plan considered plain keyword/sender-based Gmail filters
(e.g., if subject contains "thank you for applying"). That's simpler and
free to run, but brittle: every company phrases these emails differently,
rejections in particular range from blunt to extremely indirect
("we've decided to move forward with other candidates whose qualifications
more closely align...", "we will keep your resume on file", etc.), and a
purely keyword-based system either over-matches (false positives) or
needs constant manual rule tuning as new phrasings show up.

Having Claude read the actual email and reason about which of the 5
categories it belongs to handles that variation without hand-written
rules, at a cost of a fraction of a cent per email for typical volumes.
The trade-off being accepted: it depends on an external API being up and
costs a small amount of money, versus a rules engine being free and fully
offline. For this use case (a few dozen emails a week, not thousands a
minute), that trade is worth it.

## Why ntfy.sh for phone notifications

Getting a notification onto a phone from a script running on a laptop is
usually the hard part of a project like this — it normally means building
and shipping an actual mobile app with a push-notification backend (Apple
Push Notification service / Firebase Cloud Messaging), which is a
significant project on its own (see the "why not a native app" discussion
below).

ntfy.sh sidesteps that entirely: it's a free, open-source pub/sub service
— the script does a single HTTP POST to a topic name, and anything
subscribed to that topic (the ntfy phone app) gets the push instantly. No
account, no API key, no app to build or submit to an app store. The
trade-off is that public ntfy.sh topics aren't authenticated, so the topic
name itself is the only thing standing between someone and your
notifications — mitigated here by recommending a long, random topic name,
and by ntfy supporting self-hosting later if that trade stops being
acceptable.

Pushover and a custom Telegram bot were the other options considered:
Pushover is more polished and has delivery guarantees worth paying for at
scale, and Telegram is free but requires more setup (creating a bot via
BotFather, capturing a chat ID). Either is a small, isolated change to
`notifier.py` if priorities change later — the rest of the program doesn't
need to know which push service is behind `send_push_notification()`.

## Why not a full native iOS/Android app

This was considered directly. The blocker isn't difficulty of writing the
UI — it's that mobile OSes (iOS especially) don't allow an app to run
continuously in the background scanning email the way a desktop script
can; Apple restricts background execution heavily. To get "continuous
monitoring + push notification" from a phone app, the actual email-reading
and classification logic would have to live on a server somewhere, with
the phone app itself only handling display and receiving pushes — meaning
a real backend to build, host, and maintain, plus (for iOS specifically)
a paid Apple Developer account and App Store review. That's a multi-week
project on its own, and the desktop-script-plus-ntfy approach here gets
the actually-wanted outcome (a phone buzzes when something important
happens) without needing to build or run that backend at all.

## Why a flat JSON file for state instead of a database

`processed_state.json` just stores a list of Gmail message IDs already
looked at. At personal-inbox volume (tens to low hundreds of emails a
week), a database would add setup and dependency weight without adding
any real capability — a JSON file is trivially inspectable, has no schema
to migrate, and is fast enough at this scale. If this were scaled to
monitor many mailboxes at once, that calculus would change.

## Error-handling philosophy

A few deliberate choices show up throughout the code:

- **A single email's classification failing never stops the run.** Each
  message is processed inside its own `try/except`; one bad response from
  an API doesn't take down the whole batch.
- **A message is marked "processed" even if it errored**, so a single
  permanently-malformed email can't jam every future check by being
  retried forever.
- **A cycle-level failure (e.g., the network being down) backs off
  exponentially** (`main.py`'s `backoff` logic, capped at an hour) instead
  of hammering the API or crashing outright.
- **Notification failures are logged but swallowed**, since a popup or
  push not showing up shouldn't be treated as seriously as an email being
  mis-filed.

The general rule: a partial failure should degrade gracefully, not take
the whole program down or leave Gmail in an inconsistent state.
