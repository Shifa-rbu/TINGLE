"""UI flow tests using Streamlit's AppTest. The model is mocked: no key, no network.

These check what the screens show. The decision logic is tested separately in
test_risk_rules.py and test_pipeline_mocked.py.
"""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import core.pipeline as pipeline
from core.schemas import AnalysisOutcome
from fake_model import SETTINGS, FakeClient, extraction_json, text_response

APP = str(Path(__file__).parent.parent / "app.py")
TITLE = "TINGLE — your before-you-tap Spider-Sense"


@pytest.fixture(autouse=True)
def no_key_no_dotenv(monkeypatch):
    """Start every UI test with no API key and without reading any local .env file."""
    import core.model_client as mc
    monkeypatch.setattr(mc, "load_dotenv", lambda: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def fresh():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def all_text(at):
    parts = []
    for group in (at.title, at.caption, at.markdown, at.info, at.warning, at.error, at.success, at.text, at.subheader):
        parts += [el.value for el in group]
    return "\n".join(parts)


def by_label(elements, label):
    return next(el for el in elements if el.label == label)


# ---- first screen -----------------------------------------------------------------

def test_title_tagline_and_notice_are_shown_before_any_analysis():
    at = fresh()
    assert not at.exception
    assert at.title[0].value == TITLE
    notice = at.info[0].value
    assert "sent to the configured AI provider" in notice
    assert "does not store" in notice
    assert "cannot prove a message is a scam" in notice and "cannot prove a message is safe" in notice


def test_without_a_key_it_starts_in_sample_mode_and_explains():
    at = fresh()
    assert at.radio(key="mode").value.startswith("Try a synthetic sample")
    assert at.button[0].label == "Check before acting"
    assert any(b.label == "Clear" for b in at.button)


def test_live_mode_without_key_shows_a_friendly_warning():
    at = fresh()
    at.radio(key="mode").set_value("Check my own message").run()
    assert any("ANTHROPIC_API_KEY" in w.value for w in at.warning)
    assert not at.exception


def test_context_selector_has_the_expected_choices():
    at = fresh()
    options = at.selectbox(key="ctx_0").options
    assert options == ["Not selected", "Paying", "Clicking a link", "Sharing a code or personal details",
                       "Installing an app", "Not sure"]


# ---- sample mode ---------------------------------------------------------------------

def test_sample_check_shows_a_labelled_synthetic_result_with_evidence_web():
    at = fresh()
    at.button[0].click().run()
    assert not at.exception
    text = all_text(at)
    assert "Synthetic sample" in text and "not a live analysis" in text
    assert "PAUSE & VERIFY" in text  # the first sample is the fake internship fee
    assert "does not establish" in text.lower() or "not proof" in text.lower()
    web = [m.value for m in at.markdown if "tg-web" in m.value]
    assert len(web) == 1 and "5. Safer next step" in web[0]
    assert "What TINGLE could not establish" in all_text(at)


def test_sample_with_no_strong_signal_is_an_info_box_never_a_success_box():
    at = fresh()
    cases = json.loads((Path(APP).parent / "examples" / "sample_cases.json").read_text(encoding="utf-8"))["cases"]
    idx = next(i for i, c in enumerate(cases) if c["id"] == "campus_quiz_deadline")
    at.selectbox(key="sample_0").set_value(idx).run()
    at.button[0].click().run()
    assert any("NO STRONG WARNING SIGNALS FOUND" in i.value and "does NOT establish" in i.value for i in at.info)
    assert len(at.success) == 0
    assert not any("STOP & VERIFY" in e.value for e in at.error)


def test_clear_removes_the_result():
    at = fresh()
    at.button[0].click().run()
    assert any("tg-web" in m.value for m in at.markdown)
    by_label(at.button, "Clear").click().run()
    assert not any("tg-web" in m.value for m in at.markdown)
    assert "not a live analysis" not in all_text(at)


def test_changing_mode_hides_an_old_result():
    at = fresh()
    at.button[0].click().run()
    at.radio(key="mode").set_value("Check my own message").run()
    assert not any("tg-web" in m.value for m in at.markdown)


# ---- live mode: errors are never shown as a safe result -----------------------------------

def run_live_text(at, text):
    at.radio(key="mode").set_value("Check my own message").run()
    at.text_area(key="text_0").set_value(text).run()
    at.button[0].click().run()
    return at


def assert_error_not_safe(at):
    assert len(at.error) >= 1
    assert not any("NO STRONG WARNING SIGNALS FOUND" in i.value for i in at.info)
    assert len(at.success) == 0
    assert not any("tg-web" in m.value for m in at.markdown)
    assert "not a sign the message is safe" in all_text(at)


def test_missing_key_gives_a_friendly_error_and_points_to_sample_mode():
    at = run_live_text(fresh(), "Please share the OTP you just received.")
    assert_error_not_safe(at)
    assert any("ANTHROPIC_API_KEY" in e.value for e in at.error)
    assert any("sample" in i.value.lower() for i in at.info)


@pytest.mark.parametrize("error", [
    "The request to the model timed out. Please try again.",
    "The model's answer was not in the expected format, so no result is shown. Please try again.",
    "The model declined to analyse this content. No result is shown.",
])
def test_provider_failure_and_malformed_response_show_an_error_not_a_safe_result(monkeypatch, error):
    monkeypatch.setattr(pipeline, "analyze_text", lambda text, user_context=None: AnalysisOutcome(ok=False, error=error))
    at = run_live_text(fresh(), "some message")
    assert_error_not_safe(at)
    assert any(error in e.value for e in at.error)


def test_empty_text_gives_a_validation_error():
    at = run_live_text(fresh(), "")
    assert_error_not_safe(at)
    assert any("paste a message" in e.value.lower() for e in at.error)


def test_live_result_is_labelled_live_not_synthetic(monkeypatch):
    real = pipeline.analyze_text
    out = extraction_json(requested_action={"type": "share_code", "sender_asks_user": True,
                                            "evidence_quote": "share the OTP you just received"})
    monkeypatch.setattr(pipeline, "analyze_text", lambda text, user_context=None: real(
        text, user_context=user_context, client=FakeClient(text_response(out)), settings=SETTINGS))
    at = run_live_text(fresh(), "Please share the OTP you just received.")
    assert not at.exception
    assert any("STOP & VERIFY" in e.value for e in at.error)
    text = all_text(at)
    assert "Live analysis" in text and "not a live analysis" not in text
    assert any("tg-web" in m.value for m in at.markdown)


def test_user_context_reaches_the_advice(monkeypatch):
    real = pipeline.analyze_text
    out = extraction_json(requested_action={"type": "pay", "sender_asks_user": True, "evidence_quote": "pay now"},
                          signals=[{"type": "urgency", "evidence_quote": "now"}])
    monkeypatch.setattr(pipeline, "analyze_text", lambda text, user_context=None: real(
        text, user_context=user_context, client=FakeClient(text_response(out)), settings=SETTINGS))
    at = fresh()
    at.radio(key="mode").set_value("Check my own message").run()
    at.text_area(key="text_0").set_value("pay now").run()
    at.selectbox(key="ctx_0").set_value("Paying").run()
    at.button[0].click().run()
    assert any("You said you are considering paying" in m.value for m in at.markdown)


def test_model_text_cannot_render_markdown_in_the_uncertainties_box(monkeypatch):
    real = pipeline.analyze_text
    out = extraction_json(uncertainties=["![pixel](http://evil.test/p.png) [click](http://evil.test)"])
    monkeypatch.setattr(pipeline, "analyze_text", lambda text, user_context=None: real(
        text, user_context=user_context, client=FakeClient(text_response(out)), settings=SETTINGS))
    at = run_live_text(fresh(), "hello there")
    assert any("evil.test" in t.value for t in at.text)  # shown as plain text
    assert not any("evil.test" in m.value for m in at.markdown)  # never passed to Markdown
