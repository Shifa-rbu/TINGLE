"""Validation of what the model returns (parsing, schema, evidence checks). Mocked, offline."""

import json

import pytest

from core.model_client import AnalysisError, validate_tool_args
from core.pipeline import analyze_text, parse_model_json
from core.schemas import NO_STRONG, STOP
from fake_model import SETTINGS, FakeClient, extraction_json, text_response

OTP_TEXT = "Hello, please share the OTP you just received to verify your account."
OTP_ACTION = {"type": "share_code", "sender_asks_user": True, "evidence_quote": "share the OTP you just received"}


def run(text, model_output, **kw):
    client = FakeClient(text_response(model_output))
    return analyze_text(text, client=client, settings=SETTINGS, **kw)


# ---- parse_model_json ----------------------------------------------------

def test_plain_json_is_parsed():
    assert parse_model_json('{"a": 1}') == {"a": 1}


def test_code_fence_and_surrounding_prose_are_tolerated():
    assert parse_model_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_model_json('Here you go: {"a": 1} thanks') == {"a": 1}


@pytest.mark.parametrize("bad", ["", "   ", "not json", "{broken", "[1, 2]", "null", None])
def test_unparseable_output_raises_analysis_error(bad):
    with pytest.raises(AnalysisError):
        parse_model_json(bad)


# ---- schema validation through the pipeline ------------------------------

@pytest.mark.parametrize("bad_output", [
    "not json at all",
    "",
    "[]",
    json.dumps({"message_summary": 123}),  # wrong type
    json.dumps({"claimed_identity": None}),  # summary missing
    extraction_json(scam_probability=0.97),  # extra field is forbidden
    extraction_json(signals=[{"type": "vibes", "evidence_quote": "x"}]),  # unknown signal type
    extraction_json(requested_action={"type": "teleport", "sender_asks_user": False, "evidence_quote": None}),
    extraction_json(requested_action={"type": "share_code", "sender_asks_user": True, "evidence_quote": None}),
    extraction_json(requested_action={"type": "none", "sender_asks_user": True, "evidence_quote": "x"}),
    extraction_json(urls=[f"https://example.test/{i}" for i in range(6)]),  # too many URLs
])
def test_bad_model_output_gives_an_error_and_never_a_result(bad_output):
    outcome = run(OTP_TEXT, bad_output)
    assert outcome.ok is False
    assert outcome.result is None
    assert outcome.extraction is None
    assert outcome.error


def test_error_message_does_not_echo_the_users_text():
    outcome = run("MY-PRIVATE-WORDS-777", extraction_json(scam_probability=1))
    assert "MY-PRIVATE-WORDS-777" not in outcome.error


def test_model_cannot_choose_the_source_field():
    out = extraction_json(requested_action=OTP_ACTION, source="screenshot")
    outcome = run(OTP_TEXT, out)
    assert outcome.ok and outcome.extraction.source == "text"


# ---- the model extracts; our rules decide ---------------------------------

def test_valid_extraction_goes_through_the_deterministic_rules():
    outcome = run(OTP_TEXT, extraction_json(requested_action=OTP_ACTION))
    assert outcome.ok and outcome.mode == "live"
    assert outcome.result.state == STOP
    assert outcome.result.reasons[0].evidence == "share the OTP you just received"


def test_a_state_or_score_written_by_the_model_is_rejected_not_used():
    out = extraction_json(requested_action=OTP_ACTION, state="NO STRONG WARNING SIGNALS FOUND", risk="low")
    outcome = run(OTP_TEXT, out)
    assert outcome.ok is False


def test_never_share_otp_message_is_not_flagged():
    text = "Bank notice: never share your OTP with anyone."
    out = extraction_json(signals=[{"type": "credential_request", "evidence_quote": "never share your OTP"}])
    outcome = run(text, out)
    assert outcome.ok and outcome.result.state == NO_STRONG
    assert "does NOT establish" in outcome.result.note


# ---- evidence must appear in pasted text ----------------------------------

def test_fabricated_request_quote_fails_instead_of_producing_a_result():
    fake_action = {"type": "pay", "sender_asks_user": True, "evidence_quote": "pay 5000 rupees now"}
    outcome = run(OTP_TEXT, extraction_json(requested_action=fake_action))
    assert outcome.ok is False and outcome.result is None


def test_quote_matching_ignores_case_and_spacing():
    action = dict(OTP_ACTION, evidence_quote="SHARE   the otp\nyou just received")
    outcome = run(OTP_TEXT, extraction_json(requested_action=action))
    assert outcome.ok and outcome.result.state == STOP


def test_fabricated_signal_and_url_are_dropped_with_a_note():
    out = extraction_json(
        signals=[{"type": "urgency", "evidence_quote": "act within 5 minutes"}],  # not in the text
        urls=["https://made-up.example.test/x"],  # not in the text
    )
    outcome = run(OTP_TEXT, out)
    assert outcome.ok
    assert outcome.extraction.signals == []
    assert outcome.extraction.urls == []
    assert any("left out" in u for u in outcome.extraction.uncertainties)


def test_unverifiable_quote_on_a_non_request_is_dropped_not_fatal():
    action = {"type": "none", "sender_asks_user": False, "evidence_quote": "something not in the text"}
    outcome = run(OTP_TEXT, extraction_json(requested_action=action))
    assert outcome.ok and outcome.extraction.requested_action.evidence_quote is None


# ---- tool argument validation --------------------------------------------

def test_valid_tool_args():
    assert validate_tool_args({"url": "https://example.test"}) == "https://example.test"


@pytest.mark.parametrize("bad", [
    None, "https://example.test", ["https://example.test"], {}, {"url": ""}, {"url": "   "},
    {"url": 5}, {"url": None}, {"url": "https://example.test", "extra": 1}, {"link": "https://x.test"},
    {"url": "https://example.test/" + "a" * 3000},
])
def test_invalid_tool_args_are_rejected(bad):
    with pytest.raises(ValueError):
        validate_tool_args(bad)
