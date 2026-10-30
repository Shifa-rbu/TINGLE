"""TINGLE: Streamlit screens only. All analysis lives in core/ (model call, validation, rules)."""

import streamlit as st

from core.image_prep import MAX_IMAGE_BYTES, ImageError, prepare_image
from core.model_client import load_settings
from core.pipeline import MAX_TEXT_CHARS, analyze_image, analyze_sample, analyze_text, load_sample_cases
from core.schemas import NO_STRONG, PAUSE, STOP, AnalysisOutcome
from ui.evidence_web import build_evidence_web
from ui.theme import apply_theme, show_emblem

LIVE_MODE = "Check my own message"
SAMPLE_MODE = "Try a synthetic sample (no API key needed)"
PASTE = "Paste text"
UPLOAD = "Upload a screenshot"

# What the user is thinking of doing. The value is what core/advice.py understands.
CONTEXT_CHOICES = {
    "Not selected": None,
    "Paying": "paying",
    "Clicking a link": "clicking a link",
    "Sharing a code or personal details": "sharing a code/personal details",
    "Installing an app": "installing an app",
    "Not sure": None,
}

BANNER_LINES = {
    STOP: "Do not act on this request yet. Verify it through an official channel you look up yourself.",
    PAUSE: "Pause before you act. Verify this through an official source you find yourself.",
    NO_STRONG: "TINGLE did not find a strong warning sign in what you submitted.",
}


def notice_text(provider):
    return (
        "**Before you start.** TINGLE helps you pause and verify. It cannot prove a message is a scam, "
        "and it cannot prove a message is safe.  \n"
        f"When you check your own message, the text or screenshot is **sent to the configured AI provider "
        f"({provider.title()})** for analysis. This prototype **does not store** your messages or screenshots "
        "and keeps no log. The result stays only in this browser session until you press **Clear**.  \n"
        "Synthetic sample cases are processed locally: no AI provider is contacted."
    )


# --------------------------------------------------------------- session state

def clear_outcome():
    st.session_state["outcome"] = None
    st.session_state["sample_note"] = None


def clear_all():
    clear_outcome()
    st.session_state["n"] += 1  # new widget keys, so every input box starts empty


def render_error(message):
    with st.container(key="tgx_banner_error"):
        st.error(message, icon="🚫")
    st.caption(
        "No result was produced. That is not a sign the message is safe: "
        "please verify it through an official channel."
    )
    if "ANTHROPIC_API_KEY" in message or "provider" in message.lower():
        st.info("You can still explore TINGLE with the synthetic sample cases: switch to sample mode above. No key is needed.")


def render_outcome(outcome):
    if not outcome.ok:
        render_error(outcome.error)
        return

    result = outcome.result
    if outcome.mode == "sample":
        with st.container(key="tgx_synthetic"):
            st.info("🧪 **Synthetic sample.** This is a hand-written stand-in for AI output, not a live analysis of a real message.")
    elif outcome.extraction.source == "screenshot":
        st.caption("Live analysis. The text below was read from your screenshot by the AI model, so quotes could not be checked automatically.")
    else:
        st.caption("Live analysis: AI extraction, then TINGLE's fixed rules decide the warning.")

    # Each banner has its own icon, label and border style, so colour is never the only signal.
    if result.state == STOP:
        with st.container(key="tgx_banner_stop"):
            st.error(f"### {STOP}\n{BANNER_LINES[STOP]}", icon="🛑")
        st.info(result.note)
    elif result.state == PAUSE:
        with st.container(key="tgx_banner_pause"):
            st.warning(f"### {PAUSE}\n{BANNER_LINES[PAUSE]}", icon="⚠️")
        st.info(result.note)
    else:
        with st.container(key="tgx_banner_none"):
            st.info(f"### {NO_STRONG}\n{BANNER_LINES[NO_STRONG]}  \n**{result.note}**", icon="🔎")

    st.subheader("How TINGLE connected the evidence")
    st.markdown(build_evidence_web(outcome), unsafe_allow_html=True)

    st.subheader("What TINGLE could not establish")
    with st.container(key="tgx_unc"):
        # st.text, not Markdown: this text comes from the model and must not render links or images.
        if outcome.extraction.uncertainties:
            for item in outcome.extraction.uncertainties:
                st.text("• " + item)
        else:
            st.text("• No specific uncertainties were reported. That does not mean there are none.")
        st.text("• TINGLE reads only what you gave it. It cannot check who really sent the message.")

    note = st.session_state.get("sample_note")
    if note and outcome.mode == "sample":
        st.caption("About this sample: " + note)


# ------------------------------------------------------------------------ page

st.set_page_config(page_title="TINGLE", page_icon="🕷️", layout="wide")

if "n" not in st.session_state:
    st.session_state["n"] = 0
    clear_outcome()

settings = load_settings()
has_key = bool(settings["api_key"])
if "mode" not in st.session_state:
    st.session_state["mode"] = LIVE_MODE if has_key else SAMPLE_MODE
n = st.session_state["n"]

apply_theme()
show_emblem()
st.title("TINGLE — your before-you-tap Spider-Sense")
st.caption("Paste a message or upload a screenshot before you pay, click, share a code or install anything.")
with st.container(key="tgx_notice"):
    st.info(notice_text(settings["provider"]))

mode = st.radio("Mode", [LIVE_MODE, SAMPLE_MODE], key="mode", horizontal=True, on_change=clear_outcome)
live = mode == LIVE_MODE

text, uploaded, case = "", None, None
if live:
    if not has_key:
        st.warning("No API key is configured (environment variable ANTHROPIC_API_KEY), so live checks will not run. "
                   "Add it to your .env file, or switch to the synthetic sample mode.")
    kind = st.radio("What do you want to check?", [PASTE, UPLOAD], horizontal=True, on_change=clear_outcome)
    if kind == PASTE:
        text = st.text_area("Message", key=f"text_{n}", height=180, max_chars=MAX_TEXT_CHARS,
                            placeholder="Paste the message you received here…")
    else:
        uploaded = st.file_uploader(f"Screenshot (PNG or JPG, up to {MAX_IMAGE_BYTES // (1024 * 1024)} MB)",
                                    type=["png", "jpg", "jpeg"], key=f"file_{n}")
        if uploaded is not None:
            # Validate first with the same function the pipeline uses: a bad file must give a clear
            # message, and st.image would crash on invalid bytes. The preview is the cleaned image.
            try:
                preview, _ = prepare_image(uploaded.getvalue())
                st.image(preview, width=320, caption="Preview (metadata removed). Shown only on your screen until you press Check.")
            except ImageError as e:
                st.error(str(e))
else:
    cases = load_sample_cases()
    index = st.selectbox("Sample case", range(len(cases)), format_func=lambda i: cases[i]["title"],
                         key=f"sample_{n}", on_change=clear_outcome)
    case = cases[index]
    st.text_area("Synthetic example message", value=case["text"], height=120, disabled=True, key=f"sample_text_{n}_{index}")
    st.caption("Synthetic: written for this prototype. Not a real message, person or company.")

context_label = st.selectbox("Optional: what are you thinking of doing?", list(CONTEXT_CHOICES), key=f"ctx_{n}")
user_context = CONTEXT_CHOICES[context_label]

left, right, _ = st.columns([2, 1, 4])
check = left.button("Check before acting", type="primary", use_container_width=True)
right.button("Clear", on_click=clear_all, use_container_width=True)

if check:
    outcome = None
    if not live:
        outcome = analyze_sample(case, user_context=user_context)
        st.session_state["sample_note"] = case.get("note")
    elif kind == PASTE:
        with st.spinner("Reading the message and applying TINGLE's rules…"):
            outcome = analyze_text(text, user_context=user_context)
    elif uploaded is None:
        outcome = AnalysisOutcome(ok=False, error="Please upload a PNG or JPG screenshot first.")
    else:
        with st.spinner("Sending the screenshot to the AI model, then applying TINGLE's rules…"):
            outcome = analyze_image(uploaded.getvalue(), user_context=user_context)
    st.session_state["outcome"] = outcome

if st.session_state.get("outcome") is not None:
    st.divider()
    render_outcome(st.session_state["outcome"])

st.divider()
st.caption("TINGLE is a prototype risk-checking aid. It is not a live threat-intelligence service, never opens links, "
           "and never pays, blocks or reports anything for you.")
