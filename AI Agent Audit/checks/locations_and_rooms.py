"""
Checks — Location Details & Rooms
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


def _present(val: str) -> bool:
    v = (val or "").strip()
    return bool(v) or "«PII:" in v


def _amenity_count(resource: dict) -> int:
    return sum(1 for f in AMENITY_FLAGS if resource.get(f))


def check_location_details(business_id: int) -> Section:
    section = Section("Location Details")

    biz_env = nexudus(["businesses", "get", str(business_id)])
    if not biz_env.get("ok"):
        section.add(CheckResult(
            name="Business profile — data fetch",
            status="fail",
            detail=biz_env.get("summary", "Failed to fetch business profile."),
        ))
        return section

    biz = biz_env.get("data", {})

    # ── Core location fields ───────────────────────────────────────────────────
    # The AI reads: Name, Address, City, Postcode, Country, Phone, Email
    def _display(val: str) -> str:
        v = (val or "").strip()
        if not v:
            return None
        if "«PII:" in v:
            return "[protected]"
        return v

    raw_fields = {
        "Name":     biz.get("Name", ""),
        "Address":  biz.get("Address", ""),
        "City":     biz.get("TownCity", ""),
        "Postcode": biz.get("PostalCode", ""),
        "Country":  biz.get("CountryName", ""),
        "Phone":    biz.get("Phone", ""),
        "Email":    biz.get("EmailContact", "") or biz.get("ContactEmail", ""),
    }

    field_lines = []
    missing = []
    for label, raw in raw_fields.items():
        value = _display(raw)
        if value:
            field_lines.append(f"{label}: {value}")
        else:
            field_lines.append(f"{label}: —")
            missing.append(label)

    detail = "\n".join(field_lines)

    PLACEHOLDERS = {
        "City":     "e.g. Manchester",
        "Postcode": "e.g. M1 1AE",
        "Address":  "e.g. 123 High Street",
        "Phone":    "e.g. +44 161 000 0000",
        "Email":    "e.g. hello@yourspace.com",
    }

    if not missing:
        section.add(CheckResult(
            name="Location fields",
            status="pass",
            detail=detail,
        ))
    elif len(missing) <= 2:
        section.add(CheckResult(
            name="Location fields",
            status="warn",
            detail=detail,
            hint=f"Missing: {', '.join(missing)}. Fill in these fields on your business profile.",
            fields=[{"label": m, "placeholder": PLACEHOLDERS.get(m, f"Enter your {m.lower()}"), "type": "text"} for m in missing],
        ))
    else:
        section.add(CheckResult(
            name="Location fields",
            status="fail",
            detail=detail,
            hint=f"Missing: {', '.join(missing)}. The AI cannot give accurate location information without these fields.",
            fields=[{"label": m, "placeholder": PLACEHOLDERS.get(m, f"Enter your {m.lower()}"), "type": "text"} for m in missing],
        ))

    # ── Coordinates (enables distance ordering) ────────────────────────────────
    lat = biz.get("Latitude")
    lng = biz.get("Longitude")
    if lat and lng and (lat != 0 or lng != 0):
        section.add(CheckResult(
            name="Location coordinates set",
            status="pass",
            detail=f"Latitude {lat}, Longitude {lng}. Distance ordering is available on chat and voice.",
        ))
    else:
        section.add(CheckResult(
            name="Location coordinates set",
            status="warn",
            detail="Latitude/Longitude not set. The AI cannot order results by distance from the user.",
            hint="Set coordinates on your business profile (Settings > Location).",
            fields=[
                {"label": "Latitude", "placeholder": "e.g. 53.48431", "type": "text"},
                {"label": "Longitude", "placeholder": "e.g. -2.22810", "type": "text"},
            ],
        ))

    # ── Opening hours ──────────────────────────────────────────────────────────
    def _fmt_time(minutes: int) -> str:
        h, m = divmod(int(minutes), 60)
        return f"{h:02d}:{m:02d}"

    all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_lines = []
    weekdays_with_hours = 0

    for day in all_days:
        closed   = biz.get(f"{day}Closed")
        open_t   = biz.get(f"{day}OpenTime")
        close_t  = biz.get(f"{day}CloseTime")
        if closed:
            day_lines.append(f"{day}: Closed")
        elif open_t and close_t:
            day_lines.append(f"{day}: {_fmt_time(open_t)} – {_fmt_time(close_t)}")
            if day not in ("Saturday", "Sunday"):
                weekdays_with_hours += 1
        else:
            day_lines.append(f"{day}: —")

    detail = "\n".join(day_lines)

    if weekdays_with_hours >= 5:
        section.add(CheckResult(
            name="Opening hours",
            status="pass",
            detail=detail,
        ))
    elif weekdays_with_hours > 0:
        section.add(CheckResult(
            name="Opening hours",
            status="warn",
            detail=detail,
            hint="Some weekdays are missing opening hours — the AI may not answer 'when are you open?' accurately.",
        ))
    else:
        section.add(CheckResult(
            name="Opening hours",
            status="fail",
            detail=detail,
            hint="Add opening hours to your business profile.",
        ))

    return section


def check_rooms_and_resources(business_id: int) -> Section:
    section = Section("Rooms & Resources")

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

    # ── Visible resources exist ────────────────────────────────────────────────
    if total == 0:
        section.add(CheckResult(
            name="Visible rooms and resources exist",
            status="fail",
            detail="No visible, active resources found. The AI has nothing to show when asked about rooms.",
            hint="Create and publish bookable resources in Nexudus.",
        ))
        return section

    section.add(CheckResult(
        name="Visible rooms and resources exist",
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
            fields=[{"label": f"Description — {r.get('Name', 'Resource')}", "placeholder": "Describe this room: features, equipment, what it's ideal for…", "type": "textarea"} for r in no_desc],
        ))
    else:
        names = ", ".join(r.get("Name", "Unnamed") for r in no_desc[:3])
        more  = f" and {len(no_desc)-3} more" if len(no_desc) > 3 else ""
        section.add(CheckResult(
            name=f"{len(no_desc)} of {total} resources missing descriptions",
            status="warn",
            detail=f"{names}{more}.",
            hint="Add descriptions so the AI can explain what each room offers.",
            fields=[{"label": f"Description — {r.get('Name', 'Resource')}", "placeholder": "Describe this room: features, equipment, what it's ideal for…", "type": "textarea"} for r in no_desc],
        ))

    # ── Capacity ───────────────────────────────────────────────────────────────
    no_capacity = [r for r in resources if not r.get("Allocation")]
    if not no_capacity:
        section.add(CheckResult(
            name="Resource capacity",
            status="pass",
            detail=f"All {total} resources have capacity set.",
        ))
    else:
        names = ", ".join(r.get("Name", "Unnamed") for r in no_capacity[:3])
        more  = f" and {len(no_capacity)-3} more" if len(no_capacity) > 3 else ""
        section.add(CheckResult(
            name=f"{len(no_capacity)} of {total} resources missing capacity",
            status="warn",
            detail=f"{names}{more}.",
            hint="Set the Allocation field — the AI shows capacity in every room card.",
            fields=[{"label": f"Capacity — {r.get('Name', 'Resource')}", "placeholder": "e.g. 8 people", "type": "text"} for r in no_capacity],
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
        names = ", ".join(r.get("Name", "Unnamed") for r in no_amenities[:3])
        more  = f" and {len(no_amenities)-3} more" if len(no_amenities) > 3 else ""
        section.add(CheckResult(
            name=f"{len(no_amenities)} of {total} resources have no amenity flags",
            status="warn",
            detail=f"{names}{more}.",
            hint="Set amenity flags (projector, whiteboard, etc.) so the AI can answer 'does it have AV equipment?'",
        ))

    # ── Visibility restriction summary ─────────────────────────────────────────
    members_only  = [r for r in resources if r.get("OnlyForMembers")]
    contacts_only = [r for r in resources if r.get("OnlyForContacts")]
    restricted    = members_only + contacts_only

    if not restricted:
        section.add(CheckResult(
            name="Resource visibility restrictions",
            status="pass",
            detail=f"All {total} resources are visible to everyone — prospects can browse all rooms.",
        ))
    else:
        parts = []
        if members_only:
            names = ", ".join(r.get("Name", "Unnamed") for r in members_only[:2])
            more  = f" +{len(members_only)-2}" if len(members_only) > 2 else ""
            parts.append(f"{len(members_only)} members-only: {names}{more}")
        if contacts_only:
            names = ", ".join(r.get("Name", "Unnamed") for r in contacts_only[:2])
            more  = f" +{len(contacts_only)-2}" if len(contacts_only) > 2 else ""
            parts.append(f"{len(contacts_only)} contacts-only: {names}{more}")
        section.add(CheckResult(
            name="Resource visibility restrictions",
            status="pass",
            detail=f"{len(restricted)} of {total} resources are restricted — the AI will not show these to anonymous visitors. {'; '.join(parts)}.",
        ))

    return section
