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


NEXUDUS_TEAM_EMAIL = "sam@nexudus.com"


_ACTION_PLAN_EXCLUDED_TABS = {"Channels"}


def _action_plan_html(tabs: list) -> str:
    included = [(label, group) for label, group in tabs if label not in _ACTION_PLAN_EXCLUDED_TABS]
    all_sections = [s for _, group in included for s in group]
    gaps = [(s, r) for s in all_sections for r in s.results if r.status in ("warn", "fail")]

    if not gaps:
        return '<p class="tab-description">No gaps found — this account is fully set up for AI Agent.</p>'

    # Group by section
    by_section: dict = {}
    for s, r in gaps:
        by_section.setdefault(s.title, []).append(r)

    input_id = 0
    sections_html = ""
    for title, results in by_section.items():
        n_gaps = len(results)
        checks_html = ""
        for r in results:
            badge = f'<span class="badge {r.status}">{r.status.upper()}</span>'
            hint_html = f'<div class="ap-hint">→ {_esc(r.hint)}</div>' if r.hint else ""

            if r.fields:
                inputs_html = ""
                for f_def in r.fields:
                    input_id += 1
                    fid = f"ap-{input_id}"
                    label = _esc(f_def.get("label", ""))
                    placeholder = _esc(f_def.get("placeholder", ""))
                    f_type = f_def.get("type", "text")
                    if f_type == "textarea":
                        inp = f'<textarea id="{fid}" class="ap-input" data-section="{_esc(title)}" data-check="{_esc(r.name)}" data-field="{label}" placeholder="{placeholder}" rows="3"></textarea>'
                    else:
                        inp = f'<input id="{fid}" type="text" class="ap-input ap-input-text" data-section="{_esc(title)}" data-check="{_esc(r.name)}" data-field="{label}" placeholder="{placeholder}">'
                    inputs_html += f'<div class="ap-field-row"><label for="{fid}">{label}</label>{inp}</div>'
            else:
                # Action-only check — no data to collect, just show as a task
                inputs_html = f'<p class="ap-task-note">Action required: {_esc(r.hint or "See the audit tab for details.")}</p>'

            checks_html += f"""
        <div class="ap-check">
          <div class="ap-check-header">{badge}<span class="ap-check-name">{_esc(r.name)}</span></div>
          {hint_html}
          {inputs_html}
        </div>"""

        n_label = f"{n_gaps} item{'s' if n_gaps != 1 else ''}"
        sections_html += f"""
      <details class="ap-section" open>
        <summary class="ap-section-title">
          <span class="orange-dot"></span>
          <span class="ap-section-title-text">{_esc(title)}</span>
          <span class="ap-section-count">{n_label}</span>
          <span class="ap-section-chevron">›</span>
        </summary>
        <div class="ap-section-body">{checks_html}</div>
      </details>"""

    return f"""
    <p class="tab-description">Fill in the details below for each gap found in the audit. When you're done, send them directly to the Nexudus team or download a copy for your records.</p>
    <form id="action-plan-form" onsubmit="return false;">
      {sections_html}
      <div class="ap-actions">
        <button class="ap-btn ap-btn-primary" onclick="sendToNexudus()">Send to Nexudus</button>
        <button class="ap-btn ap-btn-secondary" onclick="downloadResponses()">Download</button>
        <button class="ap-btn ap-btn-secondary" onclick="copyResponses()">Copy to clipboard</button>
        <span class="ap-copy-confirm" id="copy-confirm">Copied!</span>
      </div>
    </form>"""


def _tabs_html(tabs: list) -> str:
    all_tabs = list(tabs) + [("Action Plan", None)]  # None signals action plan tab
    nav_items = ""
    panels = ""

    for i, item in enumerate(all_tabs):
        label, sections = item
        tab_id = f"tab-{i}"
        active_cls = " active" if i == 0 else ""

        if sections is None:
            # Action plan tab — count gaps as its "score"
            all_sections = [s for _, group in tabs for s in group]
            n_fail = sum(r.status == "fail" for s in all_sections for r in s.results)
            n_warn = sum(r.status == "warn" for s in all_sections for r in s.results)
            pills = _pill("fail", n_fail) + _pill("warn", n_warn)
            content = _action_plan_html(tabs)
        else:
            sc = _tab_score(sections)
            pills = (
                _pill("pass", sc["pass"]) +
                _pill("warn", sc["warn"]) +
                _pill("fail", sc["fail"])
            )
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

        nav_items += f'<button class="tab-btn{active_cls}" onclick="switchTab({i})" id="btn-{tab_id}">{_esc(label)}<span class="tab-pills">{pills}</span></button>'
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

    function collectResponses() {{
      const nl = '\\n';
      const inputs = document.querySelectorAll('.ap-input');
      let text = 'AI Agent Audit — Action Plan' + nl;
      text += '=============================' + nl + nl;
      let currentSection = '';
      let currentCheck = '';
      inputs.forEach(el => {{
        const section = el.dataset.section || '';
        const check = el.dataset.check || '';
        const fieldLabel = el.dataset.field || check;
        const value = el.value.trim();
        if (!value) return;
        if (section !== currentSection) {{
          text += (currentSection ? nl : '') + section + nl + '-'.repeat(section.length) + nl;
          currentSection = section;
          currentCheck = '';
        }}
        if (check !== currentCheck) {{
          text += nl + check + nl;
          currentCheck = check;
        }}
        text += '  ' + fieldLabel + ': ' + value + nl;
      }});
      return text;
    }}

    function sendToNexudus() {{
      const text = collectResponses();
      const subject = encodeURIComponent(document.querySelector('h1') ? 'AI Agent Audit — ' + document.querySelector('h1').textContent : 'AI Agent Audit');
      const body = encodeURIComponent(text);
      window.location.href = 'mailto:{NEXUDUS_TEAM_EMAIL}?subject=' + subject + '&body=' + body;
    }}

    function downloadResponses() {{
      const text = collectResponses();
      const blob = new Blob([text], {{ type: 'text/plain' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'ai-audit-responses.txt';
      a.click();
    }}

    function copyResponses() {{
      const text = collectResponses();
      navigator.clipboard.writeText(text).then(() => {{
        const el = document.getElementById('copy-confirm');
        el.classList.add('show');
        setTimeout(() => el.classList.remove('show'), 2000);
      }});
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
