#!/usr/bin/env python3
"""
Job Email Sorter
=================
Watches your Gmail inbox, and for each new email decides (using Claude)
whether it's related to a job application you sent, and if so which stage
it's at. It then files it into the matching Gmail label/folder, archiving
it out of your inbox, and pops a desktop notification for the two
time-sensitive categories.

Run with no arguments to start continuous monitoring:
    python main.py

Run once and exit (useful for testing, or for running via your own OS
scheduler like Task Scheduler/cron instead of leaving this running):
    python main.py --once

See README.md for one-time setup instructions.
"""
import argparse
import sys
import time
import traceback

import config
import gmail_auth
import gmail_actions
import classifier
import notifier
import state

CATEGORY_TO_LABEL = {
    "confirmation": config.LABEL_CONFIRMED,
    "action_needed": config.LABEL_ACTION_NEEDED,
    "rejected": config.LABEL_REJECTED,
    "interview": config.LABEL_INTERVIEW,
}

NOTIFICATION_TEXT = {
    "action_needed": (
        "Action needed on a job application",
        "{sender} wants you to submit something or complete a pre-screening: {subject}",
        "default",
    ),
    "interview": (
        "You're moving forward!",
        "{sender} wants to move forward / schedule an interview: {subject}",
        "urgent",
    ),
}


def run_once(service, processed_ids, is_first_run):
    lookback = config.INITIAL_LOOKBACK_DAYS if is_first_run else None
    message_ids = gmail_actions.list_candidate_message_ids(
        service, config.MAX_EMAILS_PER_CHECK, lookback_days=lookback
    )

    new_ids = [m for m in message_ids if m not in processed_ids]
    if not new_ids:
        print("  No new emails to check.")
        return

    print(f"  Checking {len(new_ids)} new email(s)...")

    for message_id in new_ids:
        try:
            details = gmail_actions.get_message_details(service, message_id)
            result = classifier.classify_email(
                subject=details["subject"],
                sender=details["sender"],
                body=details["body"] or details["snippet"],
            )
            category = result["category"]

            if category == "not_job_related":
                print(f"  - Skipping (not job-related): {details['subject'][:70]}")
            else:
                label_name = CATEGORY_TO_LABEL[category]
                gmail_actions.file_message(service, message_id, label_name)
                print(f"  - Filed as [{category}] -> {label_name}: {details['subject'][:70]}")

                if category in config.NOTIFY_CATEGORIES:
                    title, template, priority = NOTIFICATION_TEXT[category]
                    body = template.format(sender=details["sender"], subject=details["subject"])
                    notifier.send_desktop_notification(title, body)
                    notifier.send_push_notification(title, body, priority=priority)

        except Exception:
            print(f"  [!] Error processing message {message_id}, skipping it:")
            traceback.print_exc()

        finally:
            # Mark as processed even on failure so a permanently-broken message
            # can't jam every future run; you can still find it by re-checking
            # your inbox search history if needed.
            processed_ids.add(message_id)

    state.save_processed_ids(processed_ids)


def main():
    parser = argparse.ArgumentParser(description="Sort job-application emails in Gmail.")
    parser.add_argument(
        "--once", action="store_true",
        help="Check the inbox one time and exit, instead of running continuously.",
    )
    args = parser.parse_args()

    problems = config.validate()
    if problems:
        print("Before this can run, please fix the following:\n")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print("Logging in to Gmail (a browser window may open the first time)...")
    service = gmail_auth.get_gmail_service()
    gmail_actions.ensure_labels_exist(service)
    print("Connected. Labels are set up under 'Job Applications' in Gmail.\n")

    processed_ids = state.load_processed_ids()
    is_first_run = len(processed_ids) == 0

    if args.once:
        run_once(service, processed_ids, is_first_run)
        return

    print(f"Watching your inbox every {config.POLL_INTERVAL_SECONDS} seconds. "
          f"Press Ctrl+C to stop.\n")

    backoff = config.POLL_INTERVAL_SECONDS
    while True:
        try:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Checking inbox...")
            run_once(service, processed_ids, is_first_run)
            is_first_run = False
            backoff = config.POLL_INTERVAL_SECONDS
            time.sleep(config.POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\nStopped.")
            break

        except Exception:
            print("  [!] Unexpected error this cycle, will retry after a backoff:")
            traceback.print_exc()
            time.sleep(backoff)
            backoff = min(backoff * 2, 3600)  # cap backoff at 1 hour


if __name__ == "__main__":
    main()
