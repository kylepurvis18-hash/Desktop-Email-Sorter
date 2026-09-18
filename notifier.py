"""Notifications: a cross-platform desktop popup (Windows/macOS/Linux) via
plyer, plus an optional push notification to your phone via ntfy.sh."""
import requests
from plyer import notification

import config


def send_desktop_notification(title: str, message: str):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Job Email Sorter",
            timeout=15,
        )
    except Exception as e:
        # Notifications are a nice-to-have; never let a notification failure
        # stop emails from being sorted.
        print(f"  [!] Could not show desktop notification ({e}). "
              f"The email was still filed correctly.")


def send_push_notification(title: str, message: str, priority: str = "default"):
    """Sends a push notification to your phone via ntfy.sh, if configured.
    Silently does nothing if NTFY_TOPIC isn't set in .env, so this stays
    fully optional. See README.md for the 2-minute setup."""
    if not config.NTFY_TOPIC:
        return

    url = f"{config.NTFY_SERVER.rstrip('/')}/{config.NTFY_TOPIC}"
    try:
        requests.post(
            url,
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,   # "default" or "urgent" (buzzes/lights up the phone)
                "Tags": "briefcase",
            },
            timeout=10,
        )
    except Exception as e:
        # Same principle as above: a failed push should never stop the
        # program or cause an email to be re-filed/re-notified.
        print(f"  [!] Could not send phone push notification ({e}). "
              f"The email was still filed correctly.")
