"""
Checks — Private Offices & Tours
AI capability: present available private offices and generate tour request links.

Entity: floorplandesks (ItemType = 1 for Private Office)
AI fields: AvailableToAi, ShowPriceForAi, PriceForAi, NotesForAi
Availability: Available=true → available now; Available=false + AvailableFromTime → coming soon

Tour settings stored as businesssettings entries (filter --name "PublicWebSite.Tour"):
  PublicWebSite.Tour                    bool — master on/off
  PublicWebSite.Tour.Host               coworker/user ID
  PublicWebSite.Tour.RequiresConfirmation  bool
  PublicWebSite.Tour.TimeSlots.Enabled  bool — restrict to configured time slots
  PublicWebSite.Tour.TimeSlots          JSON [{FromTime, ToTime, DayOfWeek}]
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timezone
from models import Section, CheckResult, nexudus

DAY_NAMES = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}

PRIVATE_OFFICE_ITEM_TYPE = 1


def _names(items: list, key: str = "Name", limit: int = 3) -> str:
    ns = ", ".join(str(i.get(key, "Unnamed")) for i in items[:limit])
    more = f" and {len(items) - limit} more" if len(items) > limit else ""
    return ns + more


def _is_future(dt_str: str) -> bool:
    if not dt_str:
        return False
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt > datetime.now(timezone.utc)
    except ValueError:
        return False


def check_private_offices(business_id: int) -> Section:
    section = Section("Private Offices & Tours")

    env = nexudus(["floorplandesks", "list",
                   "--business-id", str(business_id),
                   "--page-size", "100"])

    if not env.get("ok"):
        section.add(CheckResult(
            name="Private offices — data fetch",
            status="fail",
            detail=env.get("summary", "Failed to fetch floor plan desks."),
        ))
        return section

    all_desks  = env.get("data") or []
    offices    = [d for d in all_desks if d.get("ItemType") == PRIVATE_OFFICE_ITEM_TYPE]
    total      = len(offices)

    # ── 1. Private offices exist on floor plans ────────────────────────────────
    if total == 0:
        section.add(CheckResult(
            name="No private offices on floor plans",
            status="fail",
            detail="The AI has no offices to present when prospects ask about private office options.",
            hint="Add private office items to your floor plans in Nexudus and enable 'Available to AI'.",
        ))
        return section

    section.add(CheckResult(
        name=f"{total} private office{'s' if total != 1 else ''} on floor plans",
        status="pass",
        detail=_names(offices),
    ))

    # ── 2. AvailableToAi ──────────────────────────────────────────────────────
    not_ai = [o for o in offices if not o.get("AvailableToAi")]
    ai_offices = [o for o in offices if o.get("AvailableToAi")]

    if not ai_offices:
        section.add(CheckResult(
            name="No private offices published to AI",
            status="fail",
            detail=f"All {total} offices have 'Available to AI' turned off. The AI cannot present any offices to prospects.",
            hint="Enable 'Available to AI' on each office you want the AI to surface.",
        ))
        return section

    if not_ai:
        section.add(CheckResult(
            name=f"{len(not_ai)} of {total} offices not published to AI",
            status="warn",
            detail=_names(not_ai),
            hint="Enable 'Available to AI' on these offices so the AI can include them when presenting options to prospects.",
        ))
        # No data to collect — customer must toggle the setting in Nexudus
    else:
        section.add(CheckResult(
            name="All offices published to AI",
            status="pass",
            detail=f"All {total} private offices have 'Available to AI' enabled.",
        ))

    ai_total = len(ai_offices)

    # ── 3. Availability status of AI-enabled offices ──────────────────────────
    now = datetime.now(timezone.utc)
    available_now  = [o for o in ai_offices if o.get("Available")]
    coming_soon    = [o for o in ai_offices if not o.get("Available") and _is_future(o.get("AvailableFromTime"))]
    no_availability = [o for o in ai_offices if not o.get("Available") and not _is_future(o.get("AvailableFromTime"))]

    status_lines = []
    if available_now:
        status_lines.append(f"{len(available_now)} available now: {_names(available_now)}")
    if coming_soon:
        status_lines.append(f"{len(coming_soon)} coming soon: {_names(coming_soon)}")
    if no_availability:
        status_lines.append(f"{len(no_availability)} with no known availability — will be silently excluded by the AI: {_names(no_availability)}")

    avail_status = "pass" if available_now or coming_soon else "warn"
    section.add(CheckResult(
        name="Office availability",
        status=avail_status,
        detail="\n".join(status_lines) if status_lines else "No availability data.",
        hint="Offices with no active contract and no known end date are silently excluded by the AI. Set contract end dates where known." if no_availability else "",
    ))

    # ── 4. Capacity set ───────────────────────────────────────────────────────
    no_cap = [o for o in ai_offices if not o.get("Capacity")]
    if not no_cap:
        section.add(CheckResult(
            name="Office capacity",
            status="pass",
            detail=f"All {ai_total} AI-enabled offices have capacity set.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_cap)} of {ai_total} AI-enabled offices missing capacity",
            status="warn",
            detail=_names(no_cap),
            hint="Set capacity — the AI collects a team size requirement from the prospect and uses it to filter offices.",
            fields=[{"label": f"Capacity — {o.get('Name', 'Office')}", "placeholder": "e.g. 4 people", "type": "text"} for o in no_cap],
        ))

    # ── 5. Price set ──────────────────────────────────────────────────────────
    no_price = [o for o in ai_offices if not o.get("Price")]
    if not no_price:
        section.add(CheckResult(
            name="Office pricing",
            status="pass",
            detail=f"All {ai_total} AI-enabled offices have a price set.",
        ))
    else:
        currency = no_price[0].get("FloorPlanBusinessCurrencyCode", "") if no_price else ""
        section.add(CheckResult(
            name=f"{len(no_price)} of {ai_total} AI-enabled offices have no price",
            status="warn",
            detail=_names(no_price),
            hint="Set a price — the AI collects a budget from the prospect and uses it to filter offices.",
            fields=[{"label": f"Monthly price — {o.get('Name', 'Office')}", "placeholder": f"e.g. {currency} 1200/month", "type": "text"} for o in no_price],
        ))

    # ── 6. Show price to AI ───────────────────────────────────────────────────
    no_show_price = [o for o in ai_offices if not o.get("ShowPriceForAi")]
    if not no_show_price:
        section.add(CheckResult(
            name="Office pricing visible to AI",
            status="pass",
            detail=f"All {ai_total} AI-enabled offices have 'Show price to AI' enabled.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_show_price)} of {ai_total} offices will not show price to AI",
            status="warn",
            detail=_names(no_show_price),
            hint="Enable 'Show price to AI' so the AI can quote monthly prices and filter offices by budget.",
        ))
        # No data to collect — customer must toggle the setting in Nexudus

    # ── 7. AI price override (informational) ──────────────────────────────────
    with_ai_price = [o for o in ai_offices if o.get("PriceForAi")]
    if with_ai_price:
        rows = ["Office | AI price | Regular price"]
        for o in with_ai_price:
            currency = o.get("FloorPlanBusinessCurrencyCode", "")
            rows.append(f"{o.get('Name')} | {currency} {o.get('PriceForAi')} | {currency} {o.get('Price')}")
        section.add(CheckResult(
            name=f"{len(with_ai_price)} office{'s' if len(with_ai_price) != 1 else ''} using AI price override",
            status="pass",
            detail="\n".join(rows),
        ))

    # ── 8. Notes for AI ───────────────────────────────────────────────────────
    no_notes = [o for o in ai_offices if not (o.get("NotesForAi") or "").strip()]
    if not no_notes:
        section.add(CheckResult(
            name="Office AI notes",
            status="pass",
            detail=f"All {ai_total} AI-enabled offices have AI notes set.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_notes)} of {ai_total} offices have no AI notes",
            status="warn",
            detail=_names(no_notes),
            hint="Add 'Notes for AI' — this is how the AI describes the office to prospects. Include size, natural light, included furniture, and any standout features.",
            fields=[
                {"label": f"AI notes — {o.get('Name', 'Office')}", "placeholder": "Describe this office: size, natural light, furniture, standout features…", "type": "textarea"}
                for o in no_notes
            ],
        ))

    # ── 9. Floor plan area (location within building) ─────────────────────────
    no_area = [o for o in ai_offices if not (o.get("Area") or "").strip()]
    if not no_area:
        section.add(CheckResult(
            name="Office floor plan location",
            status="pass",
            detail=f"All {ai_total} AI-enabled offices have a floor plan area set.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_area)} of {ai_total} offices have no floor plan area",
            status="warn",
            detail=_names(no_area),
            hint="Assign offices to a named floor plan area so the AI can describe where in the building each office is located.",
            fields=[
                {"label": f"Floor plan area — {o.get('Name', 'Office')}", "placeholder": "e.g. 2nd Floor, North Wing", "type": "text"}
                for o in no_area
            ],
        ))

    # ── Tours ─────────────────────────────────────────────────────────────────
    _add_tour_checks(section, business_id)

    return section


def _add_tour_checks(section: Section, business_id: int):
    env = nexudus(["businesssettings", "list",
                   "--business-id", str(business_id),
                   "--name", "PublicWebSite.Tour",
                   "--page-size", "10"])

    if not env.get("ok"):
        section.add(CheckResult(
            name="Tours — settings fetch failed",
            status="fail",
            detail=env.get("summary", "Could not fetch tour settings."),
        ))
        return

    records = env.get("data") or []
    by_name = {r["Name"]: r.get("Value") for r in records}

    tours_enabled = by_name.get("PublicWebSite.Tour", "").lower() == "true"

    if not tours_enabled:
        section.add(CheckResult(
            name="Tours not enabled",
            status="warn",
            detail="The AI cannot offer to book tours for prospects.",
            hint="Enable tours in your portal settings (Portal › Tour) so the AI can schedule viewings when prospects ask to see the space.",
            fields=[{"label": "Tour host name", "placeholder": "Who will host tours?", "type": "text"},
                    {"label": "Available tour hours", "placeholder": "e.g. Mon–Fri 9am–5pm", "type": "text"}],
        ))
        return

    section.add(CheckResult(
        name="Tours enabled",
        status="pass",
        detail="The AI will offer to schedule tours when prospects ask to view the space.",
    ))

    # ── Tour host ──────────────────────────────────────────────────────────────
    host_id = by_name.get("PublicWebSite.Tour.Host", "").strip()
    if not host_id:
        section.add(CheckResult(
            name="No tour host set",
            status="fail",
            detail="A tour host is required — the AI books tours with a specific team member.",
            hint="Assign a tour host in Portal › Tour settings.",
            fields=[{"label": "Tour host name / email", "placeholder": "Full name and email of the team member who will host tours", "type": "text"}],
        ))
    else:
        host_env = nexudus(["users", "get", host_id])
        if host_env.get("ok") and host_env.get("data"):
            host_name = host_env["data"].get("FullName") or f"User {host_id}"
        else:
            host_name = f"User {host_id}"
        section.add(CheckResult(
            name="Tour host set",
            status="pass",
            detail=f"Tour host: {host_name}",
        ))

    # ── Requires confirmation (informational) ──────────────────────────────────
    requires_confirm = by_name.get("PublicWebSite.Tour.RequiresConfirmation", "").lower() == "true"
    section.add(CheckResult(
        name="Tours require confirmation" if requires_confirm else "Tours auto-confirmed",
        status="pass",
        detail=(
            "Tour requests are held for manual approval before being confirmed to the prospect."
            if requires_confirm else
            "Tour bookings are confirmed automatically without manual approval."
        ),
    ))

    # ── Time slots ────────────────────────────────────────────────────────────
    slots_enabled = by_name.get("PublicWebSite.Tour.TimeSlots.Enabled", "").lower() == "true"
    slots_json    = by_name.get("PublicWebSite.Tour.TimeSlots", "")

    if not slots_enabled:
        section.add(CheckResult(
            name="Tour time slots not restricted",
            status="warn",
            detail="The AI has no time constraints when suggesting tour slots — prospects could request tours at any hour.",
            hint="Enable tour time slots in Portal › Tour settings and configure the hours the team is available for viewings.",
            fields=[{"label": "Available tour hours", "placeholder": "e.g. Mon–Fri 9:00–17:00, Sat 10:00–14:00", "type": "text"}],
        ))
        return

    if not slots_json:
        section.add(CheckResult(
            name="Tour time slots enabled but none configured",
            status="fail",
            detail="Time slot restriction is on but no slots are defined. The AI will have no valid windows to offer prospects.",
            hint="Add at least one tour time slot in Portal › Tour settings.",
            fields=[{"label": "Available tour hours", "placeholder": "e.g. Mon–Fri 9:00–17:00, Sat 10:00–14:00", "type": "text"}],
        ))
        return

    try:
        slots = json.loads(slots_json)
    except (json.JSONDecodeError, TypeError):
        section.add(CheckResult(
            name="Tour time slots — could not parse",
            status="warn",
            detail="The time slot data returned from the API could not be read.",
        ))
        return

    if not slots:
        section.add(CheckResult(
            name="Tour time slots enabled but empty",
            status="fail",
            detail="No tour time slots are configured.",
            hint="Add at least one tour time slot in Portal › Tour settings.",
        ))
        return

    rows = ["Day | From | To"]
    for s in slots:
        day      = s.get("DayOfWeek")
        from_t   = (s.get("FromTime") or "").split("T")[-1][:5]
        to_t     = (s.get("ToTime")   or "").split("T")[-1][:5]
        day_name = DAY_NAMES.get(day, str(day))
        rows.append(f"{day_name} | {from_t} | {to_t}")

    section.add(CheckResult(
        name=f"Tour time slots configured ({len(slots)} day{'s' if len(slots) != 1 else ''})",
        status="pass",
        detail="\n".join(rows),
    ))
