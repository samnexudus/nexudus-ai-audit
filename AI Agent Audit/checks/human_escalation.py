"""
Checks — Escalating to Human Support
AI capability: create help desk tickets when it cannot resolve a request or
the user asks to speak to a human.

Business settings (filter --name "OpenAI."):
  OpenAI.HelpDesk.Enabled              bool — master escalation toggle
  OpenAI.DefaultEscalationDepartment   help desk department ID (optional)
  OpenAI.EscalationResponseTimeSLA     string — SLA message shown to users (optional)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import Section, CheckResult, nexudus


def check_human_escalation(business_id: int) -> Section:
    section = Section("Escalating to Human Support")

    # ── Fetch relevant settings ────────────────────────────────────────────────
    env = nexudus(["businesssettings", "list",
                   "--business-id", str(business_id),
                   "--name", "OpenAI.",
                   "--page-size", "50"])

    if not env.get("ok"):
        section.add(CheckResult(
            name="Escalation settings — data fetch failed",
            status="fail",
            detail=env.get("summary", "Could not fetch escalation settings."),
        ))
        return section

    records  = env.get("data") or []
    by_name  = {r["Name"]: (r.get("Value") or "").strip() for r in records}

    escalation_enabled = by_name.get("OpenAI.HelpDesk.Enabled", "").lower() == "true"

    # ── 1. Master toggle ───────────────────────────────────────────────────────
    if not escalation_enabled:
        section.add(CheckResult(
            name="AI escalation to human support not enabled",
            status="warn",
            detail=(
                "When the AI cannot resolve a request or a user asks to speak to someone, "
                "it will tell them it cannot connect them to a human agent."
            ),
            hint="Enable 'AI escalation to human support' under Settings › AI Assistants › Channels › AI escalation.",
        ))
        return section

    section.add(CheckResult(
        name="AI escalation to human support enabled",
        status="pass",
        detail="The AI will create a help desk ticket and notify the user when it needs to hand off to your team.",
    ))

    # ── 2. Help desk departments exist ─────────────────────────────────────────
    dept_env = nexudus(["helpdeskdepartments", "list",
                        "--business-id", str(business_id),
                        "--page-size", "50"])

    departments = []
    if dept_env.get("ok"):
        departments = [d for d in (dept_env.get("data") or []) if d.get("Active")]

    if not departments:
        section.add(CheckResult(
            name="No active help desk departments",
            status="fail",
            detail="Escalation tickets need a department to route to. None are currently active.",
            hint="Create at least one help desk department under Settings › Help Desk › Departments.",
        ))
    else:
        dept_names = ", ".join(d.get("Name", "Unnamed") for d in departments)
        section.add(CheckResult(
            name=f"{len(departments)} active help desk department{'s' if len(departments) != 1 else ''}",
            status="pass",
            detail=dept_names,
        ))

    # ── 3. Default escalation department ──────────────────────────────────────
    dept_id = by_name.get("OpenAI.DefaultEscalationDepartment", "")
    if not dept_id:
        section.add(CheckResult(
            name="No default escalation department configured",
            status="warn",
            detail="Escalation tickets will go to the system default help desk department.",
            hint=(
                "Set a default escalation department under Settings › AI Assistants › Channels › AI escalation "
                "to control exactly where AI-generated tickets land."
            ),
        ))
    else:
        matched = next((d for d in departments if str(d.get("Id")) == dept_id), None)
        dept_label = matched.get("Name") if matched else None
        section.add(CheckResult(
            name="Default escalation department set",
            status="pass",
            detail=f"AI escalation tickets will be routed to: {dept_label}" if dept_label else "Default escalation department configured.",
        ))

    # ── 4. SLA / response time message ────────────────────────────────────────
    sla_message = by_name.get("OpenAI.EscalationResponseTimeSLA", "")
    if not sla_message:
        section.add(CheckResult(
            name="No response time message configured",
            status="warn",
            detail=(
                "After escalating, the AI will not tell the user how long to expect a response. "
                "This can lead to follow-up messages asking for an update."
            ),
            hint=(
                "Add an SLA message under Settings › AI Assistants › Channels › AI escalation, "
                "e.g. 'We usually respond within 2 hours during business hours.'"
            ),
        ))
    else:
        section.add(CheckResult(
            name="Response time message set",
            status="pass",
            detail=f'"{sla_message}"',
        ))

    return section
