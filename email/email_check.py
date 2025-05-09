import argparse
import datetime
import getpass
import imaplib
import json
import logging
import os
import pickle
from pathlib import Path
from typing import Optional

import attrs
import google.auth
import keyring
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/email_check.log", mode="a"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("email_check")

# Config paths - Following XDG Base Directory specification
CONFIG_DIR = Path.home() / ".config" / "email_check"
CONFIG_PATH = CONFIG_DIR / "config.json"
TOKENS_DIR = CONFIG_DIR / "tokens"
RESULTS_PATH = CONFIG_DIR / "last_results.json"

# App name for keyring
APP_NAME = "email_check"

# Gmail API scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


@attrs.define
class GmailHandler:
    """Handler for Gmail accounts using the Gmail API"""

    account_name: str
    email: str
    service: Optional[object] = attrs.field(default=None)

    def authenticate(self) -> bool:
        """Authenticate with Gmail API"""
        creds = None
        token_path = TOKENS_DIR / f"{self.email}.pickle"

        if token_path.exists():
            with open(token_path, "rb") as token:
                creds = pickle.load(token)

        # If credentials don't exist or are invalid, prompt login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                client_secret_file = CONFIG_DIR / "credentials.json"
                if not client_secret_file.exists():
                    logger.error(
                        "Missing credentials.json. Download from Google Cloud Console"
                    )
                    print(
                        "Please download credentials.json from Google Cloud Console and place in ~/.config/email_check/"
                    )
                    return False

                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secret_file, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(token_path, "wb") as token:
                pickle.dump(creds, token)

        self.service = build("gmail", "v1", credentials=creds)
        return True

    def get_unread_count(self) -> int:
        """Get unread email count using Gmail API"""
        if not self.service:
            if not self.authenticate():
                return -1

        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q="is:unread")
                .execute()
            )
            return len(results.get("messages", []))
        except Exception as e:
            logger.error(
                f"Error getting unread count for {self.account_name}: {str(e)}"
            )
            return -1


@attrs.define
class ImapHandler:
    """Handler for IMAP accounts (iCloud and others)"""

    account: dict

    def get_password(self) -> str:
        """Get password from keyring or prompt if not available"""
        # Try to get password from keyring
        password = keyring.get_password(APP_NAME, self.account["email"])

        # If password not in keyring, prompt user and store it
        if password is None:
            print(
                f"Enter password for {self.account['name']} ({self.account['email']}):"
            )
            password = getpass.getpass()

            # Store in keyring
            keyring.set_password(APP_NAME, self.account["email"], password)

        return password

    def get_unread_count(self) -> int:
        """Get unread email count using IMAP"""
        name = self.account["name"]

        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(
                self.account["imap_server"], self.account["imap_port"]
            )

            # Get password from keyring
            password = self.get_password()

            # Login
            mail.login(self.account["email"], password)

            # Select inbox
            mail.select("INBOX")

            # Search for unread messages
            status, response = mail.search(None, "UNSEEN")
            if status != "OK":
                logger.error(f"Failed to search for UNSEEN messages in {name}")
                return -1

            # Count unread messages
            unread_count = len(response[0].split())

            # Logout
            mail.logout()

            logger.info(f"{name}: {unread_count} unread messages")
            return unread_count

        except Exception as e:
            logger.error(f"Error checking {name}: {str(e)}")
            return -1


@attrs.define
class EmailCounter:
    config_path: Path = attrs.field(default=CONFIG_PATH)
    accounts: list[dict] = attrs.field(factory=list)
    handlers: dict = attrs.field(factory=dict)

    def __attrs_post_init__(self):
        """Initialize after attrs sets basic attributes"""
        self._ensure_config_dir()
        self.accounts = self._load_config()
        self._setup_handlers()

    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        CONFIG_DIR.mkdir(exist_ok=True, parents=True)
        TOKENS_DIR.mkdir(exist_ok=True)

    def _setup_handlers(self):
        """Setup appropriate handlers for each account type"""
        for account in self.accounts:
            if account["type"] == "gmail":
                self.handlers[account["name"]] = GmailHandler(
                    account["name"], account["email"]
                )
            else:
                # For non-Gmail accounts, we only store email, server, port in config
                # Password will be retrieved from keyring
                self.handlers[account["name"]] = ImapHandler(account)

    def _load_config(self) -> list[dict]:
        """Load configuration from file or create default if not exists"""
        if not self.config_path.exists():
            logger.info(
                f"Config file not found, creating template at {self.config_path}"
            )
            default_config = [
                {"name": "Gmail 1", "email": "your.email@gmail.com", "type": "gmail"},
                {
                    "name": "Gmail 2",
                    "email": "your.second.email@gmail.com",
                    "type": "gmail",
                },
                {
                    "name": "iCloud",
                    "email": "your.email@icloud.com",
                    "type": "icloud",
                    "imap_server": "imap.mail.me.com",
                    "imap_port": 993,
                },
            ]

            # Save default config
            with open(self.config_path, "w") as f:
                json.dump(default_config, f, indent=4)

            # Secure the config file
            os.chmod(self.config_path, 0o600)

            logger.warning(
                "Please edit the config file with your actual email credentials"
            )
            return default_config

        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error("Config file is not valid JSON")
            raise

    def check_all_accounts(self) -> dict[str, int]:
        """Check all accounts and return unread counts"""
        results = {}
        for name, handler in self.handlers.items():
            count = handler.get_unread_count()
            results[name] = count
        return results

    def save_results(self, results: dict[str, int]):
        """Save results to file for later retrieval"""
        data = {"timestamp": datetime.datetime.now().isoformat(), "counts": results}
        with open(RESULTS_PATH, "w") as f:
            json.dump(data, f, indent=4)

        # Secure the results file
        os.chmod(RESULTS_PATH, 0o644)
        logger.info(f"Results saved to {RESULTS_PATH}")


def configure_account_passwords():
    """Utility function to configure or update passwords in keyring"""
    counter = EmailCounter()

    print("Setting up passwords for email accounts in keyring")
    for account in counter.accounts:
        if account["type"] != "gmail":  # Gmail uses OAuth, no password needed
            email = account["email"]
            name = account["name"]

            print(f"\nAccount: {name} ({email})")
            choice = input(
                "Do you want to update the password for this account? (y/n): "
            )

            if choice.lower() == "y":
                print("Enter new password:")
                password = getpass.getpass()
                keyring.set_password(APP_NAME, email, password)
                print(f"Password updated for {email}")


def main():
    parser = argparse.ArgumentParser(description="Email Inbox Counter")
    parser.add_argument(
        "--output-json", action="store_true", help="Output results as JSON to stdout"
    )
    parser.add_argument(
        "--output-text",
        action="store_true",
        help="Output results as formatted text to stdout",
    )
    parser.add_argument(
        "--configure",
        action="store_true",
        help="Configure or update passwords in keyring",
    )
    args = parser.parse_args()

    # If configure mode is selected, run the configuration utility
    if args.configure:
        configure_account_passwords()
        return 0

    counter = EmailCounter()

    # Check if config needs to be updated
    first_account = counter.accounts[0]
    if first_account.get("email") == "your.email@gmail.com":
        logger.warning("Please edit the config file before running")
        print(f"Edit the configuration file at: {CONFIG_PATH}")
        return 1

    try:
        # Check all accounts
        results = counter.check_all_accounts()

        # Save results for later reference
        counter.save_results(results)

        # Output based on flags
        if args.output_json:
            print(
                json.dumps(
                    {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "counts": results,
                    }
                )
            )
        elif args.output_text or not (args.output_json):
            # Default to text output if no format specified
            print("--- Email Inbox Counts ---")
            for name, count in results.items():
                if count >= 0:
                    print(f"{name}: {count} unread")
                else:
                    print(f"{name}: Error checking inbox")
            print(
                f"Last checked: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print(f"Error occurred: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
