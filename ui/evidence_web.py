"""The evidence web: claim -> pressure/signals -> requested action -> evidence -> next step.

build_evidence_web(outcome) returns one self-contained HTML string (inline CSS, no
scripts, no external files). Everything that came from the message or the model is
escaped, so a message cannot inject markup into the page.
"""

import html

from core.schemas import NO_STRONG, PAUSE, STOP

# Accent colours per state. Deliberately no green: "no warning" must never look like "safe".
ACCENTS = {STOP: "#ff3b4e", PAUSE: "#ffb020", NO_STRONG: "#4aa8ff"}
# Each state also has an icon, so the colour is never the only cue.
ICONS = {STOP: "🛑", PAUSE: "⚠️", NO_STRONG: "🔎"}

ACTION_LABELS = {
    "pay": "pay money",
    "share_code": "share a one-time code / security code",
    "share_password": "share a password",
    "share_personal_details": "share personal details",
    "install_app": "install an app",
    "install_remote_access": "install remote-access software",
    "click_link": "open a link",
    "other": "do something else",
}

SIGNAL_LABELS = {
    "urgency": "Urgency",
    "advance_fee": "Up-front fee",
    "payment_request": "Payment request",
    "credential_request": "Code / password mentioned",
    "remote_access": "Remote access mentioned",
    "link": "Link",
    "other": "Other",
}

# Written as one line (no newlines) so Markdown cannot split the HTML block. No images, fonts or URLs.
CSS = (
    ".tg-hud{border:1px solid rgba(74,168,255,.55);border-radius:14px;padding:12px 14px 18px 14px;color:#f5f8ff;"
    "background:linear-gradient(180deg,rgba(16,36,80,.92),rgba(8,18,44,.95));"
    "box-shadow:0 0 28px rgba(47,107,255,.28),inset 0 0 40px rgba(74,168,255,.06);}"
    ".tg-head{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:14px;"
    "font-size:.78rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#4aa8ff;}"
    ".tg-state{border:2px solid var(--tg-accent);border-radius:999px;padding:2px 12px;letter-spacing:.06em;color:#f5f8ff;}"
    ".tg-web{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:32px;margin:0;padding:0;list-style:none;}"
    ".tg-col{position:relative;border:1px solid rgba(74,168,255,.55);border-top:4px solid var(--tg-accent);"
    "border-radius:10px;padding:12px;background:rgba(12,26,61,.96);font-size:.88rem;line-height:1.45;"
    "box-shadow:0 0 14px rgba(47,107,255,.22);}"
    ".tg-col:not(:last-child)::after{content:'';position:absolute;top:34px;right:-26px;width:26px;height:2px;"
    "background:linear-gradient(90deg,#4aa8ff,var(--tg-accent));box-shadow:0 0 8px #4aa8ff;}"
    ".tg-col:not(:last-child)::before{content:'';position:absolute;top:28px;right:-32px;width:0;height:0;"
    "border-left:8px solid var(--tg-accent);border-top:7px solid transparent;border-bottom:7px solid transparent;}"
    ".tg-title{font-weight:700;font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;color:#4aa8ff;margin-bottom:8px;}"
    ".tg-item{margin:0 0 9px 0;overflow-wrap:anywhere;}"
    ".tg-quote{display:block;font-style:italic;color:#d8e4ff;border-left:2px solid var(--tg-accent);padding-left:8px;margin-top:3px;}"
    ".tg-muted{color:#b4c2e0;}"
    ".tg-tag{display:inline-block;font-size:.72rem;font-weight:700;border:1px solid #4aa8ff;background:rgba(74,168,255,.16);"
    "border-radius:10px;padding:0 8px;margin-right:4px;color:#f5f8ff;}"
    "@media (max-width:1000px){.tg-web{grid-template-columns:1fr;gap:36px;}"
    ".tg-col:not(:last-child)::after{top:auto;right:auto;left:50%;bottom:-30px;width:2px;height:24px;"
    "background:linear-gradient(180deg,#4aa8ff,var(--tg-accent));}"
    ".tg-col:not(:last-child)::before{top:auto;right:auto;left:calc(50% - 7px);bottom:-36px;"
    "border-left:7px solid transparent;border-right:7px solid transparent;border-top:8px solid var(--tg-accent);border-bottom:0;}}"
)


def _e(value):
    """Escape for HTML. '$' is escaped too, so Streamlit does not treat it as maths."""
    text = " ".join(str(value).split())  # one line: blank lines would break Markdown HTML blocks
    return html.escape(text, quote=True).replace("$", "&#36;")


def _quote(text):
    return f'<span class="tg-quote">&ldquo;{_e(text)}&rdquo;</span>'


def _item(inner):
    return f'<div class="tg-item">{inner}</div>'


def _column(title, items):
    body = "".join(items) if items else _item('<span class="tg-muted">Nothing found</span>')
    return f'<li class="tg-col"><div class="tg-title">{_e(title)}</div>{body}</li>'


def _claim_items(extraction):
    who = extraction.claimed_identity or "Sender not identified"
    return [
        _item(f"<b>{_e(who)}</b>"),
        _item(_e(extraction.message_summary)),
    ]


def _signal_items(extraction):
    return [
        _item(f'<span class="tg-tag">{_e(SIGNAL_LABELS.get(s.type, s.type))}</span>{_quote(s.evidence_quote)}')
        for s in extraction.signals
    ]


def _action_items(extraction):
    action = extraction.requested_action
    if action.type == "none":
        return [_item('<span class="tg-muted">No request for you to act was found.</span>')]
    label = ACTION_LABELS.get(action.type, action.type)
    if action.sender_asks_user:
        line = f"The sender asks you to <b>{_e(label)}</b>."
    else:
        line = f'Mentions: {_e(label)}, but <b>not asking you to do it</b>.'
    items = [_item(line)]
    if action.evidence_quote:
        items.append(_item(_quote(action.evidence_quote)))
    return items


def _evidence_items(outcome):
    result = outcome.result
    items = []
    for r in result.reasons:
        kind = "Link observation" if r.evidence_kind == "url" else "Quote"
        items.append(_item(f"<b>{_e(r.text)}</b><span class=\"tg-quote\">{_e(kind)}: {_e(r.evidence)}</span>"))
    for r in result.minor_notes:
        kind = "Link observation" if r.evidence_kind == "url" else "Quote"
        items.append(_item(
            f'<span class="tg-muted">Noticed, no warning: {_e(r.text)}</span>'
            f'<span class="tg-quote tg-muted">{_e(kind)}: {_e(r.evidence)}</span>'))
    if not result.reasons:
        items.insert(0, _item("<b>No warning-level evidence found.</b>"))
    for obs in outcome.url_observations:
        if obs.accepted:
            line = f"<b>{_e(obs.hostname)}</b> (read from the link text only; never opened)"
        else:
            line = f"Link not inspected: {_e(obs.rejected_reason)}"
        items.append(_item(line))
    return items


def build_evidence_web(outcome):
    """HTML for a successful outcome (outcome.ok must be True)."""
    state = outcome.result.state
    accent = ACCENTS[state]
    columns = [
        _column("1. Claim", _claim_items(outcome.extraction)),
        _column("2. Pressure & signals", _signal_items(outcome.extraction)),
        _column("3. Requested action", _action_items(outcome.extraction)),
        _column("4. Evidence", _evidence_items(outcome)),
        _column("5. Safer next step", [_item(_e(s)) for s in outcome.result.next_steps]),
    ]
    head = f'<div class="tg-head"><span>Evidence web</span><span class="tg-state">{ICONS[state]} {_e(state)}</span></div>'
    label = "Evidence web: claim, pressure and signals, requested action, evidence, safer next step"
    return (f'<style>{CSS}</style><section class="tg-hud" aria-label="{label}" style="--tg-accent:{accent}">'
            f'{head}<ol class="tg-web" role="list">{"".join(columns)}</ol></section>')
