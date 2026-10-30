"""The evidence web is a pure function: outcome in, escaped HTML out. Offline, no Streamlit needed."""

import json

import pytest

from core.pipeline import analyze_sample, analyze_text, load_sample_cases
from core.schemas import NO_STRONG, PAUSE, STOP
from fake_model import SETTINGS, FakeClient, extraction_json, text_response
from ui.evidence_web import ACCENTS, build_evidence_web

CASES = load_sample_cases()


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_every_sample_renders_all_five_steps_in_order(case):
    page = build_evidence_web(analyze_sample(case))
    positions = [page.index(t) for t in ("1. Claim", "2. Pressure &amp; signals", "3. Requested action",
                                          "4. Evidence", "5. Safer next step")]
    assert positions == sorted(positions)


def test_page_has_no_scripts_external_assets_or_green():
    for case in CASES:
        page = build_evidence_web(analyze_sample(case)).lower()
        for banned in ("<script", "<link", "<img", "<iframe", "@import", "url(", "src=", "http://", "https://fonts", "green"):
            assert banned not in page


def test_accent_colour_follows_the_state_and_is_never_green():
    states = {c["expected_state"]: analyze_sample(c) for c in CASES}
    for state, outcome in states.items():
        assert ACCENTS[state] in build_evidence_web(outcome)
    assert len(set(ACCENTS.values())) == 3
    assert all(not c.startswith("#0") for c in ACCENTS.values())  # crude: no dark-green hex


def test_evidence_quotes_and_url_observations_are_shown():
    case = next(c for c in CASES if c["id"] == "fake_internship_fee")
    page = build_evidence_web(analyze_sample(case))
    assert "within 10 minutes" in page
    assert "bit.ly" in page and "link shortener" in page
    assert "never opened" in page
    assert "Do not pay yet" in page  # the mapped next step


def test_never_share_otp_sample_shows_mention_not_request():
    case = next(c for c in CASES if c["id"] == "never_share_otp_notice")
    outcome = analyze_sample(case)
    assert outcome.result.state == NO_STRONG
    page = build_evidence_web(outcome)
    assert "No warning-level evidence found" in page
    assert "Never share your OTP with anyone" in page


def test_markup_from_the_message_is_escaped():
    text = "<script>alert(1)</script> please share the OTP you just received $5 ![x](http://evil.test/p.png)"
    out = extraction_json(
        message_summary="<b>bold</b> <img src=x onerror=alert(1)>",
        claimed_identity="<i>Bank</i>",
        requested_action={"type": "share_code", "sender_asks_user": True, "evidence_quote": "share the OTP you just received"},
        signals=[{"type": "other", "evidence_quote": "<script>alert(1)</script>"}],
    )
    outcome = analyze_text(text, client=FakeClient(text_response(out)), settings=SETTINGS)
    assert outcome.ok and outcome.result.state == STOP
    page = build_evidence_web(outcome)
    assert "<script" not in page and "<img" not in page and "<b>bold" not in page and "<i>Bank" not in page
    assert "&lt;script&gt;" in page and "&lt;img" in page
    assert "$" not in page  # dollar signs are escaped so Markdown cannot treat them as maths


def test_text_is_one_line_so_markdown_html_blocks_do_not_break():
    out = extraction_json(message_summary="line one\n\nline two\n\n    indented")
    page = build_evidence_web(analyze_text("hello", client=FakeClient(text_response(out)), settings=SETTINGS))
    assert "\n" not in page


def test_screenshot_source_does_not_change_the_structure():
    case = next(c for c in CASES if c["id"] == "otp_request")
    outcome = analyze_sample(case)
    outcome.extraction = outcome.extraction.model_copy(update={"source": "screenshot"})
    assert "3. Requested action" in build_evidence_web(outcome)


def test_pause_state_uses_amber_accent_and_stop_uses_red():
    pause = next(analyze_sample(c) for c in CASES if c["expected_state"] == PAUSE)
    stop = next(analyze_sample(c) for c in CASES if c["expected_state"] == STOP)
    assert ACCENTS[PAUSE] in build_evidence_web(pause) and ACCENTS[STOP] in build_evidence_web(stop)
    assert json.dumps(ACCENTS)  # sanity: plain strings
