"""
HTML report generator for the AI Agent Audit.
"""
from __future__ import annotations

import html as htmllib
import os
from datetime import date as Date
from typing import Optional
from brand import css, logo_data_uri, GOOGLE_FONTS_URL, C, FONT_DISPLAY, FONT_BODY


def _esc(s: str) -> str:
    return htmllib.escape(str(s or ""))


def _badge(status: str) -> str:
    return f'<span class="badge {status}">{status.upper()}</span>'


def _pill(status: str, n: int) -> str:
    if n == 0:
        return ""
    return f'<span class="pill {status}">{n}</span>'


def _detail_html(text: str) -> str:
    """Render detail text.
    - Single line → plain div
    - Lines with ': ' → 2-column label/value field table
    - Lines with ' | ' → multi-column table (first line treated as header if all cols are non-empty)
    """
    if not text:
        return ""
    lines = text.split("\n")
    if len(lines) == 1:
        return f'<div class="check-detail">{_esc(text)}</div>'

    # Detect pipe-delimited multi-column table
    if any(" | " in line for line in lines):
        rows = ""
        for i, line in enumerate(lines):
            cols = [c.strip() for c in line.split(" | ")]
            if i == 0:
                cells = "".join(f'<th>{_esc(c)}</th>' for c in cols)
                rows += f'<tr>{cells}</tr>'
            else:
                cells = "".join(f'<td>{_esc(c)}</td>' for c in cols)
                rows += f'<tr>{cells}</tr>'
        return f'<table class="field-table multi-col">{rows}</table>'

    # 2-column label/value table
    rows = ""
    for line in lines:
        if ": " in line:
            label, _, value = line.partition(": ")
            missing = value == "—"
            val_class = ' class="field-missing"' if missing else ""
            rows += f'<tr><td class="field-label">{_esc(label)}</td><td{val_class}>{_esc(value)}</td></tr>'
        else:
            rows += f'<tr><td colspan="2">{_esc(line)}</td></tr>'
    return f'<table class="field-table">{rows}</table>'


def _check_card(result) -> str:
    detail_html = _detail_html(result.detail)
    hint_html   = f'<div class="check-hint">→ {_esc(result.hint)}</div>' if result.hint and result.status in ("warn", "fail") else ""
    return f"""
    <div class="check {result.status}">
      <div class="check-header">
        {_badge(result.status)}
        <span class="check-name">{_esc(result.name)}</span>
      </div>
      {detail_html}
      {hint_html}
    </div>"""


def _section_html(section) -> str:
    sc = section.score
    open_attr = ""
    cards = "".join(_check_card(r) for r in section.results)
    pills = (
        _pill("pass", sc["pass"]) +
        _pill("warn", sc["warn"]) +
        _pill("fail", sc["fail"]) +
        _pill("skip", sc["skip"])
    )
    return f"""
  <details class="section"{open_attr}>
    <summary class="section-title">
      <span class="orange-dot"></span>
      <span class="section-title-text">{_esc(section.title)}</span>
      <span class="section-pills">{pills}</span>
      <span class="section-chevron">›</span>
    </summary>
    <div class="section-body">
      {cards}
    </div>
  </details>"""


def _tab_score(sections: list) -> dict:
    totals = {"pass": 0, "warn": 0, "fail": 0, "skip": 0}
    for s in sections:
        for k, v in s.score.items():
            totals[k] += v
    return totals


def _tabs_html(tabs: list) -> str:
    nav_items = ""
    panels = ""
    for i, (label, sections) in enumerate(tabs):
        tab_id = f"tab-{i}"
        active_cls = " active" if i == 0 else ""
        sc = _tab_score(sections)
        pills = (
            _pill("pass", sc["pass"]) +
            _pill("warn", sc["warn"]) +
            _pill("fail", sc["fail"])
        )
        nav_items += f'<button class="tab-btn{active_cls}" onclick="switchTab({i})" id="btn-{tab_id}">{_esc(label)}<span class="tab-pills">{pills}</span></button>'

        descriptions = {
            "Conversational Agents": "The Nexudus AI assistant answers questions, helps members manage their bookings, and guides prospects toward purchasing a day pass, signing up for a membership, or scheduling a private office tour.",
            "Channels": "The AI assistant supports four channels: Chat, Email, WhatsApp, and Voice. All four share the same capabilities, the same data, and the same visibility rules. The differences are in how conversations are started, how sessions are managed, and how responses are formatted.",
        }
        desc = descriptions.get(label, "")
        desc_html = f'<p class="tab-description">{_esc(desc)}</p>' if desc else ""

        if sections:
            content = desc_html + "".join(_section_html(s) for s in sections)
        else:
            content = desc_html + '<div class="tab-empty">No checks configured for this tab yet.</div>'

        panels += f'<div class="tab-panel{active_cls}" id="{tab_id}">{content}</div>'

    return f"""
  <div class="tab-nav">{nav_items}</div>
  <div class="tab-body">{panels}</div>"""


def generate_html(tabs: list, whoami: dict, run_date: Optional[Date] = None) -> str:
    run_date = run_date or Date.today()
    business = _esc(whoami.get("defaultBusinessName", "Unknown Business"))
    logo_src = logo_data_uri()
    logo_img = f'<img src="{logo_src}" alt="Nexudus">' if logo_src else ""

    all_sections = [s for _, group in tabs for s in group]
    total_pass = total_warn = total_fail = 0
    for s in all_sections:
        sc = s.score
        total_pass += sc["pass"]
        total_warn += sc["warn"]
        total_fail += sc["fail"]

    total = total_pass + total_warn + total_fail
    score_pct = round((total_pass / total) * 100) if total else 0

    warn_colour = C["orange"] if total_warn > 0 else C["green"]
    fail_colour = C["pink"]   if total_fail > 0 else C["grey_medium"]

    tabs_html = _tabs_html(tabs)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Agent Audit — {business}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{GOOGLE_FONTS_URL}" rel="stylesheet">
  <style>{css()}</style>
</head>
<body>
  <div class="page">

    <header>
      {logo_img}
      <div class="header-text">
        <div class="label">AI Agent Audit</div>
        <h1>{business}</h1>
        <div class="meta">Generated {run_date.strftime("%-d %B %Y")}</div>
      </div>
    </header>

    <div class="accent-bar"></div>

    <div class="score-bar">
      <div class="score-item">
        <strong class="orange">{score_pct}%</strong>
        Overall score
      </div>
      <div class="score-divider"></div>
      <div class="score-item">
        <strong style="color:{C['green']}">{total_pass}</strong>
        Passed
      </div>
      <div class="score-divider"></div>
      <div class="score-item">
        <strong style="color:{warn_colour}">{total_warn}</strong>
        Warnings
      </div>
      <div class="score-divider"></div>
      <div class="score-item">
        <strong style="color:{fail_colour}">{total_fail}</strong>
        Failed
      </div>
      <div class="score-divider"></div>
      <div class="score-item">
        <strong style="color:{C['navy']}">{total}</strong>
        Total checks
      </div>
    </div>

    <div class="body">
      {tabs_html}
    </div>

    <footer>
      <span>Nexudus AI Agent Audit · {run_date.strftime("%B %Y")}</span>
      <span class="watermark">Powered by Nexudus</span>
    </footer>

  </div>
  <script>
    function switchTab(i) {{
      document.querySelectorAll('.tab-btn').forEach((b, idx) => b.classList.toggle('active', idx === i));
      document.querySelectorAll('.tab-panel').forEach((p, idx) => p.classList.toggle('active', idx === i));
    }}
  </script>
</body>
</html>"""


def save_report(html: str, business_name: str, run_date: Optional[Date] = None, output_dir: str = ".") -> str:
    run_date = run_date or Date.today()
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "" for c in business_name).strip().replace(" ", "-")
    filename = f"{run_date.isoformat()}.html"
    path = os.path.join(output_dir, "Reports", safe_name, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
