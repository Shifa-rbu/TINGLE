"""The decision rules. Plain if-statements, no scores, no probabilities, no network.

Rules in plain English
----------------------
STOP & VERIFY
  Rule 1: the SENDER asks the user to share an OTP/security code, share a password,
          or install remote-access software.
PAUSE & VERIFY
  Rule 2: the sender asks the user to pay AND the message also shows pressure
          (an urgency signal) or an advance-fee signal.
  Rule 3: the sender asks the user to do something AND a link in the message has
          a feature worth verifying (short link, IP address, '@' trick, ...).
NO STRONG WARNING SIGNALS FOUND
  Everything else. This never means "safe".

Things that do not trigger a warning by themselves (they become minor notes):
a deadline, a link, a payment request with no pressure, or a message that only
MENTIONS an OTP/password/remote access without asking the user to share it.
"""

from core.advice import get_next_steps
from core.schemas import NO_STRONG, PAUSE, STOP, Reason, Result
from tools.inspect_url import inspect_url

NOTE_STRONG = (
    "TINGLE is a checking aid, not proof. It found reasons to pause, but it cannot "
    "prove this message is fraudulent. Verify with an official source."
)
NOTE_NONE = (
    "No strong warning signal was found in what you submitted. This does NOT establish "
    "that the message is safe. Verify anything important with an official source."
)

# Rule 1: what each STOP-level request means in plain words.
STOP_ACTIONS = {
    "share_code": "The sender asks you to share a one-time code or security code.",
    "share_password": "The sender asks you to share a password.",
    "install_remote_access": "The sender asks you to install remote-access software, which can give someone control of your device.",
}


def quotes_of(extraction, signal_type):
    return [s.evidence_quote for s in extraction.signals if s.type == signal_type]


def assess(extraction, url_observations=None, user_context=None):
    """Turn an Extraction (plus URL observations) into a Result."""
    if url_observations is None:
        url_observations = [inspect_url(u) for u in extraction.urls]

    action = extraction.requested_action
    asked = action.sender_asks_user and action.type != "none"

    stop_reasons = []
    pause_reasons = []
    minor_notes = []

    urgency_quotes = quotes_of(extraction, "urgency")
    fee_quotes = quotes_of(extraction, "advance_fee")
    pressure_used = False

    # Rule 1: STOP
    if asked and action.type in STOP_ACTIONS:
        stop_reasons.append(Reason(
            text=STOP_ACTIONS[action.type],
            evidence=action.evidence_quote,
            evidence_kind="quote",
        ))

    # Rule 2: urgent payment / advance fee
    if asked and action.type == "pay":
        if urgency_quotes or fee_quotes:
            pause_reasons.append(Reason(
                text="The sender asks you to pay money.",
                evidence=action.evidence_quote,
                evidence_kind="quote",
            ))
            for q in urgency_quotes:
                pause_reasons.append(Reason(
                    text="Time pressure is attached to the payment request.",
                    evidence=q, evidence_kind="quote"))
            for q in fee_quotes:
                pause_reasons.append(Reason(
                    text="A fee is requested up front.",
                    evidence=q, evidence_kind="quote"))
            pressure_used = True
        else:
            minor_notes.append(Reason(
                text="The message asks you to pay, but no time pressure or up-front fee wording was found. Still confirm the payee with an official source.",
                evidence=action.evidence_quote,
                evidence_kind="quote",
            ))

    # Rule 3 + link notes
    has_flagged_url = False
    for obs in url_observations:
        if not obs.accepted:
            minor_notes.append(Reason(
                text="A URL could not be inspected, so nothing is known about it.",
                evidence=f"{obs.url or '(empty)'}: {obs.rejected_reason}",
                evidence_kind="url",
            ))
        elif obs.flags:
            has_flagged_url = True
            reason = Reason(
                text="A link in the message has features worth verifying. This is a reason to check it, not proof of fraud.",
                evidence=f"{obs.hostname}: " + "; ".join(obs.flags),
                evidence_kind="url",
            )
            if asked:
                pause_reasons.append(reason)
            else:
                minor_notes.append(reason)
        elif asked and action.type == "click_link":
            minor_notes.append(Reason(
                text="The message asks you to open a link. Verify it independently; https alone does not make a site safe.",
                evidence=f"{obs.hostname}: {obs.observations[-1]}",
                evidence_kind="url",
            ))

    # Mentions of codes/passwords/remote access that are NOT requests.
    mention_types = {
        "credential_request": "The message mentions a code or password, but the sender does not appear to be asking you to share it.",
        "remote_access": "The message mentions remote access, but the sender does not appear to be asking you to install it.",
    }
    for signal_type, text in mention_types.items():
        already_stopped = asked and action.type in STOP_ACTIONS
        if already_stopped:
            continue
        for q in quotes_of(extraction, signal_type):
            minor_notes.append(Reason(text=text, evidence=q, evidence_kind="quote"))

    # Urgency that did not lead to a warning: a deadline alone is not enough.
    if not pressure_used:
        for q in urgency_quotes:
            minor_notes.append(Reason(
                text="The message mentions a deadline or urgency. A deadline alone does not trigger a warning.",
                evidence=q, evidence_kind="quote"))

    # Choose the state: strongest rule wins.
    if stop_reasons:
        state, reasons, note = STOP, stop_reasons + pause_reasons, NOTE_STRONG
    elif pause_reasons:
        state, reasons, note = PAUSE, pause_reasons, NOTE_STRONG
    else:
        state, reasons, note = NO_STRONG, [], NOTE_NONE

    steps = get_next_steps(state, action.type if asked else "none", has_flagged_url, user_context)
    return Result(state=state, reasons=reasons, minor_notes=minor_notes, next_steps=steps, note=note)
