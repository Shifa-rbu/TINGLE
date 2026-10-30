"""Input -> model -> validation -> URL observations -> deterministic rules -> outcome.

The model only extracts. The warning state and the advice come from core/risk_rules.py.
Any failure becomes AnalysisOutcome(ok=False, error=...). It is never turned into a
"safe" result. User content is kept in local variables only: not logged, not saved.
"""

import json
import re
from pathlib import Path

from pydantic import ValidationError

from core.image_prep import ImageError, prepare_image
from core.model_client import (
    AnalysisError,
    build_image_content,
    build_text_content,
    load_settings,
    make_client,
    run_extraction,
)
from core.risk_rules import assess
from core.schemas import AnalysisOutcome, Extraction
from tools.inspect_url import inspect_url

MAX_TEXT_CHARS = 6000
SAMPLES_FILE = Path(__file__).resolve().parent.parent / "examples" / "sample_cases.json"

MALFORMED = "The model's answer was not in the expected format, so no result is shown. Please try again."


# ------------------------------------------------------- parsing and checks

def parse_model_json(raw_text):
    """Turn the model's reply into a dict, or raise AnalysisError."""
    text = (raw_text or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise AnalysisError(MALFORMED)
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        raise AnalysisError(MALFORMED) from None
    if not isinstance(data, dict):
        raise AnalysisError(MALFORMED)
    return data


def validate_extraction(data, source):
    """Check the dict against the schema. The app, not the model, decides `source`."""
    data = dict(data)
    data.pop("source", None)
    try:
        extraction = Extraction.model_validate(data)
    except ValidationError:
        # The error text can contain the user's own words, so it is not shown.
        raise AnalysisError(MALFORMED) from None
    return extraction.model_copy(update={"source": source})


def _norm(s):
    return " ".join(s.split()).casefold()


def verify_text_evidence(extraction, original_text):
    """For pasted text: keep only evidence that really appears in what the user pasted."""
    haystack = _norm(original_text)
    dropped = 0

    action = extraction.requested_action
    if action.evidence_quote and _norm(action.evidence_quote) not in haystack:
        if action.sender_asks_user:
            # We cannot show a request we cannot find. Fail rather than guess.
            raise AnalysisError(
                "The model's evidence did not match your message, so no result is shown. Please try again."
            )
        action = action.model_copy(update={"evidence_quote": None})

    signals = [s for s in extraction.signals if _norm(s.evidence_quote) in haystack]
    dropped += len(extraction.signals) - len(signals)

    urls = [u for u in extraction.urls if _norm(u) in haystack]
    dropped += len(extraction.urls) - len(urls)

    uncertainties = list(extraction.uncertainties)
    if dropped:
        uncertainties.append(
            f"{dropped} item(s) the model reported could not be found in your text and were left out."
        )
    return extraction.model_copy(update={
        "requested_action": action, "signals": signals, "urls": urls, "uncertainties": uncertainties,
    })


# ------------------------------------------------------------------ finish

def _finish(raw_text, tool_observations, source, original_text, user_context):
    extraction = validate_extraction(parse_model_json(raw_text), source)
    if source == "text":
        extraction = verify_text_evidence(extraction, original_text)
    else:
        extraction = extraction.model_copy(update={"uncertainties": extraction.uncertainties + [
            "Quotes were read from the image by the model and could not be checked automatically."
        ]})

    # Use what the model's inspect_url calls found; inspect any other URL locally (same safe function).
    seen = {o.url: o for o in tool_observations}
    observations = [seen.get(u.strip()) or inspect_url(u) for u in extraction.urls]

    result = assess(extraction, observations, user_context)
    return AnalysisOutcome(ok=True, mode="live", extraction=extraction,
                           url_observations=observations, result=result)


def _get_client(client, settings):
    settings = settings or load_settings()
    return client if client is not None else make_client(settings), settings


def analyze_text(text, user_context=None, client=None, settings=None):
    try:
        if not isinstance(text, str) or not text.strip():
            raise AnalysisError("Please paste a message to check.")
        if len(text) > MAX_TEXT_CHARS:
            raise AnalysisError(f"The message is longer than {MAX_TEXT_CHARS} characters. Please paste a shorter part.")
        client, settings = _get_client(client, settings)
        raw, observations = run_extraction(client, settings, build_text_content(text))
        return _finish(raw, observations, "text", text, user_context)
    except AnalysisError as e:
        return AnalysisOutcome(ok=False, error=str(e))


def analyze_image(image_bytes, user_context=None, client=None, settings=None):
    try:
        clean_bytes, media_type = prepare_image(image_bytes)  # validates and strips metadata
        client, settings = _get_client(client, settings)
        raw, observations = run_extraction(client, settings, build_image_content(clean_bytes, media_type))
        return _finish(raw, observations, "screenshot", None, user_context)
    except (AnalysisError, ImageError) as e:
        return AnalysisOutcome(ok=False, error=str(e))


# ---------------------------------------------------------------- sample mode

def load_sample_cases():
    return json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))["cases"]


def analyze_sample(case, user_context=None):
    """Demo mode: uses a hand-written synthetic extraction. No model, no key, no network."""
    extraction = Extraction.model_validate(case["extraction"])
    observations = [inspect_url(u) for u in extraction.urls]
    result = assess(extraction, observations, user_context)
    return AnalysisOutcome(ok=True, mode="sample", extraction=extraction,
                           url_observations=observations, result=result)
