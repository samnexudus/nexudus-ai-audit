"""
Checks — Channels
Four channels: Chat (always on), WhatsApp, Email, Voice.
All share the same AI capabilities and data — differences are in setup and session handling.

WhatsApp settings (businesssettings --name "AiWhatsApp"):
  AiWhatsApp.Enabled                  bool — master toggle
  AiWhatsApp.Twilio.AccountId         Twilio Account SID
  AiWhatsApp.Twilio.AuthToken         Twilio Auth Token (redacted in API)
  AiWhatsApp.PhoneNumber              WhatsApp-enabled phone number
  AiWhatsApp.Outbound.TemplatContentSid  Twilio content template SID for outbound messages
  AiWhatsApp.Outbound.OptInKeyword    Keyword users send to opt in to outbound messages
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import Section, CheckResult, nexudus


def check_chat_channel(_business_id: int) -> Section:
    section = Section("Chat")
    section.add(CheckResult(
        name="Chat channel enabled",
        status="pass",
        detail="Chat is available by default on your Nexudus portal — no additional configuration required.",
    ))
    return section


def check_whatsapp_channel(business_id: int) -> Section:
    section = Section("WhatsApp")

    env = nexudus(["businesssettings", "list",
                   "--business-id", str(business_id),
                   "--name", "AiWhatsApp",
                   "--page-size", "20"])

    if not env.get("ok"):
        section.add(CheckResult(
            name="WhatsApp settings — data fetch failed",
            status="fail",
            detail=env.get("summary", "Could not fetch WhatsApp settings."),
        ))
        return section

    records = env.get("data") or []
    by_name = {r["Name"]: (r.get("Value") or "").strip() for r in records}

    enabled = by_name.get("AiWhatsApp.Enabled", "").lower() == "true"

    # ── 1. Master toggle ───────────────────────────────────────────────────────
    if not enabled:
        section.add(CheckResult(
            name="WhatsApp channel not enabled",
            status="warn",
            detail="The AI is not available on WhatsApp for this location.",
            hint="Enable WhatsApp under Settings › AI Assistants › Channels › WhatsApp and complete the Twilio configuration.",
        ))
        return section

    section.add(CheckResult(
        name="WhatsApp channel enabled",
        status="pass",
        detail="The AI is active on WhatsApp for this location.",
    ))

    # ── 2. Twilio Account SID ──────────────────────────────────────────────────
    account_id = by_name.get("AiWhatsApp.Twilio.AccountId", "")
    if not account_id:
        section.add(CheckResult(
            name="Twilio Account SID not set",
            status="fail",
            detail="A Twilio Account SID is required to send and receive WhatsApp messages.",
            hint="Add your Twilio Account SID under Settings › AI Assistants › Channels › WhatsApp.",
        ))
    else:
        section.add(CheckResult(
            name="Twilio Account SID set",
            status="pass",
            detail=f"Account SID: {account_id}",
        ))

    # ── 3. Twilio Auth Token ───────────────────────────────────────────────────
    auth_token = by_name.get("AiWhatsApp.Twilio.AuthToken", "")
    if not auth_token:
        section.add(CheckResult(
            name="Twilio Auth Token not set",
            status="fail",
            detail="A Twilio Auth Token is required to authenticate API requests.",
            hint="Add your Twilio Auth Token under Settings › AI Assistants › Channels › WhatsApp.",
        ))
    else:
        section.add(CheckResult(
            name="Twilio Auth Token set",
            status="pass",
        ))

    # ── 4. WhatsApp phone number ───────────────────────────────────────────────
    phone = by_name.get("AiWhatsApp.PhoneNumber", "")
    if not phone:
        section.add(CheckResult(
            name="WhatsApp phone number not set",
            status="fail",
            detail="A WhatsApp-enabled phone number is required for the AI to send and receive messages.",
            hint="Add your WhatsApp phone number under Settings › AI Assistants › Channels › WhatsApp.",
        ))
    else:
        section.add(CheckResult(
            name="WhatsApp phone number set",
            status="pass",
            detail=phone,
        ))

    # ── 5. Outbound message template ──────────────────────────────────────────
    template_sid = by_name.get("AiWhatsApp.Outbound.TemplatContentSid", "")
    if not template_sid:
        section.add(CheckResult(
            name="Outbound message template not configured",
            status="warn",
            detail="Without a Twilio content template SID, the AI cannot send outbound WhatsApp messages to initiate conversations.",
            hint="Create a WhatsApp message template in Twilio and add the Content SID under Settings › AI Assistants › Channels › WhatsApp.",
        ))
    else:
        section.add(CheckResult(
            name="Outbound message template set",
            status="pass",
            detail=f"Template SID: {template_sid}",
        ))

    # ── 6. Opt-in keyword ─────────────────────────────────────────────────────
    opt_in_keyword = by_name.get("AiWhatsApp.Outbound.OptInKeyword", "")
    if not opt_in_keyword:
        section.add(CheckResult(
            name="Opt-in keyword not set",
            status="warn",
            detail="Without an opt-in keyword, users cannot subscribe to receive outbound WhatsApp messages from the AI.",
            hint="Set an opt-in keyword (e.g. 'JOIN' or 'START') under Settings › AI Assistants › Channels › WhatsApp.",
        ))
    else:
        section.add(CheckResult(
            name="Opt-in keyword set",
            status="pass",
            detail=f'Users can opt in to outbound messages by sending: "{opt_in_keyword}"',
        ))

    return section


def _mins_to_hhmm(value: str) -> str:
    try:
        mins = int(value)
        return f"{mins // 60:02d}:{mins % 60:02d}"
    except (ValueError, TypeError):
        return value


def check_voice_channel(business_id: int) -> Section:
    section = Section("Voice")

    env = nexudus(["businesssettings", "list",
                   "--business-id", str(business_id),
                   "--name", "AiVoice",
                   "--page-size", "50"])

    if not env.get("ok"):
        section.add(CheckResult(
            name="Voice settings — data fetch failed",
            status="fail",
            detail=env.get("summary", "Could not fetch voice settings."),
        ))
        return section

    records = env.get("data") or []
    by_name = {r["Name"]: (r.get("Value") or "").strip() for r in records}

    enabled = by_name.get("AiVoice.Enabled", "").lower() == "true"

    # ── 1. Master toggle ───────────────────────────────────────────────────────
    if not enabled:
        section.add(CheckResult(
            name="Voice channel not enabled",
            status="warn",
            detail="The AI is not available on voice calls for this location.",
            hint="Enable Voice under Settings › AI Assistants › Channels › Voice and complete the Twilio and ElevenLabs configuration.",
        ))
        return section

    section.add(CheckResult(
        name="Voice channel enabled",
        status="pass",
        detail="The AI is active on voice calls for this location.",
    ))

    # ── 2. Twilio configuration ────────────────────────────────────────────────
    twilio_account = by_name.get("AiVoice.Twilio.AccountId", "")
    twilio_token   = by_name.get("AiVoice.Twilio.AuthToken", "")
    twilio_phone   = by_name.get("AiVoice.Twilio.PhoneNumber", "")

    twilio_missing = [k for k, v in [
        ("Account ID", twilio_account),
        ("Auth Token", twilio_token),
        ("Phone number", twilio_phone),
    ] if not v]

    if twilio_missing:
        section.add(CheckResult(
            name=f"Twilio configuration incomplete — {len(twilio_missing)} field{'s' if len(twilio_missing) != 1 else ''} missing",
            status="fail",
            detail=", ".join(twilio_missing),
            hint="Complete the Twilio configuration under Settings › AI Assistants › Channels › Voice.",
        ))
    else:
        section.add(CheckResult(
            name="Twilio configuration complete",
            status="pass",
            detail=f"Account ID set · Auth Token set · Phone number: {twilio_phone}",
        ))

    # ── 3. ElevenLabs configuration ────────────────────────────────────────────
    el_bearer  = by_name.get("AiVoice.Elevenlabs.BearerToken", "")
    el_auth    = by_name.get("AiVoice.Elevenlabs.AuthToken", "")
    el_agent   = by_name.get("AiVoice.Elevenlabs.AgentId", "")
    el_phone   = by_name.get("AiVoice.Elevenlabs.PhoneNumberId", "")

    el_missing = [k for k, v in [
        ("Bearer Token", el_bearer),
        ("Auth Token", el_auth),
        ("Agent ID", el_agent),
        ("Phone Number ID", el_phone),
    ] if not v]

    if el_missing:
        section.add(CheckResult(
            name=f"ElevenLabs configuration incomplete — {len(el_missing)} field{'s' if len(el_missing) != 1 else ''} missing",
            status="fail",
            detail=", ".join(el_missing),
            hint="Complete the ElevenLabs configuration under Settings › AI Assistants › Channels › Voice.",
        ))
    else:
        section.add(CheckResult(
            name="ElevenLabs configuration complete",
            status="pass",
            detail=f"Bearer Token set · Auth Token set · Agent ID set · Phone Number ID set",
        ))

    # ── 4. Outbound call window ────────────────────────────────────────────────
    start = by_name.get("AiVoice.Outbound.CallStartTime", "")
    end   = by_name.get("AiVoice.Outbound.CallEndTime", "")

    if start and end:
        section.add(CheckResult(
            name="Outbound call window set",
            status="pass",
            detail=f"{_mins_to_hhmm(start)} – {_mins_to_hhmm(end)}",
        ))
    else:
        section.add(CheckResult(
            name="Outbound call window not configured",
            status="warn",
            detail="No call start/end times set — the AI may attempt outbound calls at any hour.",
            hint="Set a call window under Settings › AI Assistants › Channels › Voice.",
        ))

    # ── 5. Outbound calling constraints (informational) ────────────────────────
    max_secs    = by_name.get("AiVoice.Outbound.MaxCallDurationSeconds", "")
    allow_wknd  = by_name.get("AiVoice.Outbound.AllowWeekendCalls", "").lower() == "true"
    allow_hols  = by_name.get("AiVoice.Outbound.AllowHolidayCalls", "").lower() == "true"
    max_defer   = by_name.get("AiVoice.Outbound.MaxDeferralHours", "")

    lines = []
    if max_secs:
        try:
            secs = int(max_secs)
            lines.append(f"Max call duration: {secs // 60}m {secs % 60}s")
        except ValueError:
            lines.append(f"Max call duration: {max_secs}s")
    if max_defer:
        lines.append(f"Max deferral: {max_defer} hours")
    lines.append(f"Weekend calls: {'allowed' if allow_wknd else 'not allowed'}")
    lines.append(f"Holiday calls: {'allowed' if allow_hols else 'not allowed'}")

    if lines:
        section.add(CheckResult(
            name="Outbound call constraints",
            status="pass",
            detail="\n".join(lines),
        ))

    return section


def check_email_channel(business_id: int) -> Section:
    section = Section("Email")

    # Email has no discoverable settings via the CLI — we infer setup from
    # whether any AI conversation sessions have Channel == "Email".
    env = nexudus(["openaichatmessages", "list",
                   "--business-id", str(business_id),
                   "--page-size", "200"])

    if not env.get("ok"):
        section.add(CheckResult(
            name="Email channel — session data unavailable",
            status="skip",
            detail="Could not fetch conversation history to check for email sessions.",
        ))
        return section

    records = env.get("data") or []
    email_messages = [r for r in records if (r.get("Channel") or "").lower() == "email"]

    if email_messages:
        section.add(CheckResult(
            name="Email channel in use",
            status="pass",
            detail=f"{len(email_messages)} email conversation message{'s' if len(email_messages) != 1 else ''} found — the email channel appears to be set up and active.",
        ))
    else:
        section.add(CheckResult(
            name="No email conversations detected",
            status="warn",
            detail="None of the recent AI conversation messages were received via the email channel.",
            hint="If you intend to use the email channel, check your email account configuration under Settings › AI Assistants › Channels › Email. If email is not yet in use, you can ignore this.",
        ))

    return section


