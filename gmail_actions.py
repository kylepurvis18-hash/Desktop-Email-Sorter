"""Everything that talks to the Gmail API directly: listing inbox messages,
extracting readable text from them, managing the "folder" labels, and filing
a message into the right one."""
import base64
import datetime
import re

import config

_label_cache = {}  # name -> id, filled in by ensure_labels_exist()


def ensure_labels_exist(service):
    """Creates the nested Gmail labels we use as "folders" if they don't
    already exist, and returns a dict of {label_name: label_id}."""
    global _label_cache
    if _label_cache:
        return _label_cache

    existing = service.users().labels().list(userId="me").execute().get("labels", [])
    name_to_id = {lbl["name"]: lbl["id"] for lbl in existing}

    wanted = [
        config.LABEL_ROOT,
        config.LABEL_CONFIRMED,
        config.LABEL_ACTION_NEEDED,
        config.LABEL_REJECTED,
        config.LABEL_INTERVIEW,
    ]

    for name in wanted:
        if name not in name_to_id:
            created = (
                service.users()
                .labels()
                .create(
                    userId="me",
                    body={
                        "name": name,
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                    },
                )
                .execute()
            )
            name_to_id[name] = created["id"]

    _label_cache = name_to_id
    return name_to_id


def list_candidate_message_ids(service, max_results, lookback_days=None):
    """Returns recent inbox message IDs, newest first. On the very first run
    (lookback_days set) it restricts to recent mail so we don't reclassify
    someone's entire inbox history."""
    query = "in:inbox"
    if lookback_days:
        after = (
            datetime.date.today() - datetime.timedelta(days=lookback_days)
        ).strftime("%Y/%m/%d")
        query += f" after:{after}"

    resp = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    return [m["id"] for m in resp.get("messages", [])]


def _walk_parts_for_text(payload):
    """Recursively pulls plain-text (falling back to HTML) out of a Gmail
    message payload, which can be nested arbitrarily deep for multipart mail."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return _decode(payload["body"]["data"])

    if payload.get("mimeType") == "text/html" and payload.get("body", {}).get("data"):
        html = _decode(payload["body"]["data"])
        return re.sub("<[^<]+?>", " ", html)

    text = ""
    for part in payload.get("parts", []) or []:
        found = _walk_parts_for_text(part)
        if found:
            text = found
            if part.get("mimeType") == "text/plain":
                break  # prefer plain text over html if we find both
    return text


def _decode(data):
    return base64.urlsafe_b64decode(data.encode("UTF-8")).decode("UTF-8", errors="replace")


def get_message_details(service, message_id):
    """Fetches one message and returns the bits we need for classification."""
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
    body_text = _walk_parts_for_text(msg["payload"]) or msg.get("snippet", "")

    return {
        "id": message_id,
        "subject": headers.get("subject", "(no subject)"),
        "sender": headers.get("from", "(unknown sender)"),
        "snippet": msg.get("snippet", ""),
        "body": body_text[:4000],  # keep prompts small and cheap
    }


def file_message(service, message_id, label_name):
    """Applies the given category label and archives the message out of the
    inbox (removes the INBOX label), so it behaves like being moved into a
    folder rather than just tagged."""
    label_ids = ensure_labels_exist(service)
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={
            "addLabelIds": [label_ids[label_name]],
            "removeLabelIds": ["INBOX"],
        },
    ).execute()
