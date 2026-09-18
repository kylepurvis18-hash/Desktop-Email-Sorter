"""Loads configuration from the .env file (or environment variables)."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "300"))
MAX_EMAILS_PER_CHECK = int(os.environ.get("MAX_EMAILS_PER_CHECK", "25"))
INITIAL_LOOKBACK_DAYS = int(os.environ.get("INITIAL_LOOKBACK_DAYS", "14"))

# Optional phone push notifications via ntfy.sh. Leave NTFY_TOPIC blank to
# disable push notifications entirely (desktop notifications still work).
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").strip()
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()

CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"
STATE_PATH = BASE_DIR / "processed_state.json"

# Gmail label names. Using "Parent/Child" creates a nested label, which Gmail
# displays like a folder with sub-folders in the left sidebar.
LABEL_ROOT = "Job Applications"
LABEL_CONFIRMED = f"{LABEL_ROOT}/Application Received"
LABEL_ACTION_NEEDED = f"{LABEL_ROOT}/Action Needed"
LABEL_REJECTED = f"{LABEL_ROOT}/Not Moving Forward"
LABEL_INTERVIEW = f"{LABEL_ROOT}/Interview - Moving Forward"

# Categories that should trigger a desktop notification.
NOTIFY_CATEGORIES = {"action_needed", "interview"}

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")


def validate():
    problems = []
    if not ANTHROPIC_API_KEY:
        problems.append(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    if not CREDENTIALS_PATH.exists():
        problems.append(
            f"Missing {CREDENTIALS_PATH.name}. Download your Gmail OAuth credentials "
            "from Google Cloud Console and save them next to this script (see README.md)."
        )
    return problems
