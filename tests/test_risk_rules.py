import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.risk_rules import assess
from core.schemas import NO_STRONG, PAUSE, STOP, Extraction


def make(action_type="none", asks=False, quote=None, signals=None, urls=None, source="text"):
    """Small helper to build an Extraction for a test."""
    return Extraction(
        message_summary="test message",
        requested_action={"type": action_type, "sender_asks_user": asks, "evidence_quote": quote},
        signals=signals or [],
        urls=urls or [],
        source=source,
    )


def sig(kind, quote):
    return {"type": kind, "evidence_quote": quote}


# ---- Rule 1: STOP --------------------------------------------------------

def test_explicit_otp_request_is_stop_and_cites_quote():
    e = make("share_code", True, "send me the OTP you just received",
             [sig("credential_request", "send me the OTP you just received")])
    r = assess(e)
    assert r.state == STOP
    assert r.reasons[0].evidence == "send me the OTP you just received"
    assert r.reasons[0].evidence_kind == "quote"


def test_password_request_is_stop():
    r = assess(make("share_password", True, "reply with your password"))
    assert r.state == STOP


def test_remote_access_install_request_is_stop():
    r = assess(make("install_remote_access", True, "Install the RemoteFix app"))
    assert r.state == STOP
    assert "remote-access" in r.reasons[0].text


def test_never_share_otp_warning_is_not_a_request():
    e = make("none", False, None, [sig("credential_request", "Never share your OTP with anyone")])
    r = assess(e)
    assert r.state == NO_STRONG
    assert r.reasons == []
    # It is shown as a minor note that quotes the message, not as a warning.
    assert any(n.evidence == "Never share your OTP with anyone" for n in r.minor_notes)


def test_request_flag_false_means_no_stop_even_if_type_is_share_code():
    # The rules trust sender_asks_user. If it is False, there is no request.
    r = assess(make("share_code", False, None))
    assert r.state == NO_STRONG


# ---- Rule 2: PAUSE for urgent payment / advance fee ----------------------

def test_urgent_internship_fee_is_pause_with_evidence():
    e = make("pay", True, "Pay Rs 699 to confirm your seat",
             [sig("urgency", "within 10 minutes"), sig("advance_fee", "Pay Rs 699")])
    r = assess(e)
    assert r.state == PAUSE
    evidence = [x.evidence for x in r.reasons]
    assert "Pay Rs 699 to confirm your seat" in evidence
    assert "within 10 minutes" in evidence
    assert "Pay Rs 699" in evidence


def test_advance_fee_without_urgency_is_still_pause():
    e = make("pay", True, "pay the joining fee", [sig("advance_fee", "joining fee")])
    assert assess(e).state == PAUSE


def test_payment_with_no_pressure_is_not_a_warning_but_is_noted():
    e = make("pay", True, "pay at the student desk")
    r = assess(e)
    assert r.state == NO_STRONG
    assert any(n.evidence == "pay at the student desk" for n in r.minor_notes)


def test_urgency_without_payment_request_is_not_pause():
    e = make("pay", False, None, [sig("urgency", "within 10 minutes")])
    assert assess(e).state == NO_STRONG


def test_stop_beats_pause_when_both_apply():
    e = make("share_code", True, "tell us the code",
             [sig("urgency", "right now")], urls=["https://bit.ly/x"])
    assert assess(e).state == STOP


# ---- Deadline alone ------------------------------------------------------

def test_campus_event_deadline_alone_is_not_the_strongest_warning():
    e = make("none", False, None, [sig("urgency", "closes on Friday at 5 PM")])
    r = assess(e)
    assert r.state == NO_STRONG
    assert r.state != STOP
    assert any("deadline alone" in n.text for n in r.minor_notes)


# ---- Rule 3 / URLs -------------------------------------------------------

def test_short_link_with_a_request_prompts_pause_but_not_stop():
    e = make("click_link", True, "Confirm delivery details here", urls=["https://bit.ly/abc"])
    r = assess(e)
    assert r.state == PAUSE
    url_reason = [x for x in r.reasons if x.evidence_kind == "url"][0]
    assert "link shortener" in url_reason.evidence
    assert "not proof of fraud" in url_reason.text


def test_short_link_with_no_request_is_only_a_minor_note():
    e = make("none", False, None, urls=["https://bit.ly/abc"])
    r = assess(e)
    assert r.state == NO_STRONG
    assert any(n.evidence_kind == "url" for n in r.minor_notes)


def test_ordinary_https_link_with_click_request_is_not_a_warning():
    e = make("click_link", True, "see the schedule here", urls=["https://schedule.example.test/week1"])
    r = assess(e)
    assert r.state == NO_STRONG
    assert any("https alone does not make a site safe" in n.text for n in r.minor_notes)


def test_invalid_and_non_web_urls_are_handled_safely():
    e = make("none", False, None, urls=["javascript:alert(1)", "not a url", "https://example.test/" + "a" * 5000])
    r = assess(e)
    assert r.state == NO_STRONG  # unknown is not "dangerous" and not "safe"
    assert len([n for n in r.minor_notes if n.evidence_kind == "url"]) == 3
    assert "NOT establish" in r.note


# ---- No-strong note, advice, context -------------------------------------

def test_no_strong_result_says_it_does_not_establish_safety():
    r = assess(make())
    assert r.state == NO_STRONG
    assert "does NOT establish" in r.note
    assert r.next_steps


def test_strong_result_note_says_it_is_not_proof():
    r = assess(make("share_code", True, "send the OTP"))
    assert "not proof" in r.note


def test_next_steps_match_the_request_type():
    otp = assess(make("share_code", True, "send the OTP")).next_steps
    pay = assess(make("pay", True, "pay now", [sig("urgency", "now")])).next_steps
    assert any("code" in s for s in otp)
    assert any("Do not pay yet" in s for s in pay)
    assert otp != pay


def test_user_context_only_adds_a_reminder_and_never_changes_the_state():
    e = make("share_code", True, "send the OTP")
    plain = assess(e)
    with_context = assess(e, user_context="paying")
    assert plain.state == with_context.state
    assert len(with_context.next_steps) == len(plain.next_steps) + 1


def test_advice_never_claims_certainty():
    texts = []
    for e in (make("share_code", True, "send the OTP"), make("pay", True, "pay now", [sig("urgency", "now")]), make()):
        r = assess(e)
        texts += r.next_steps + [r.note]
    joined = " ".join(texts).lower()
    # ("is safe" is not banned: the note correctly says "does NOT establish that the message is safe".)
    for phrase in ("this is a scam", "definitely", "100%", "guaranteed safe", "is definitely"):
        assert phrase not in joined


def test_every_displayed_reason_has_evidence():
    e = make("pay", True, "pay now", [sig("urgency", "now")], urls=["https://bit.ly/a"])
    r = assess(e)
    for item in r.reasons + r.minor_notes:
        assert item.evidence.strip()
        assert item.evidence_kind in ("quote", "url")


# ---- Schema validation ---------------------------------------------------

def test_request_without_quote_is_rejected_by_schema():
    with pytest.raises(ValidationError):
        make("share_code", True, None)


def test_request_with_type_none_is_rejected_by_schema():
    with pytest.raises(ValidationError):
        make("none", True, "do it")


def test_unknown_action_type_and_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        make("hack_the_planet", False)
    with pytest.raises(ValidationError):
        Extraction(message_summary="x", scam_probability=0.97)


def test_too_many_urls_are_rejected():
    with pytest.raises(ValidationError):
        make(urls=[f"https://example.test/{i}" for i in range(6)])


# ---- Synthetic sample cases ----------------------------------------------

CASES = json.loads((Path(__file__).parent.parent / "examples" / "sample_cases.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_sample_case_gives_expected_state(case):
    r = assess(Extraction(**case["extraction"]))
    assert r.state == case["expected_state"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_sample_case_quotes_really_appear_in_the_sample_text(case):
    e = Extraction(**case["extraction"])
    quotes = [s.evidence_quote for s in e.signals]
    if e.requested_action.evidence_quote:
        quotes.append(e.requested_action.evidence_quote)
    for q in quotes:
        assert q in case["text"], q


def test_samples_include_both_suspicious_and_benign():
    kinds = {c["kind"] for c in CASES}
    assert kinds == {"suspicious", "benign"}
