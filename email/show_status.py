import argparse
import json
import os
from datetime import datetime
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "email_counter"
RESULTS_PATH = CONFIG_DIR / "last_results.json"


def format_time_ago(timestamp_str):
    """Format the time difference in a human-readable way"""
    timestamp = datetime.fromisoformat(timestamp_str)
    now = datetime.now()
    diff = now - timestamp

    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return f"{diff.seconds} second{'s' if diff.seconds != 1 else ''} ago"


def main():
    parser = argparse.ArgumentParser(description="Show Email Inbox Status")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--legacy-path",
        action="store_true",
        help="Check the old ~/.email_counter location for backward compatibility",
    )
    args = parser.parse_args()

    # First check the new path
    results_path = RESULTS_PATH

    # If file doesn't exist and legacy-path flag is set, check old location
    if not results_path.exists() and args.legacy_path:
        legacy_results_path = Path.home() / ".email_counter" / "last_results.json"
        if legacy_results_path.exists():
            results_path = legacy_results_path
            print(
                "Using legacy configuration path. Consider migrating to the new location."
            )

    if not results_path.exists():
        print("No email status data found. Run email_counter first.")
        print(f"Expected path: {RESULTS_PATH}")
        return 1

    try:
        with open(results_path, "r") as f:
            data = json.load(f)

        timestamp = data.get("timestamp")
        counts = data.get("counts", {})

        if args.json:
            print(json.dumps(data))
        else:
            print("--- Email Inbox Status ---")
            for name, count in counts.items():
                if count >= 0:
                    print(f"{name}: {count} unread")
                else:
                    print(f"{name}: Error checking inbox")

            if timestamp:
                time_ago = format_time_ago(timestamp)
                print(f"Last checked: {time_ago}")
                print(
                    f"Exact time: {datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')}"
                )

    except Exception as e:
        print(f"Error reading email status: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
