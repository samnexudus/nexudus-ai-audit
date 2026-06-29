"""
Nexudus brand reference — single source of truth for all audit report styling.

Fonts:    Parkinsans (headings/labels) · Poppins (body/captions)
Hero:     Orange #FE4D00 — must appear in every design
Core:     Navy #212C6A · Blue #5757F4 · Green #28B95F · Pink #FF4F95
"""

import base64
import os

# ── Colour palette ─────────────────────────────────────────────────────────────

C = {
    # Hero
    "orange":           "#FE4D00",
    "orange_pale":      "#FFF2EC",
    "orange_light":     "#FFDACC",
    "orange_medium":    "#FF6E2F",
    "orange_dark":      "#723031",

    # Core — Navy
    "navy":             "#212C6A",

    # Core — Blue
    "blue":             "#5757F4",
    "blue_pale":        "#F1F4FF",
    "blue_light":       "#C5CCFF",
    "blue_medium":      "#8694FF",

    # Core — Green  (used for PASS)
    "green":            "#28B95F",
    "green_pale":       "#E0FFF0",
    "green_light":      "#9AE9B8",
    "green_medium":     "#70CF94",
    "green_dark":       "#00703E",

    # Core — Pink  (used for FAIL)
    "pink":             "#FF4F95",
    "pink_pale":        "#FFF0F5",
    "pink_light":       "#FFCCDF",
    "pink_medium":      "#FF84B5",
    "pink_dark":        "#6D1A3B",

    # Neutrals
    "white":            "#FDFDFD",
    "bg":               "#F8F8F8",
    "bg_warm":          "#F6F4EE",
    "border_warm":      "#D6D4CE",
    "border_neutral":   "#ECECEC",
    "border_cool":      "#CBCDD2",
    "grey_medium":      "#98989F",
    "text_body":        "#535060",
    "bg_blue_tint":     "#EEF6FF",
    "black":            "#151515",
}

# ── Status colour mapping ──────────────────────────────────────────────────────
#   pass  → Green
#   warn  → Orange
#   fail  → Pink (darkened for contrast)
#   skip  → Neutral grey

STATUS = {
    "pass": {
        "bg":     C["green_pale"],
        "border": C["green_light"],
        "text":   C["green_dark"],
        "badge":  C["green"],
    },
    "warn": {
        "bg":     C["orange_pale"],
        "border": C["orange_light"],
        "text":   C["orange_dark"],
        "badge":  C["orange"],
    },
    "fail": {
        "bg":     C["pink_pale"],
        "border": C["pink_light"],
        "text":   C["pink_dark"],
        "badge":  C["pink"],
    },
    "skip": {
        "bg":     C["bg"],
        "border": C["border_neutral"],
        "text":   C["grey_medium"],
        "badge":  C["grey_medium"],
    },
}

# ── Typography ─────────────────────────────────────────────────────────────────

FONT_DISPLAY = "Parkinsans, sans-serif"   # headings, labels, buttons
FONT_BODY    = "Poppins, sans-serif"      # body copy, captions, table text

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Parkinsans:wght@400;500;600"
    "&family=Poppins:wght@400;500;600"
    "&display=swap"
)

# ── Logo ───────────────────────────────────────────────────────────────────────

def logo_data_uri() -> str:
    """Embed Logo.png as a base64 data URI so the HTML is fully self-contained."""
    logo_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "Logo.png"))
    if not os.path.exists(logo_path):
        return ""
    with open(logo_path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"

# ── CSS ────────────────────────────────────────────────────────────────────────

def css() -> str:
    return f"""
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: {FONT_BODY};
  background: {C['bg']};
  color: {C['text_body']};
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}}

/* ── Page wrapper ── */
.page {{
  max-width: 960px;
  margin: 48px auto;
  background: {C['white']};
  border-radius: 24px;
  box-shadow: 0 4px 24px rgba(33,44,106,0.10);
  overflow: hidden;
}}

/* ── Header ── */
header {{
  background: {C['navy']};
  color: {C['white']};
  padding: 32px 48px 28px;
  display: flex;
  align-items: center;
  gap: 32px;
}}
header img {{ height: 32px; width: auto; flex-shrink: 0; }}
header .header-text .label {{
  font-family: {FONT_DISPLAY};
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: {C['blue_light']};
  margin-bottom: 6px;
}}
header h1 {{
  font-family: {FONT_DISPLAY};
  font-size: 22px;
  font-weight: 600;
  color: {C['white']};
  line-height: 1.29;
}}
header .meta {{
  margin-top: 6px;
  font-size: 13px;
  color: {C['blue_light']};
  font-family: {FONT_BODY};
}}

/* ── Orange accent bar ── */
.accent-bar {{
  height: 4px;
  background: {C['orange']};
}}

/* ── Score bar ── */
.score-bar {{
  background: {C['blue_pale']};
  border-bottom: 1px solid {C['blue_light']};
  padding: 20px 48px;
  display: flex;
  gap: 36px;
  align-items: center;
}}
.score-item {{
  font-family: {FONT_BODY};
  font-size: 13px;
  color: {C['text_body']};
}}
.score-item strong {{
  display: block;
  font-family: {FONT_DISPLAY};
  font-size: 26px;
  font-weight: 600;
  color: {C['navy']};
  line-height: 1.1;
}}
.score-item strong.orange {{ color: {C['orange']}; }}
.score-divider {{
  width: 1px;
  height: 36px;
  background: {C['blue_light']};
}}

/* ── Body ── */
.body {{ padding: 40px 48px 56px; }}

/* ── Section dropdowns ── */
.section {{
  margin-bottom: 12px;
  border: 1px solid {C['border_neutral']};
  border-radius: 12px;
  overflow: hidden;
}}
.section summary {{
  list-style: none;
}}
.section summary::-webkit-details-marker {{ display: none; }}

.section-title {{
  font-family: {FONT_DISPLAY};
  font-size: 15px;
  font-weight: 600;
  color: {C['navy']};
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  background: {C['white']};
  transition: background 0.15s;
}}
.section-title:hover {{ background: {C['bg']}; }}
.section-title .orange-dot {{
  width: 8px; height: 8px;
  border-radius: 50%;
  background: {C['orange']};
  flex-shrink: 0;
}}
.section-title-text {{ flex: 1; }}
.section-pills {{ display: flex; gap: 5px; }}
.section-chevron {{
  font-size: 18px;
  color: {C['grey_medium']};
  transition: transform 0.2s;
  line-height: 1;
}}
details.section[open] .section-chevron {{ transform: rotate(90deg); }}
.section-body {{
  padding: 4px 14px 14px;
  background: {C['bg']};
  border-top: 1px solid {C['border_neutral']};
}}

/* ── Summary table ── */
.summary-table {{
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 40px;
  font-size: 13px;
  font-family: {FONT_BODY};
}}
.summary-table th {{
  font-family: {FONT_DISPLAY};
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: {C['grey_medium']};
  border-bottom: 2px solid {C['border_neutral']};
  padding: 8px 12px;
  text-align: left;
}}
.summary-table td {{
  padding: 11px 12px;
  border-bottom: 1px solid {C['border_neutral']};
  vertical-align: middle;
  color: {C['text_body']};
}}
.summary-table tr:last-child td {{ border-bottom: none; }}
.summary-table .sname {{
  font-family: {FONT_DISPLAY};
  font-weight: 600;
  color: {C['navy']};
}}
.summary-table .pill-group {{ display: flex; gap: 6px; flex-wrap: wrap; }}

/* ── Check cards ── */
.check {{
  border-radius: 12px;
  border: 1px solid;
  padding: 14px 18px;
  margin-bottom: 10px;
}}
.check.pass {{ background:{C['green_pale']}; border-color:{C['green_light']}; }}
.check.warn {{ background:{C['orange_pale']}; border-color:{C['orange_light']}; }}
.check.fail {{ background:{C['pink_pale']}; border-color:{C['pink_light']}; }}
.check.skip {{ background:{C['bg']}; border-color:{C['border_neutral']}; }}

.check-header {{ display: flex; align-items: center; gap: 10px; }}

/* ── Badges ── */
.badge {{
  font-family: {FONT_DISPLAY};
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 6px;
  color: {C['white']};
  flex-shrink: 0;
}}
.badge.pass {{ background: {C['green']}; }}
.badge.warn {{ background: {C['orange']}; }}
.badge.fail {{ background: {C['pink']}; }}
.badge.skip {{ background: {C['grey_medium']}; }}

.check-name {{
  font-family: {FONT_DISPLAY};
  font-size: 14px;
  font-weight: 600;
}}
.check.pass .check-name {{ color: {C['green_dark']}; }}
.check.warn .check-name {{ color: {C['orange_dark']}; }}
.check.fail .check-name {{ color: {C['pink_dark']}; }}
.check.skip .check-name {{ color: {C['grey_medium']}; }}

.check-detail {{
  margin-top: 6px;
  font-size: 13px;
  font-family: {FONT_BODY};
  color: {C['text_body']};
}}
.check-hint {{
  margin-top: 6px;
  font-size: 13px;
  font-family: {FONT_BODY};
  font-weight: 500;
}}
.check.warn .check-hint {{ color: {C['orange']}; }}
.check.fail .check-hint {{ color: {C['pink_dark']}; }}

/* ── Mini pills (summary table counts) ── */
.pill {{
  display: inline-block;
  font-family: {FONT_DISPLAY};
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 20px;
  color: {C['white']};
}}
.pill.pass {{ background: {C['green']}; }}
.pill.warn {{ background: {C['orange']}; }}
.pill.fail {{ background: {C['pink']}; }}
.pill.skip {{ background: {C['grey_medium']}; }}

/* ── Field table (location details etc.) ── */
.field-table {{
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
  font-family: {FONT_BODY};
  font-size: 13px;
}}
.field-table td {{
  padding: 4px 8px 4px 0;
  vertical-align: top;
  color: {C['text_body']};
}}
.field-table .field-label {{
  font-family: {FONT_DISPLAY};
  font-weight: 600;
  color: {C['navy']};
  white-space: nowrap;
  width: 90px;
}}
.field-table .field-missing {{
  color: {C['grey_medium']};
  font-style: italic;
}}
.field-table.multi-col th {{
  font-family: {FONT_DISPLAY};
  font-weight: 600;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: {C['grey_medium']};
  padding: 4px 16px 6px 0;
  border-bottom: 1px solid {C['border_neutral']};
  text-align: left;
}}
.field-table.multi-col td {{
  padding: 5px 16px 5px 0;
  border-bottom: 1px solid {C['border_neutral']};
}}
.field-table.multi-col tr:last-child td {{ border-bottom: none; }}

/* ── Tabs ── */
.tab-nav {{
  display: flex;
  gap: 4px;
  border-bottom: 2px solid {C['border_neutral']};
  margin-bottom: 24px;
}}
.tab-btn {{
  font-family: {FONT_DISPLAY};
  font-size: 13px;
  font-weight: 600;
  color: {C['grey_medium']};
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  padding: 10px 16px 12px;
  margin-bottom: -2px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: color 0.15s;
}}
.tab-btn:hover {{ color: {C['navy']}; }}
.tab-btn.active {{
  color: {C['navy']};
  border-bottom-color: {C['orange']};
}}
.tab-pills {{ display: flex; gap: 4px; }}
.tab-panel {{ display: none; }}
.tab-panel.active {{ display: block; }}
.tab-description {{
  font-family: {FONT_BODY};
  font-size: 14px;
  color: {C['text_body']};
  line-height: 1.6;
  margin-bottom: 24px;
}}
.tab-empty {{
  font-family: {FONT_BODY};
  font-size: 14px;
  color: {C['grey_medium']};
  padding: 40px 0;
  text-align: center;
}}

/* ── Action Plan ── */
details.ap-section {{
  margin-bottom: 12px;
  border: 1px solid {C['border_neutral']};
  border-radius: 12px;
  overflow: hidden;
}}
details.ap-section summary {{ list-style: none; }}
details.ap-section summary::-webkit-details-marker {{ display: none; }}

.ap-section-title {{
  font-family: {FONT_DISPLAY};
  font-size: 15px;
  font-weight: 600;
  color: {C['navy']};
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  background: {C['white']};
  transition: background 0.15s;
}}
.ap-section-title:hover {{ background: {C['bg']}; }}
.ap-section-title .orange-dot {{
  width: 8px; height: 8px;
  border-radius: 50%;
  background: {C['orange']};
  flex-shrink: 0;
}}
.ap-section-title-text {{ flex: 1; }}
.ap-section-count {{
  font-family: {FONT_BODY};
  font-size: 12px;
  font-weight: 500;
  color: {C['grey_medium']};
}}
.ap-section-chevron {{
  font-size: 18px;
  color: {C['grey_medium']};
  transition: transform 0.2s;
  line-height: 1;
}}
details.ap-section[open] .ap-section-chevron {{ transform: rotate(90deg); }}
.ap-section-body {{
  padding: 8px 14px 14px;
  background: {C['bg']};
  border-top: 1px solid {C['border_neutral']};
}}

.ap-check {{
  background: {C['white']};
  border: 1px solid {C['border_neutral']};
  border-radius: 10px;
  padding: 14px 16px;
  margin-top: 10px;
}}
.ap-check-header {{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}}
.ap-check-name {{
  font-family: {FONT_DISPLAY};
  font-size: 13px;
  font-weight: 600;
  color: {C['navy']};
}}
.ap-hint {{
  font-family: {FONT_BODY};
  font-size: 12px;
  color: {C['grey_medium']};
  margin-bottom: 10px;
}}
.ap-field-row {{
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}}
.ap-field-row label {{
  font-family: {FONT_DISPLAY};
  font-size: 12px;
  font-weight: 600;
  color: {C['navy']};
  min-width: 180px;
  padding-top: 8px;
  flex-shrink: 0;
}}
.ap-input, .ap-input-text {{
  flex: 1;
  font-family: {FONT_BODY};
  font-size: 13px;
  color: {C['text_body']};
  background: {C['bg']};
  border: 1px solid {C['border_cool']};
  border-radius: 6px;
  padding: 7px 10px;
  outline: none;
  transition: border-color 0.15s;
  width: 100%;
}}
.ap-input {{ resize: vertical; }}
.ap-input:focus, .ap-input-text:focus {{
  border-color: {C['blue']};
  background: {C['white']};
}}
.ap-task-note {{
  font-family: {FONT_BODY};
  font-size: 13px;
  color: {C['grey_medium']};
  font-style: italic;
  padding: 4px 0;
}}
.ap-actions {{
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 16px 0 4px;
  margin-top: 16px;
  border-top: 1px solid {C['border_neutral']};
}}
.ap-btn {{
  font-family: {FONT_DISPLAY};
  font-size: 13px;
  font-weight: 600;
  padding: 9px 20px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: opacity 0.15s;
}}
.ap-btn:hover {{ opacity: 0.85; }}
.ap-btn-primary {{ background: {C['orange']}; color: {C['white']}; }}
.ap-btn-secondary {{ background: {C['bg']}; color: {C['navy']}; border: 1px solid {C['border_cool']}; }}
.ap-copy-confirm {{
  font-family: {FONT_BODY};
  font-size: 12px;
  color: {C['green']};
  opacity: 0;
  transition: opacity 0.3s;
}}
.ap-copy-confirm.show {{ opacity: 1; }}

/* ── Footer ── */
footer {{
  border-top: 1px solid {C['border_neutral']};
  padding: 18px 48px;
  font-family: {FONT_BODY};
  font-size: 12px;
  color: {C['grey_medium']};
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
footer .watermark {{
  font-family: {FONT_DISPLAY};
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: {C['border_cool']};
}}

/* ── Print ── */
@media print {{
  body {{ background: {C['white']}; }}
  .page {{ margin: 0; border-radius: 0; box-shadow: none; max-width: 100%; }}
}}
"""
