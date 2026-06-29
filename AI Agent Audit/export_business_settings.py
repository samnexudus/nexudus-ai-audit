#!/usr/bin/env python3
"""
Export all BusinessSettings for a given business to a JSON file.

Usage:
    python export_business_settings.py                  # uses whoami default
    python export_business_settings.py --business-id 1414852340
    python export_business_settings.py --output jactin-house-settings.json
"""

import argparse
import json
import os
import sys
from datetime import date

# Ensure ~/.dotnet/tools is on PATH
_dotnet = os.path.expanduser("~/.dotnet/tools")
if _dotnet not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _dotnet + os.pathsep + os.environ.get("PATH", "")

from models import nexudus


def fetch_all_business_settings(business_id: int, page_size: int = 100) -> list:
    """Fetch all business settings across all pages."""
    all_settings = []
    page = 1

    while True:
        cmd = [
            "businesssettings", "list",
            "--business-id", str(business_id),
            "--page-number", str(page),
            "--page-size", str(page_size),
            "--agent",
        ]
        envelope = nexudus(cmd)

        if not envelope.get("ok"):
            print(f"Error on page {page}: {envelope.get('summary', 'Unknown error')}", file=sys.stderr)
            break

        data = envelope.get("data", [])
        if not data:
            break

        all_settings.extend(data)
        meta = envelope.get("meta", {})
        total = meta.get("total", 0)
        total_pages = meta.get("totalPages", 1)

        print(f"  Fetched page {page}/{total_pages} ({len(all_settings)}/{total} settings)")

        if page >= total_pages:
            break
        page += 1

    return all_settings


def main():
    parser = argparse.ArgumentParser(description="Export BusinessSettings to JSON")
    parser.add_argument("--business-id", type=int, default=None,
                        help="Business ID to export settings for")
    parser.add_argument("--output", type=str, default=None,
                        help="Output JSON file path")
    args = parser.parse_args()

    # Get business ID from args or whoami
    if args.business_id:
        business_id = args.business_id
        business_name = f"business-{business_id}"
    else:
        whoami = nexudus(["whoami"])
        if not whoami.get("ok"):
            print("Not authenticated. Run 'nexudus login' first.", file=sys.stderr)
            sys.exit(1)
        data = whoami.get("data", {})
        business_id = data.get("defaultBusinessId")
        business_name = data.get("defaultBusinessName", "unknown").replace(" ", "-")
        print(f"Using default business: {business_name} (ID: {business_id})")

    # Fetch all settings
    print(f"\nFetching BusinessSettings for business {business_id}...")
    settings = fetch_all_business_settings(business_id)
    print(f"\nTotal: {len(settings)} settings fetched.")

    # Build output
    payload = {
        "exportedAt": date.today().isoformat(),
        "businessId": business_id,
        "entity": "BusinessSettings",
        "count": len(settings),
        "data": settings,
    }

    # Determine output path
    if not args.output:
        today = date.today().isoformat()
        args.output = f"jactin-house-business-settings-{today}.json"

    with open(args.output, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
