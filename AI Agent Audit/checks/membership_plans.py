"""
Checks — Membership Plans
AI capability: present and sell membership plans across all channels.

Tariff AI fields: AvailableToAi, ShowPriceForAi, PriceForAi, NotesForAi
eTariffType enum:
  1=FullTimePrivateOffice  2=PartTimePrivateOffice
  3=FullTimeDedicatedDesk  4=PartTimeDedicatedDesk
  5=FullTimeHotDesk        6=PartTimeHotDesk
  7=FullTimeOther          8=PartTimeOther
  9=Storage               10=VirtualOffice  11=Virtual  99=Other
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import Section, CheckResult, nexudus

TARIFF_TYPE_NAMES = {
    1: "Full-time Private Office",  2: "Part-time Private Office",
    3: "Full-time Dedicated Desk",  4: "Part-time Dedicated Desk",
    5: "Full-time Hot Desk",        6: "Part-time Hot Desk",
    7: "Full-time Other",           8: "Part-time Other",
    9: "Storage",                  10: "Virtual Office",
    11: "Virtual",                 99: "Other",
}

# The three categories the AI understands and maps natural language to
AI_CATEGORIES = {
    "Hot Desk":        {5, 6},
    "Dedicated Desk":  {3, 4},
    "Virtual Office":  {10, 11},
}

# Keyword sets for miscategorisation detection (name + description)
MISTYPE_KEYWORDS = {
    "Hot Desk":        ["hot desk", "hot-desk", "hotdesk", "flex desk", "flexi desk",
                        "floating desk", "shared desk", "coworking desk"],
    "Dedicated Desk":  ["dedicated desk", "fixed desk", "assigned desk", "permanent desk"],
    "Virtual Office":  ["virtual office", "postal address", "registered address",
                        "mail address", "mailing address"],
}
CORRECT_TYPES = {
    "Hot Desk":       "Full-time Hot Desk or Part-time Hot Desk",
    "Dedicated Desk": "Full-time Dedicated Desk or Part-time Dedicated Desk",
    "Virtual Office": "Virtual Office or Virtual",
}


def _names(items: list, key: str = "Name", limit: int = 3) -> str:
    ns = ", ".join(str(i.get(key, "Unnamed")) for i in items[:limit])
    more = f" and {len(items) - limit} more" if len(items) > limit else ""
    return ns + more


def check_membership_plans(business_id: int) -> Section:
    section = Section("Membership Plans")

    env = nexudus(["tariffs", "list",
                   "--business-id", str(business_id),
                   "--archived", "false",
                   "--page-size", "100"])

    if not env.get("ok"):
        section.add(CheckResult(
            name="Membership plans — data fetch",
            status="fail",
            detail=env.get("summary", "Failed to fetch tariffs."),
        ))
        return section

    all_tariffs = env.get("data") or []

    # ── 0. Miscategorised plans ────────────────────────────────────────────────
    wrong_types = {}   # label → list of (tariff, suggested_label)
    all_correct_types = set().union(*AI_CATEGORIES.values())

    for t in all_tariffs:
        if t.get("SystemTariffType") in all_correct_types:
            continue
        text = (
            (t.get("Name") or "") + " " +
            (t.get("Description") or "")
        ).lower()
        for label, keywords in MISTYPE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                wrong_types.setdefault(label, []).append(t)
                break

    for label, mistyped in wrong_types.items():
        rows = [f"Plan | Current type | Should be"]
        for t in mistyped:
            current = TARIFF_TYPE_NAMES.get(t.get("SystemTariffType"), str(t.get("SystemTariffType", "?")))
            rows.append(f"{t.get('Name')} | {current} | {CORRECT_TYPES[label]}")
        section.add(CheckResult(
            name=f"{len(mistyped)} plan{'s' if len(mistyped) != 1 else ''} may be a {label} plan set to the wrong type",
            status="warn",
            detail="\n".join(rows),
            hint=f"Set the plan type to '{CORRECT_TYPES[label]}' so the AI matches it when prospects ask about {label.lower()} options.",
        ))

    # ── Work with visible, AI-enabled plans ───────────────────────────────────
    ai_plans = [t for t in all_tariffs if t.get("AvailableToAi")]
    total_ai  = len(ai_plans)

    if total_ai == 0:
        section.add(CheckResult(
            name="No plans published to AI",
            status="fail",
            detail="None of the membership plans have 'Available to AI' enabled. The AI cannot present any plans to prospects.",
            hint="Enable 'Available to AI' on each plan you want the AI to recommend.",
        ))
        return section

    section.add(CheckResult(
        name=f"{total_ai} plan{'s' if total_ai != 1 else ''} published to AI",
        status="pass",
        detail=_names(ai_plans),
    ))

    # ── 1. Type coverage per AI category ──────────────────────────────────────
    for category, type_ids in AI_CATEGORIES.items():
        matching = [t for t in ai_plans if t.get("SystemTariffType") in type_ids]
        visible  = [t for t in matching if t.get("Visible")]
        if visible:
            section.add(CheckResult(
                name=f"{category} plans available",
                status="pass",
                detail=f"{len(visible)} visible AI-enabled {category.lower()} plan{'s' if len(visible) != 1 else ''}: {_names(visible)}.",
            ))
        elif matching:
            section.add(CheckResult(
                name=f"{category} plans exist but are hidden",
                status="warn",
                detail=_names(matching),
                hint=f"These {category.lower()} plans have 'Available to AI' on but Visible = off. The AI will say options exist but cannot show details or a sign-up link.",
            ))
        else:
            section.add(CheckResult(
                name=f"No {category.lower()} plans",
                status="warn",
                detail=f"The AI has no plans to show when a prospect asks about {category.lower()} options.",
                hint=f"Create at least one {category.lower()} plan and enable 'Available to AI'.",
            ))

    # ── 2. Visibility ─────────────────────────────────────────────────────────
    hidden = [t for t in ai_plans if not t.get("Visible")]
    if hidden:
        section.add(CheckResult(
            name=f"{len(hidden)} of {total_ai} AI-enabled plans are hidden",
            status="warn",
            detail=_names(hidden),
            hint="Hidden plans: the AI acknowledges they exist but cannot show pricing or a sign-up link. Set Visible = on for full self-serve.",
        ))

    # ── 3. Descriptions ───────────────────────────────────────────────────────
    no_desc = [t for t in ai_plans if not (t.get("Description") or "").strip()]
    if not no_desc:
        section.add(CheckResult(
            name="Plan descriptions",
            status="pass",
            detail=f"All {total_ai} AI-enabled plans have descriptions.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_desc)} of {total_ai} AI-enabled plans missing descriptions",
            status="warn",
            detail=_names(no_desc),
            hint="Add descriptions — the AI presents them in the plan card alongside the sign-up link.",
            fields=[{"label": f"Description — {t.get('Name', 'Plan')}", "placeholder": "What's included, who it's for, contract terms…", "type": "textarea"} for t in no_desc],
        ))

    # ── 4. Show price to AI ───────────────────────────────────────────────────
    no_price = [t for t in ai_plans if not t.get("ShowPriceForAi")]
    if not no_price:
        section.add(CheckResult(
            name="Plan pricing visible to AI",
            status="pass",
            detail=f"All {total_ai} AI-enabled plans have 'Show price to AI' enabled.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_price)} of {total_ai} AI-enabled plans will not show price",
            status="warn",
            detail=_names(no_price),
            hint="Enable 'Show price to AI' so the AI can quote monthly prices and filter plans by budget.",
        ))

    # ── 5. AI price override (informational) ──────────────────────────────────
    with_ai_price = [t for t in ai_plans if t.get("PriceForAi")]
    if with_ai_price:
        rows = ["Plan | AI price | Regular price"]
        for t in with_ai_price:
            rows.append(f"{t.get('Name')} | {t.get('CurrencyCode', '')} {t.get('PriceForAi')} | {t.get('CurrencyCode', '')} {t.get('Price')}")
        section.add(CheckResult(
            name=f"{len(with_ai_price)} plan{'s' if len(with_ai_price) != 1 else ''} using AI price override",
            status="pass",
            detail="\n".join(rows),
        ))

    # ── 6. AI notes ───────────────────────────────────────────────────────────
    no_notes = [t for t in ai_plans if not (t.get("NotesForAi") or "").strip()]
    if not no_notes:
        section.add(CheckResult(
            name="Plan AI notes",
            status="pass",
            detail=f"All {total_ai} AI-enabled plans have AI notes set.",
        ))
    else:
        section.add(CheckResult(
            name=f"{len(no_notes)} of {total_ai} AI-enabled plans have no AI notes",
            status="warn",
            detail=_names(no_notes),
            hint="Add 'Notes for AI' to describe what's included, who the plan suits, or any key terms the AI should convey naturally.",
            fields=[{"label": f"AI notes — {t.get('Name', 'Plan')}", "placeholder": "What's included, who it suits, key terms and perks the AI should mention…", "type": "textarea"} for t in no_notes],
        ))

    return section
