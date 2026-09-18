"""Handles Gmail OAuth login and returns an authenticated Gmail API client."""
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config

# We only ask for the two permissions this program actually needs:
#  - read your email
#  - apply/remove labels (i.e. move things into "folders") and archive
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_gmail_service():
    """Returns an authenticated Gmail API service object, prompting a one-time
    browser login the first time this program is ever run."""
    creds = None

    if config.TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(config.TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not config.CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Could not find {config.CREDENTIALS_PATH}. See README.md for how "
                    "to download your Gmail OAuth credentials.json from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(config.CREDENTIALS_PATH), SCOPES
            )
            # Opens your default browser for a one-time Google sign-in/consent screen.
            creds = flow.run_local_server(port=0)

        config.TOKEN_PATH.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)
