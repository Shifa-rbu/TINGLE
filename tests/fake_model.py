"""A fake stand-in for the Anthropic client, so tests need no key and no network."""

import json
from types import SimpleNamespace as NS

SETTINGS = {"provider": "anthropic", "api_key": "placeholder-not-a-real-key",
            "model": "test-model", "timeout": 5.0, "max_tokens": 100}


def text_response(text):
    return NS(stop_reason="end_turn", content=[NS(type="text", text=text)])


def tool_response(*calls):
    """calls = (tool_name, input_dict) pairs the fake model 'asks' for."""
    blocks = [NS(type="tool_use", id=f"toolu_{i}", name=n, input=inp) for i, (n, inp) in enumerate(calls)]
    return NS(stop_reason="tool_use", content=blocks)


def stop_response(reason):
    return NS(stop_reason=reason, content=[])


def extraction_json(**overrides):
    data = {
        "message_summary": "A test message.",
        "claimed_identity": None,
        "requested_action": {"type": "none", "sender_asks_user": False, "evidence_quote": None},
        "signals": [],
        "urls": [],
        "uncertainties": [],
    }
    data.update(overrides)
    return json.dumps(data)


class FakeClient:
    """Returns the queued responses in order. A queued Exception is raised instead."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.messages = self  # so client.messages.create(...) works

    def create(self, **kwargs):
        kwargs["messages"] = list(kwargs["messages"])  # snapshot (the real list keeps growing)
        self.calls.append(kwargs)
        assert self.responses, "the fake model was called more times than expected"
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
