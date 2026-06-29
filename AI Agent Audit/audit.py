#!/usr/bin/env python3
"""
AI Agent Audit — Nexudus account readiness check for AI Agent functionality.

Usage:
    python audit.py
    python audit.py --business <id>       # audit a specific business
    python audit.py --output ./reports/   # custom output directory
    python audit.py --no-html             # terminal output only
    python audit.py --json                # machine-readable JSON to stdout
"""

import argparse
import json
import os
import sys
from datetime import date as Date
from typing import Optional

# Ensure ~/.dotnet/tools is on PATH before any subprocess calls
_dotnet = os.path.expanduser("~/.dotnet/tools")
if _dotnet not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _dotnet + os.pathsep + os.environ.get("PATH", "")

from models import Section, CheckResult, nexudus

# ── Colours (terminal only) ───────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
DIM    = "\033[2m"


def require_auth() -> Optional[dict]:
    envelope = nexudus(["whoami"])
    if not envelope.get("ok"):
        return None
    return envelope.get("data")


# ── Check modules ─────────────────────────────────────────────────────────────

from checks.conversation_assistant import check_conversation_assistant
from checks.locations_and_rooms import check_location_details
from checks.rooms_and_resources import check_rooms_and_resources
from checks.day_passes import check_day_passes
from checks.membership_plans import check_membership_plans
from checks.channels import check_chat_channel, check_whatsapp_channel, check_email_channel, check_voice_channel
from checks.human_escalation import check_human_escalation
from checks.private_offices import check_private_offices
from checks.proactive_agent import check_proactive_agent


# ── Terminal reporter ─────────────────────────────────────────────────────────

STATUS_ICON = {
    "pass": f"{GREEN}✓{RESET}",
    "warn": f"{YELLOW}⚠{RESET}",
    "fail": f"{RED}✗{RESET}",
    "skip": f"{DIM}–{RESET}",
}
STATUS_LABEL = {
    "pass": f"{GREEN}PASS{RESET}",
    "warn": f"{YELLOW}WARN{RESET}",
    "fail": f"{RED}FAIL{RESET}",
    "skip": f"{DIM}SKIP{RESET}",
}


def print_report(sections: list[Section], whoami: dict):
    business = whoami.get("defaultBusinessName", "Unknown")
    print(f"\n{BOLD}{CYAN}━━━ AI Agent Audit — {business} ━━━{RESET}\n")

    total_pass = total_warn = total_fail = 0

    for section in sections:
        sc = section.score
        total_pass += sc["pass"]
        total_warn += sc["warn"]
        total_fail += sc["fail"]
        print(f"{BOLD}{section.title}{RESET}")
        for r in section.results:
            print(f"  {STATUS_ICON[r.status]} {r.name}  [{STATUS_LABEL[r.status]}]")
            if r.detail:
                print(f"     {DIM}{r.detail}{RESET}")
            if r.hint and r.status in ("warn", "fail"):
                print(f"     {YELLOW}→ {r.hint}{RESET}")
        print()

    total = total_pass + total_warn + total_fail
    print(f"{BOLD}Summary:{RESET}  "
          f"{GREEN}{total_pass} passed{RESET}  "
          f"{YELLOW}{total_warn} warnings{RESET}  "
          f"{RED}{total_fail} failed{RESET}  "
          f"(of {total} checks)\n")


def print_json_output(sections: list[Section], whoami: dict):
    out = {
        "business":   whoami.get("defaultBusinessName"),
        "businessId": whoami.get("defaultBusinessId"),
        "date":       Date.today().isoformat(),
        "sections": [
            {
                "title": s.title,
                "score": s.score,
                "checks": [
                    {"name": r.name, "status": r.status, "detail": r.detail, "hint": r.hint}
                    for r in s.results
                ],
            }
            for s in sections
        ],
    }
    print(json.dumps(out, indent=2))


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Audit a Nexudus account for AI Agent readiness.")
    parser.add_argument("--business", help="Business ID to audit (defaults to your default business)")
    parser.add_argument("--output",   default=".", help="Directory to write the HTML report into")
    parser.add_argument("--no-html",  action="store_true", help="Skip HTML report, terminal output only")
    parser.add_argument("--json",     action="store_true", dest="as_json", help="Output as JSON to stdout (no HTML)")
    parser.add_argument("--publish",  action="store_true", help="Publish the HTML report to GitHub Pages")
    args = parser.parse_args()

    print(f"""
{BOLD}{CYAN}  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗██████╗ ██╗   ██╗███████╗
  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔══██╗██║   ██║██╔════╝
  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║██║  ██║██║   ██║███████╗
  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║██║  ██║██║   ██║╚════██║
  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝██████╔╝╚██████╔╝███████║
  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝{RESET}
{BOLD}                    AI Agent Audit{RESET} · {DIM}by Nexudus{RESET}

  Checking your space is ready to let AI do the heavy lifting.
  Grab a coffee — this won't take long. ☕
""", file=sys.stderr)

    whoami = require_auth()
    if not whoami:
        print(f"{RED}Not authenticated. Run 'nexudus login' first.{RESET}", file=sys.stderr)
        sys.exit(1)

    business_id = args.business or whoami.get("defaultBusinessId")

    print(f"  Auditing {BOLD}{whoami.get('defaultBusinessName', business_id)}{RESET}…\n", file=sys.stderr)

    tabs = [
        ("Conversational Agents", [
            check_location_details(business_id),
            check_conversation_assistant(business_id),
            check_rooms_and_resources(business_id),
            check_day_passes(business_id),
            check_membership_plans(business_id),
            check_private_offices(business_id),
            check_human_escalation(business_id),
        ]),
        ("Channels", [
            check_chat_channel(business_id),
            check_whatsapp_channel(business_id),
            check_email_channel(business_id),
            check_voice_channel(business_id),
        ]),
        ("Proactive Agents", [
            check_proactive_agent(business_id),
        ]),
    ]

    sections: list[Section] = [s for _, group in tabs for s in group]

    if args.as_json:
        print_json_output(sections, whoami)
        return

    print_report(sections, whoami)

    if not args.no_html:
        from report import generate_html, save_report
        from datetime import date as Date
        run_date = Date.today()
        html = generate_html(tabs, whoami)
        path = save_report(html, whoami.get("defaultBusinessName", "business"), run_date=run_date, output_dir=args.output)
        print(f"{GREEN}✓ Report saved:{RESET} {path}\n")

        if args.publish:
            from publish import publish
            print(f"Publishing to GitHub Pages…", file=sys.stderr)
            url = publish(path, str(business_id), whoami.get("defaultBusinessName", ""), run_date)
            print(f"{GREEN}✓ Published:{RESET} {url}\n")


if __name__ == "__main__":
    main()
