"""
Checks — Rooms & Resources
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import Section, CheckResult, nexudus

AMENITY_FLAGS = [
    "Projector", "Internet", "ConferencePhone", "StandardPhone", "WhiteBoard",
    "LargeDisplay", "Catering", "TeaAndCoffee", "AirConditioning", "Heating",
    "NaturalLight", "StandingDesk", "QuietZone", "Soundproof", "VideoConferencing",
    "WirelessPresentation", "PaSystem", "FlipChart", "SecurityLock", "PrivacyScreen",
]


def _amenity_count(r: dict) -> int:
    return sum(1 for f in AMENITY_FLAGS if r.get(f))


def _names(resources: list, limit: int = 3) -> str:
    names = ", ".join(r.get("Name", "Unnamed") for r in resources[:limit])
    more  = f" and {len(resources) - limit} more" if len(resources) > limit else ""
    return names + more


def check_rooms_and_resources(business_id: int) -> Section:
    section = Section("Rooms & Resources")

    # ── Fetch visible resources ────────────────────────────────────────────────
    res_env = nexudus(["resources", "list",
                       "--business-id", str(business_id),
                       "--visible", "true",
                       "--archived", "false",
                       "--page-size", "100"])

    if not res_env.get("ok"):
        section.add(CheckResult(
            name="Rooms & resources — data fetch",
            status="fail",
            detail=res_env.get("summary", "Failed to fetch resources."),
        ))
        return section

    resources = res_env.get("data") or []
    total = len(resources)

    # ── Exist ──────────────────────────────────────────────────────────────────
    if total == 0:
        section.add(CheckResult(
            name="No visible rooms or resources",
            status="fail",
            detail="The AI has nothing to show when asked about rooms.",
            hint="Create and publish bookable resources in Nexudus.",
        ))
        return section

    section.add(CheckResult(
        name="Visible rooms and resources",
        status="pass",
        detail=f"{total} visible resource{'s' if total != 1 else ''} found.",
    ))

    # ── Descriptions ───────────────────────────────────────────────────────────
    no_desc = [r for r in resources if not (r.get("Description") or "").strip()]
    if not no_desc:
        section.add(CheckResult(
            name="Resource descriptions",
            status="pass",
            detail=f"All {total} resources have descriptions.",
        ))
    elif len(no_desc) == total:
        section.add(CheckResult(
            name="No resources have descriptions",
            status="fail",
            detail="The AI returns descriptions verbatim in room cards — without them it has nothing to say about each room.",
            hint="Add a description to every room and resource.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_desc)} of {total} resources missing descriptions",
            status="warn",
            detail=_names(no_desc),
            hint="Add descriptions so the AI can explain what each room offers.",
        ))

    # ── Capacity ───────────────────────────────────────────────────────────────
    no_cap = [r for r in resources if not r.get("Allocation")]
    if not no_cap:
        section.add(CheckResult(
            name="Resource capacity",
            status="pass",
            detail=f"All {total} resources have capacity set.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_cap)} of {total} resources missing capacity",
            status="warn",
            detail=_names(no_cap),
            hint="Set the Allocation field — the AI shows capacity in every room card.",
        ))

    # ── Amenity flags ──────────────────────────────────────────────────────────
    no_amenities = [r for r in resources if _amenity_count(r) == 0]
    if not no_amenities:
        section.add(CheckResult(
            name="Resource amenity flags",
            status="pass",
            detail=f"All {total} resources have at least one amenity flag set.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_amenities)} of {total} resources have no amenity flags",
            status="warn",
            detail=_names(no_amenities),
            hint="Set amenity flags (projector, whiteboard, etc.) so the AI can answer 'does it have AV equipment?'",
        ))

    # ── Booking duration limits ────────────────────────────────────────────────
    no_duration = [
        r for r in resources
        if not r.get("MinBookingLength") and not r.get("MaxBookingLength")
    ]
    if not no_duration:
        section.add(CheckResult(
            name="Booking duration limits",
            status="pass",
            detail=f"All {total} resources have min/max booking length set.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_duration)} of {total} resources missing booking duration limits",
            status="warn",
            detail=_names(no_duration),
            hint="Set MinBookingLength and MaxBookingLength so the AI can answer 'how long can I book it for?'",
        ))

    # ── Advance booking limit ──────────────────────────────────────────────────
    no_advance = [r for r in resources if not r.get("BookInAdvanceLimit")]
    if not no_advance:
        section.add(CheckResult(
            name="Advance booking limits",
            status="pass",
            detail=f"All {total} resources have an advance booking limit set.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_advance)} of {total} resources missing advance booking limit",
            status="warn",
            detail=_names(no_advance),
            hint="Set BookInAdvanceLimit so the AI can answer 'how far ahead can I book?'",
        ))

    # ── Late booking limit ─────────────────────────────────────────────────────
    no_late = [r for r in resources if not r.get("LateBookingLimit")]
    if not no_late:
        section.add(CheckResult(
            name="Minimum booking notice",
            status="pass",
            detail=f"All {total} resources have a minimum booking notice set.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_late)} of {total} resources missing minimum booking notice",
            status="warn",
            detail=_names(no_late),
            hint="Set LateBookingLimit so the AI can answer 'how much notice do I need to book?'",
        ))

    # ── Cancellation policy ────────────────────────────────────────────────────
    no_cancel = [r for r in resources if not r.get("LateCancellationLimit")]
    if not no_cancel:
        section.add(CheckResult(
            name="Cancellation policy",
            status="pass",
            detail=f"All {total} resources have a cancellation policy set.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_cancel)} of {total} resources missing cancellation policy",
            status="warn",
            detail=_names(no_cancel),
            hint="Set LateCancellationLimit so the AI can explain your cancellation rules.",
        ))

    # ── Confirmation required (informational) ─────────────────────────────────
    needs_confirm = [r for r in resources if r.get("RequiresConfirmation")]
    if needs_confirm:
        section.add(CheckResult(
            name=f"{len(needs_confirm)} resource{'s' if len(needs_confirm) != 1 else ''} require{'s' if len(needs_confirm) == 1 else ''} booking confirmation",
            status="pass",
            detail=f"{_names(needs_confirm)}. The AI will inform users that bookings are subject to approval.",
        ))

    # ── Time slots (requires individual get per resource) ─────────────────────
    no_slots = []
    for r in resources:
        detail_env = nexudus(["resources", "get", str(r["Id"])])
        if detail_env.get("ok"):
            slots = detail_env.get("data", {}).get("TimeSlots") or []
            if not slots:
                no_slots.append(r)

    if not no_slots:
        section.add(CheckResult(
            name="Resource availability time slots",
            status="pass",
            detail=f"All {total} resources have time slots configured.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_slots)} of {total} resources missing time slots",
            status="warn",
            detail=_names(no_slots),
            hint="Add time slots to each resource — without them the AI cannot describe when the room is available for booking.",
        ))

    # ── Pricing (booking rates via ExtraServices) ──────────────────────────────
    rates_env = nexudus(["extraservices", "list",
                         "--business-id", str(business_id),
                         "--page-size", "100"])

    if not rates_env.get("ok"):
        section.add(CheckResult(
            name="Resource pricing — data fetch",
            status="fail",
            detail=rates_env.get("summary", "Failed to fetch booking rates."),
        ))
    else:
        rates = rates_env.get("data") or []
        # Build set of resource type names that have at least one rate
        covered_types = set()
        for rate in rates:
            for name in (rate.get("ResourceTypeNames") or "").split(","):
                covered_types.add(name.strip())

        no_pricing = [
            r for r in resources
            if r.get("ResourceTypeName") not in covered_types
        ]

        if not no_pricing:
            section.add(CheckResult(
                name="Resource pricing",
                status="pass",
                detail=f"All {total} resources have at least one booking rate configured.",
            ))
        else:
            section.add(CheckResult(
                name=f"{len(no_pricing)} of {total} resources have no booking rates",
                status="warn",
                detail=_names(no_pricing),
                hint="Add booking rates to these resource types — without pricing the AI cannot quote a cost.",
            ))

    # ── Visibility restrictions (informational) ────────────────────────────────
    members_only  = [r for r in resources if r.get("OnlyForMembers")]
    contacts_only = [r for r in resources if r.get("OnlyForContacts")]
    restricted    = members_only + contacts_only

    if not restricted:
        section.add(CheckResult(
            name="Resource visibility",
            status="pass",
            detail=f"All {total} resources are visible to everyone.",
        ))
    else:
        parts = []
        if members_only:
            parts.append(f"{len(members_only)} members-only: {_names(members_only, 2)}")
        if contacts_only:
            parts.append(f"{len(contacts_only)} contacts-only: {_names(contacts_only, 2)}")
        section.add(CheckResult(
            name=f"{len(restricted)} of {total} resources are access-restricted",
            status="pass",
            detail=f"The AI will not show these to anonymous visitors. {'; '.join(parts)}.",
        ))

    return section
