"""
Checks — Day Passes
AI capability: list and sell day passes across all channels.

Product AI fields: AvailableToAi, NotesForAi, ShowPriceForAi, PriceForAi
Resource day-use kind: SystemResourceType — HotDesk=2, PrivateOffice=3 (Day Office), DayPass=11
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import Section, CheckResult, nexudus

DAY_PASS_PRODUCT_TYPE = 1   # eProductType.DayPass

PRODUCT_TYPE_NAMES = {
    0: "None", 1: "Day Pass", 2: "Credit Bundle", 3: "Stationery",
    4: "Booking Feature", 5: "Booking Products", 99: "Other",
}

RESOURCE_KIND_NAMES = {
    0: "None", 1: "Meeting Room", 2: "Hot Desk", 3: "Private Office",
    4: "Event Space", 5: "Lab", 6: "Kitchen", 7: "Treatment Room",
    9: "Storage Unit", 10: "Machine", 11: "Day Pass", 12: "Phone Booth", 99: "Other",
}

# eResourceType values the AI surfaces as bookable day-use spaces
DAY_USE_RESOURCE_KINDS = {2, 3, 11}   # HotDesk, PrivateOffice (Day Office), DayPass
DAY_USE_KIND_LABELS = {2: "Hot Desk", 3: "Day Office", 11: "Day Pass"}


def _names(items: list, key: str = "Name", limit: int = 3) -> str:
    ns = ", ".join(str(i.get(key, "Unnamed")) for i in items[:limit])
    more = f" and {len(items) - limit} more" if len(items) > limit else ""
    return ns + more


def check_day_passes(business_id: int) -> Section:
    section = Section("Day Passes")

    # ── Fetch all non-archived day pass products ───────────────────────────────
    prod_env = nexudus(["products", "list",
                        "--business-id", str(business_id),
                        "--system-product-type", "1",
                        "--archived", "false",
                        "--page-size", "100"])

    if not prod_env.get("ok"):
        section.add(CheckResult(
            name="Day pass products — data fetch",
            status="fail",
            detail=prod_env.get("summary", "Failed to fetch products."),
        ))
        return section

    day_passes = prod_env.get("data") or []
    total      = len(day_passes)

    # ── 0. Scan ALL products for likely-day-pass items with wrong type ─────────
    # Fetch non-archived products of any type to find miscategorised ones
    all_env = nexudus(["products", "list",
                       "--business-id", str(business_id),
                       "--archived", "false",
                       "--page-size", "100"])

    DAY_PASS_KEYWORDS = [
        "day pass", "day-pass", "daypass",
        "drop in", "drop-in", "dropin",
        "daily pass", "day rate", "day ticket",
        "hot desk pass", "coworking pass", "workspace pass",
        "flexi pass", "flexible pass",
        "visitor pass", "guest pass",
    ]

    if all_env.get("ok"):
        all_products = all_env.get("data") or []
        mistyped = []
        for p in all_products:
            if p.get("SystemProductType") == DAY_PASS_PRODUCT_TYPE:
                continue
            text = (
                (p.get("Name") or "") + " " +
                (p.get("Description") or "")
            ).lower()
            if any(kw in text for kw in DAY_PASS_KEYWORDS):
                mistyped.append(p)

        if mistyped:
            rows = ["Product | Current type | Should be"]
            for p in mistyped:
                current = PRODUCT_TYPE_NAMES.get(p.get("SystemProductType"), str(p.get("SystemProductType", "?")))
                rows.append(f"{p.get('Name')} | {current} | Day Pass")
            section.add(CheckResult(
                name=f"{len(mistyped)} product{'s' if len(mistyped) != 1 else ''} may be a day pass set to the wrong product type",
                status="warn",
                detail="\n".join(rows),
                hint="These look like day pass products but are not set to product type 'Day Pass'. Without the correct type they won't appear in AI day pass results and can't use the AI visibility settings.",
            ))

    # ── 1. Day pass products exist ─────────────────────────────────────────────
    if total == 0:
        section.add(CheckResult(
            name="No day pass products found",
            status="fail",
            detail="The AI has nothing to present when asked about day passes.",
            hint="Create at least one day pass product in Nexudus (Portal › Products) with SystemProductType = Day Pass.",
            fields=[
                {"label": "Day pass name", "placeholder": "e.g. Single Day Pass", "type": "text"},
                {"label": "Day pass price", "placeholder": "e.g. £25", "type": "text"},
                {"label": "Day pass description", "placeholder": "What's included — desk access, Wi-Fi, coffee, etc.", "type": "textarea"},
            ],
        ))
    else:
        section.add(CheckResult(
            name=f"{total} day pass product{'s' if total != 1 else ''} found",
            status="pass",
            detail=_names(day_passes),
        ))

        # ── 2. AvailableToAi — the master AI switch ────────────────────────────
        # The CLI omits false/null fields, so absence of the key = not enabled
        not_ai = [p for p in day_passes if not p.get("AvailableToAi")]
        if not_ai:
            section.add(CheckResult(
                name=f"{len(not_ai)} of {total} day passes not published to AI",
                status="fail",
                detail=_names(not_ai),
                hint="Set 'Available to AI' on each day pass — without it the AI will never mention the product regardless of other settings.",
            ))
        else:
            section.add(CheckResult(
                name="All day passes published to AI",
                status="pass",
                detail=f"All {total} day pass product{'s' if total != 1 else ''} {'have' if total != 1 else 'has'} 'Available to AI' enabled.",
            ))

        # ── 3. Visibility — hidden passes get 'contact us' response only ───────
        hidden = [p for p in day_passes if not p.get("Visible")]
        if hidden:
            section.add(CheckResult(
                name=f"{len(hidden)} of {total} day passes not visible",
                status="warn",
                detail=_names(hidden),
                hint="Hidden passes: the AI tells users to contact the team but cannot show a price or purchase link. Set Visible = on for full self-serve.",
            ))
        else:
            section.add(CheckResult(
                name="Day pass visibility",
                status="pass",
                detail=f"All {total} day pass product{'s' if total != 1 else ''} {'are' if total != 1 else 'is'} visible.",
            ))

        # ── 4. Descriptions ────────────────────────────────────────────────────
        no_desc = [p for p in day_passes if not (p.get("Description") or "").strip()]
        if not no_desc:
            section.add(CheckResult(
                name="Day pass descriptions",
                status="pass",
                detail=f"All {total} day pass product{'s' if total != 1 else ''} have descriptions.",
            ))
        else:
            section.add(CheckResult(
                name=f"{len(no_desc)} of {total} day passes missing descriptions",
                status="warn",
                detail=_names(no_desc),
                hint="Add descriptions — the AI presents them in the day pass card alongside the purchase link.",
                fields=[{"label": f"Description — {p.get('Name', 'Day pass')}", "placeholder": "What's included, who it's for, any access details…", "type": "textarea"} for p in no_desc],
            ))

        # ── 5. ShowPriceForAi ──────────────────────────────────────────────────
        no_price_shown = [p for p in day_passes if not p.get("ShowPriceForAi")]
        if no_price_shown:
            section.add(CheckResult(
                name=f"{len(no_price_shown)} of {total} day passes will not show price to AI",
                status="warn",
                detail=_names(no_price_shown),
                hint="Enable 'Show price to AI' so the AI can quote a price and filter by budget when users ask for options under a certain amount.",
            ))
        else:
            section.add(CheckResult(
                name="Day pass pricing visible to AI",
                status="pass",
                detail=f"All {total} day pass product{'s' if total != 1 else ''} {'have' if total != 1 else 'has'} price shown to AI.",
            ))

        # ── 6. PriceForAi override (informational) ─────────────────────────────
        with_ai_price = [p for p in day_passes if p.get("PriceForAi")]
        if with_ai_price:
            lines = [
                f"{p.get('Name')}: {p.get('CurrencyCode', '')} {p.get('PriceForAi')} (regular: {p.get('Price')})"
                for p in with_ai_price
            ]
            section.add(CheckResult(
                name=f"{len(with_ai_price)} day pass{'es' if len(with_ai_price) != 1 else ''} using AI price override",
                status="pass",
                detail="\n".join(lines),
            ))

        # ── 7. NotesForAi ──────────────────────────────────────────────────────
        no_notes = [p for p in day_passes if not (p.get("NotesForAi") or "").strip()]
        if no_notes:
            section.add(CheckResult(
                name=f"{len(no_notes)} of {total} day passes have no AI notes",
                status="warn",
                detail=_names(no_notes),
                hint="Add 'Notes for AI' to enrich how the AI describes each pass — include what's included, who it suits, or any access details.",
                fields=[{"label": f"AI notes — {p.get('Name', 'Day pass')}", "placeholder": "What's included, who it suits, access details, any restrictions…", "type": "textarea"} for p in no_notes],
            ))
        else:
            section.add(CheckResult(
                name="Day pass AI notes",
                status="pass",
                detail=f"All {total} day pass product{'s' if total != 1 else ''} have AI notes set.",
            ))

        # ── 8. Audience restrictions ───────────────────────────────────────────
        members_only  = [p for p in day_passes if p.get("OnlyForMembers")]
        contacts_only = [p for p in day_passes if p.get("OnlyForContacts")]
        restricted    = members_only + contacts_only

        if not restricted:
            section.add(CheckResult(
                name="Day pass audience",
                status="pass",
                detail="All day passes are available to everyone — the AI can show them to anonymous visitors.",
            ))
        else:
            parts = []
            if members_only:
                parts.append(f"{len(members_only)} members-only: {_names(members_only, 2)}")
            if contacts_only:
                parts.append(f"{len(contacts_only)} contacts-only: {_names(contacts_only, 2)}")
            section.add(CheckResult(
                name=f"{len(restricted)} of {total} day passes are audience-restricted",
                status="warn",
                detail="; ".join(parts) + ". Anonymous visitors will not see these.",
                hint="If you want to sell day passes to prospective visitors, remove the audience restriction.",
            ))

    # ── 9. Bookable day-use resources by SystemResourceType ───────────────────
    res_env = nexudus(["resources", "list",
                       "--business-id", str(business_id),
                       "--archived", "false",
                       "--page-size", "100"])

    if not res_env.get("ok"):
        section.add(CheckResult(
            name="Day-use bookable resources — data fetch",
            status="fail",
            detail=res_env.get("summary", "Failed to fetch resources."),
        ))
        return section

    resources     = res_env.get("data") or []
    day_resources = [
        r for r in resources
        if r.get("Visible") and r.get("SystemResourceType") in DAY_USE_RESOURCE_KINDS
    ]

    # Keywords per kind — used to detect resources with the wrong SystemResourceType
    RESOURCE_KIND_KEYWORDS = {
        "Hot Desk":   ["hot desk", "hot-desk", "hotdesk", "floating desk", "flex desk", "flexi desk", "hot desks"],
        "Day Office": ["day office", "day-office"],
        "Day Pass":   ["day pass", "day-pass", "daypass", "drop in", "drop-in"],
    }
    CORRECT_KIND = {"Hot Desk": 2, "Day Office": 3, "Day Pass": 11}

    mistyped_resources = []
    for r in resources:
        kind = r.get("SystemResourceType")
        if kind in DAY_USE_RESOURCE_KINDS:
            continue  # already correct
        text = (
            (r.get("Name") or "") + " " +
            (r.get("ResourceTypeName") or "") + " " +
            (r.get("Description") or "")
        ).lower()
        for label, keywords in RESOURCE_KIND_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                mistyped_resources.append((r, label))
                break

    if mistyped_resources:
        rows = ["Resource | Current kind | Should be"]
        for r, label in mistyped_resources:
            current = RESOURCE_KIND_NAMES.get(r.get("SystemResourceType"), str(r.get("SystemResourceType", "?")))
            rows.append(f"{r.get('Name')} | {current} | {label}")
        section.add(CheckResult(
            name=f"{len(mistyped_resources)} resource{'s' if len(mistyped_resources) != 1 else ''} may have the wrong Resource Kind set",
            status="warn",
            detail="\n".join(rows),
            hint="Set the Resource Kind to 'Hot Desk', 'Day Office', or 'Day Pass' on these resources so the AI surfaces them when users ask about day use options.",
        ))

    if not day_resources:
        section.add(CheckResult(
            name="No bookable day-use resources",
            status="warn",
            detail=(
                "The AI surfaces bookable resources with a Resource Kind of Day Pass, Day Office, or Hot Desk "
                "alongside day pass products. None exist in this account."
            ),
            hint="If you have hot desks or day offices, set their Resource Kind so the AI can include them in results.",
        ))
    else:
        dr_total = len(day_resources)
        type_summary = {}
        for r in day_resources:
            label = DAY_USE_KIND_LABELS.get(r.get("SystemResourceType"), "Unknown")
            type_summary[label] = type_summary.get(label, 0) + 1
        ts = ", ".join(f"{n} × {t}" for t, n in sorted(type_summary.items()))

        section.add(CheckResult(
            name=f"{dr_total} day-use bookable resource{'s' if dr_total != 1 else ''}",
            status="pass",
            detail=f"{ts}. The AI shows these alongside day pass products.",
        ))

        no_desc = [r for r in day_resources if not (r.get("Description") or "").strip()]
        no_cap  = [r for r in day_resources if not r.get("Allocation")]

        if no_desc:
            section.add(CheckResult(
                name=f"{len(no_desc)} of {dr_total} day-use resources missing descriptions",
                status="warn",
                detail=_names(no_desc),
                hint="Add descriptions — the AI presents them when listing day-use space options.",
                fields=[{"label": f"Description — {r.get('Name', 'Resource')}", "placeholder": "Describe this space: size, equipment, what it's ideal for…", "type": "textarea"} for r in no_desc],
            ))
        if no_cap:
            section.add(CheckResult(
                name=f"{len(no_cap)} of {dr_total} day-use resources missing capacity",
                status="warn",
                detail=_names(no_cap),
                hint="Set capacity (Allocation) — the AI shows how many people each space fits.",
                fields=[{"label": f"Capacity — {r.get('Name', 'Resource')}", "placeholder": "e.g. 6 people", "type": "text"} for r in no_cap],
            ))

    return section
