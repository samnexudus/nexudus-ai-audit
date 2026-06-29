"""
Checks — AI Conversation Assistant
Section 1: FAQ Articles (Capability: Answering Questions)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date, timedelta
from models import Section, CheckResult, nexudus

# ── Constants ──────────────────────────────────────────────────────────────────

MIN_ARTICLES_PASS  = 5
MIN_FULLTEXT_CHARS = 100
STALE_DAYS         = 365
MAX_MISSING_TOPICS_WARN = 3   # warn if ≤ this many missing; fail if more

EXPECTED_TOPICS = [
    ("Opening hours",          ["opening hour", "open", "close", "when are you", "hours of operation"]),
    ("Parking",                ["parking", "car park", "car-park"]),
    ("Wi-Fi / internet",       ["wifi", "wi-fi", "internet", "password", "broadband", "network"]),
    ("Pet policy",             ["pet", "dog", "cat", "animal"]),
    ("Printing",               ["print", "printer", "printing"]),
    ("Guest / visitor policy", ["guest", "visitor"]),
    ("Out-of-hours access",    ["24/7", "out of hours", "out-of-hours", "weekend", "after hours", "24 hour"]),
    ("Mail & deliveries",      ["mail", "parcel", "delivery", "postal", "package", "post"]),
    ("Kitchen & refreshments", ["kitchen", "coffee", "food", "drink", "fridge", "refreshment"]),
    ("Noise policy",           ["noise", "quiet", "phone call", "quiet zone"]),
    ("Cancellation policy",    ["cancel", "cancellation", "notice period"]),
    ("Getting here",           ["direction", "tube", "bus", "train", "transport", "nearest", "how to get", "getting here"]),
    ("Accessibility",          ["wheelchair", "disabled", "accessible", "lift", "elevator", "accessibility"]),
    ("Security & access",      ["key fob", "door access", "access control", "entry", "security", "out of hours"]),
]


# ── Helper ─────────────────────────────────────────────────────────────────────

def _article_text(a: dict) -> str:
    return " ".join(filter(None, [
        a.get("Title", ""),
        a.get("SummaryText", ""),
        a.get("FullText", ""),
        a.get("GroupName", ""),
    ])).lower()


# ── Checks ─────────────────────────────────────────────────────────────────────

def check_conversation_assistant(business_id: int) -> Section:
    section = Section("AI Conversation Assistant — FAQ Articles")

    # ── Fetch all published articles ───────────────────────────────────────────
    envelope = nexudus(["faqarticles", "list",
                        "--business-id", str(business_id),
                        "--active", "true",
                        "--page-size", "100"])

    if not envelope.get("ok"):
        section.add(CheckResult(
            name="FAQ articles — data fetch",
            status="fail",
            detail=envelope.get("summary", "Failed to fetch FAQ articles."),
            hint="Check that you are authenticated and have access to this business.",
        ))
        return section

    articles = envelope.get("data") or []
    total    = len(articles)

    # ── 1.1  Published articles exist ─────────────────────────────────────────
    if total == 0:
        section.add(CheckResult(
            name="No published FAQ articles",
            status="fail",
            detail="The AI has nothing to search — it cannot answer any knowledge base questions.",
            hint="Create and publish FAQ articles in Nexudus covering common member and visitor questions.",
        ))
        return section
    elif total < MIN_ARTICLES_PASS:
        section.add(CheckResult(
            name=f"Only {total} published FAQ article{'s' if total != 1 else ''}",
            status="warn",
            detail="Very thin coverage — common questions are almost certainly not all addressed.",
            hint=f"Aim for at least {MIN_ARTICLES_PASS} articles to cover common questions.",
        ))
    else:
        section.add(CheckResult(
            name="Published FAQ articles",
            status="pass",
            detail=f"{total} published articles found.",
        ))

    # ── 1.2  Articles have body content (FullText) ────────────────────────────
    no_fulltext   = [a for a in articles if not (a.get("FullText") or "").strip()]
    thin_fulltext = [a for a in articles if len((a.get("FullText") or "").strip()) < MIN_FULLTEXT_CHARS
                     and (a.get("FullText") or "").strip()]

    missing_pct = len(no_fulltext) / total
    if missing_pct > 0.20:
        section.add(CheckResult(
            name=f"{len(no_fulltext)} of {total} articles have no body content",
            status="fail",
            detail="Title-only articles give the AI nothing to match against semantically.",
            hint="Add detailed body content (FullText) to each article.",
            fields=[{"label": f"Content — {a.get('Title', 'Untitled')}", "placeholder": "Full article content (at least a paragraph)…", "type": "textarea"} for a in no_fulltext],
        ))
    elif thin_fulltext:
        names = ", ".join(a.get("Title", "Untitled") for a in thin_fulltext[:3])
        more  = f" and {len(thin_fulltext)-3} more" if len(thin_fulltext) > 3 else ""
        section.add(CheckResult(
            name=f"{len(thin_fulltext)} article{'s' if len(thin_fulltext)!=1 else ''} with thin body content",
            status="warn",
            detail=f"Under {MIN_FULLTEXT_CHARS} characters: {names}{more}.",
            hint="Expand these articles — short content reduces the AI's ability to find relevant answers.",
            fields=[{"label": f"Expanded content — {a.get('Title', 'Untitled')}", "placeholder": "Provide a fuller version of this article…", "type": "textarea"} for a in thin_fulltext],
        ))
    elif no_fulltext:
        names = ", ".join(a.get("Title", "Untitled") for a in no_fulltext[:3])
        section.add(CheckResult(
            name=f"{len(no_fulltext)} article{'s' if len(no_fulltext)!=1 else ''} missing body content",
            status="warn",
            detail=f"{names}.",
            hint="Add body content to these articles.",
            fields=[{"label": f"Content — {a.get('Title', 'Untitled')}", "placeholder": "Full article content…", "type": "textarea"} for a in no_fulltext],
        ))
    else:
        section.add(CheckResult(
            name="FAQ article body content",
            status="pass",
            detail=f"All {total} articles have body content.",
        ))

    # ── 1.3  Articles have summaries (SummaryText) ───────────────────────────
    no_summary = [a for a in articles if not (a.get("SummaryText") or "").strip()]
    missing_pct = len(no_summary) / total

    if missing_pct > 0.30:
        section.add(CheckResult(
            name=f"{len(no_summary)} of {total} articles missing summaries",
            status="warn",
            detail="The AI surfaces the summary first in its reply.",
            hint="Add a concise SummaryText to each article.",
            fields=[{"label": f"Summary — {a.get('Title', 'Untitled')}", "placeholder": "1–2 sentence summary of this article", "type": "textarea"} for a in no_summary],
        ))
    elif no_summary:
        names = ", ".join(a.get("Title", "Untitled") for a in no_summary[:3])
        section.add(CheckResult(
            name=f"{len(no_summary)} article{'s' if len(no_summary)!=1 else ''} missing summaries",
            status="warn",
            detail=f"{names}.",
            hint="Add a SummaryText to these articles.",
            fields=[{"label": f"Summary — {a.get('Title', 'Untitled')}", "placeholder": "1–2 sentence summary of this article", "type": "textarea"} for a in no_summary],
        ))
    else:
        section.add(CheckResult(
            name="FAQ article summaries",
            status="pass",
            detail=f"All {total} articles have summaries.",
        ))

    # ── 1.4  Articles are organised into groups (GroupName) ──────────────────
    ungrouped = [a for a in articles if not (a.get("GroupName") or "").strip()]
    groups    = {}
    for a in articles:
        g = (a.get("GroupName") or "").strip()
        if g:
            groups[g] = groups.get(g, 0) + 1

    if len(ungrouped) == total:
        section.add(CheckResult(
            name="FAQ articles are organised into groups",
            status="warn",
            detail="No articles have a GroupName set — all articles are ungrouped.",
            hint="Add GroupName values to organise articles by topic (e.g. 'Access & Facilities', 'Pricing', 'Policies').",
        ))
    else:
        group_summary = ", ".join(f"{g} ({n})" for g, n in sorted(groups.items()))
        detail = f"{len(groups)} group{'s' if len(groups)!=1 else ''}: {group_summary}."
        if ungrouped:
            detail += f" {len(ungrouped)} article{'s' if len(ungrouped)!=1 else ''} still ungrouped."
        section.add(CheckResult(
            name="FAQ articles are organised into groups",
            status="pass" if not ungrouped else "warn",
            detail=detail,
            hint="Move ungrouped articles into a named group." if ungrouped else "",
        ))

    # ── 1.5  Content freshness ────────────────────────────────────────────────
    cutoff     = date.today() - timedelta(days=STALE_DAYS)
    stale      = []
    no_date    = []
    for a in articles:
        updated = a.get("UpdatedOn") or a.get("CreatedOn")
        if not updated:
            no_date.append(a)
            continue
        try:
            d = date.fromisoformat(updated[:10])
            if d < cutoff:
                stale.append(a)
        except ValueError:
            no_date.append(a)

    if stale:
        names = ", ".join(a.get("Title", "Untitled") for a in stale[:3])
        more  = f" and {len(stale)-3} more" if len(stale) > 3 else ""
        section.add(CheckResult(
            name="FAQ content is up to date",
            status="warn",
            detail=(f"{len(stale)} article{'s' if len(stale)!=1 else ''} "
                    f"not updated in over 12 months: {names}{more}."),
            hint="Review and refresh these articles to ensure the AI gives accurate answers.",
            fields=[{"label": f"Updated content — {a.get('Title', 'Untitled')}", "placeholder": "Paste the refreshed article content here…", "type": "textarea"} for a in stale],
        ))
    else:
        section.add(CheckResult(
            name="FAQ content is up to date",
            status="pass",
            detail=f"All articles updated within the last 12 months.",
        ))

    # ── 1.6  FAQ access control setting ──────────────────────────────────────
    settings_env = nexudus(["businesssettings", "list",
                            "--business-id", str(business_id),
                            "--name", "Access.FAQs"])

    faq_access = None
    if settings_env.get("ok"):
        records = settings_env.get("data") or []
        if records:
            faq_access = records[0].get("Value")

    ACCESS_LABELS = {
        "1": "Everyone (any visitor, logged in or not)",
        "2": "Logged-in users only",
        "3": "Members only — contacts and anonymous visitors are turned away",
        "4": "Contacts only — members and anonymous visitors are turned away",
    }
    if faq_access is None:
        section.add(CheckResult(
            name="FAQ access control configured",
            status="warn",
            detail="Could not read the Access.FAQs business setting.",
            hint="Check the Access > FAQs setting in your portal configuration.",
        ))
    else:
        val   = str(faq_access)
        label = ACCESS_LABELS.get(val, f"Unknown ({faq_access})")
        if val in ("3", "4"):
            section.add(CheckResult(
                name="FAQ access control configured",
                status="warn",
                detail=f"FAQ visibility is set to: {label}.",
                hint="Prospects and anonymous visitors cannot get FAQ answers from the AI. Consider setting to 'Everyone' if you want the AI to help convert leads.",
            ))
        else:
            section.add(CheckResult(
                name="FAQ access control configured",
                status="pass",
                detail=f"FAQ visibility is set to: {label}.",
            ))

    # ── 1.7  Expected topic coverage ─────────────────────────────────────────
    article_texts = [_article_text(a) for a in articles]
    combined      = " ".join(article_texts)

    covered = []
    missing = []
    for topic, keywords in EXPECTED_TOPICS:
        if any(kw in combined for kw in keywords):
            covered.append(topic)
        else:
            missing.append(topic)

    if not missing:
        section.add(CheckResult(
            name="FAQ topic coverage",
            status="pass",
            detail=f"All {len(EXPECTED_TOPICS)} expected topics are covered.",
        ))
    elif len(missing) <= MAX_MISSING_TOPICS_WARN:
        section.add(CheckResult(
            name=f"{len(missing)} expected topic{'s' if len(missing)!=1 else ''} not covered",
            status="warn",
            detail=f"{', '.join(missing)}.",
            hint="Add articles covering these topics to improve AI answer coverage.",
            fields=[{"label": f"Article content — {t}", "placeholder": f"Content for a new FAQ article covering '{t}'…", "type": "textarea"} for t in missing],
        ))
    else:
        section.add(CheckResult(
            name=f"{len(missing)} of {len(EXPECTED_TOPICS)} expected topics not covered",
            status="fail",
            detail=f"{', '.join(missing)}.",
            hint="Create articles for these topics. The AI can only answer questions it has content for.",
            fields=[{"label": f"Article content — {t}", "placeholder": f"Content for a new FAQ article covering '{t}'…", "type": "textarea"} for t in missing],
        ))

    return section
