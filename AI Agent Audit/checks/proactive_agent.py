"""
Checks — Proactive AI Agent
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import Section, CheckResult, nexudus


def check_proactive_agent(business_id: int) -> Section:
    section = Section("Proactive AI Agent")

    # ── Configured ────────────────────────────────────────────────────────────
    # TODO: fill in checks once Sam provides detail
    section.add(CheckResult(
        name="Configured",
        status="skip",
        detail="Not yet defined — awaiting spec.",
    ))

    return section
