"""Data shapes used by TINGLE. Pydantic checks them, so bad model output is rejected
instead of silently turning into a result."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# The three possible results (shown to the user exactly like this).
STOP = "STOP & VERIFY"
PAUSE = "PAUSE & VERIFY"
NO_STRONG = "NO STRONG WARNING SIGNALS FOUND"

ActionType = Literal[
    "none",
    "pay",
    "share_code",  # OTP / security code
    "share_password",
    "share_personal_details",
    "install_app",
    "install_remote_access",
    "click_link",
    "other",
]

SignalType = Literal[
    "urgency",
    "advance_fee",
    "payment_request",
    "credential_request",
    "remote_access",
    "link",
    "other",
]

MAX_URLS = 5


class RequestedAction(BaseModel):
    """What the message wants the reader to do."""

    model_config = ConfigDict(extra="forbid")

    type: ActionType = "none"
    # True only if the SENDER is asking the reader to do it.
    # "Never share your OTP" is NOT a request, so this must be False there.
    sender_asks_user: bool = False
    evidence_quote: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def check_request_has_evidence(self):
        if self.sender_asks_user:
            if self.type == "none":
                raise ValueError("sender_asks_user is True but action type is 'none'")
            if not (self.evidence_quote and self.evidence_quote.strip()):
                raise ValueError("a request must come with an evidence quote")
        return self


class Signal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: SignalType
    evidence_quote: str = Field(min_length=1, max_length=300)


class Extraction(BaseModel):
    """What the AI model reads out of a message or screenshot."""

    model_config = ConfigDict(extra="forbid")

    message_summary: str = Field(max_length=500)
    claimed_identity: str | None = Field(default=None, max_length=200)  # None = unknown
    requested_action: RequestedAction = Field(default_factory=RequestedAction)
    signals: list[Signal] = Field(default_factory=list, max_length=20)
    urls: list[str] = Field(default_factory=list, max_length=MAX_URLS)
    uncertainties: list[str] = Field(default_factory=list, max_length=10)
    # "screenshot" evidence is transcribed by the model, so the UI labels it that way.
    source: Literal["text", "screenshot"] = "text"


class UrlObservation(BaseModel):
    """What inspect_url found out by only reading the URL text. Not a verdict."""

    url: str  # shortened if it was oversized
    accepted: bool
    hostname: str | None = None
    scheme: str | None = None
    observations: list[str] = Field(default_factory=list)  # neutral facts
    flags: list[str] = Field(default_factory=list)  # reasons to verify the link
    rejected_reason: str | None = None


class Reason(BaseModel):
    """One displayed reason. Always carries its evidence."""

    text: str
    evidence: str  # a quote from the message, or a URL observation
    evidence_kind: Literal["quote", "url"]


class Result(BaseModel):
    state: Literal["STOP & VERIFY", "PAUSE & VERIFY", "NO STRONG WARNING SIGNALS FOUND"]
    reasons: list[Reason]  # what caused the warning (empty for NO STRONG)
    minor_notes: list[Reason]  # things noticed that did NOT cause a warning
    next_steps: list[str]
    note: str  # limitation reminder shown with every result


class AnalysisOutcome(BaseModel):
    """What the pipeline hands to the UI: either a result or an error, never both.
    An error is NEVER shown as a 'safe' answer."""

    ok: bool
    mode: Literal["live", "sample"] = "live"
    error: str | None = None
    extraction: Extraction | None = None
    url_observations: list[UrlObservation] = Field(default_factory=list)
    result: Result | None = None
