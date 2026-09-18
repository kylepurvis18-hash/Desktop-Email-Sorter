"""Tracks which Gmail message IDs we've already looked at, so we never
re-classify or re-notify about the same email twice. Stored as a plain JSON
file next to this script."""
import json
import config


def load_processed_ids() -> set:
    if not config.STATE_PATH.exists():
        return set()
    try:
        with open(config.STATE_PATH, "r") as f:
            data = json.load(f)
        return set(data.get("processed_ids", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_processed_ids(ids: set):
    # Cap how much history we keep on disk so the file doesn't grow forever.
    trimmed = list(ids)[-5000:]
    with open(config.STATE_PATH, "w") as f:
        json.dump({"processed_ids": trimmed}, f)
