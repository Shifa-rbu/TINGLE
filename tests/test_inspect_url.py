import ast
import socket
from pathlib import Path

import pytest

from tools.inspect_url import MAX_URL_LENGTH, inspect_url


def test_normal_https_url_is_parsed_without_flags():
    obs = inspect_url("https://www.example.test/path?x=1")
    assert obs.accepted
    assert obs.scheme == "https"
    assert obs.hostname == "www.example.test"
    assert obs.flags == []


def test_https_observation_says_https_is_not_proof_of_safety():
    obs = inspect_url("https://example.test")
    assert any("does not mean the site is trustworthy" in o for o in obs.observations)


def test_plain_http_is_noted():
    obs = inspect_url("http://example.test")
    assert obs.accepted
    assert any("plain http" in o for o in obs.observations)


@pytest.mark.parametrize("url", [
    "https://bit.ly/abc123",
    "http://tinyurl.com/x",
    "https://www.t.co/x",
])
def test_known_shorteners_are_flagged(url):
    obs = inspect_url(url)
    assert obs.accepted
    assert any("link shortener" in f for f in obs.flags)


def test_ip_address_hostname_is_flagged():
    obs = inspect_url("http://192.168.0.1/login")
    assert obs.accepted
    assert any("IP address" in f for f in obs.flags)


def test_at_sign_trick_shows_real_host():
    obs = inspect_url("https://mybank.com@evil.example.test/login")
    assert obs.hostname == "evil.example.test"
    assert any("'@'" in f for f in obs.flags)


def test_punycode_unusual_port_and_many_subdomains_are_flagged():
    assert any("punycode" in f for f in inspect_url("https://xn--pple-43d.test").flags)
    assert any("unusual port" in f for f in inspect_url("https://example.test:8443/").flags)
    assert any("many parts" in f for f in inspect_url("https://a.b.c.d.example.test").flags)


def test_default_ports_are_not_flagged():
    assert inspect_url("https://example.test:443/").flags == []
    assert inspect_url("http://example.test:80/").flags == []


@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "file:///etc/passwd",
    "ftp://example.test/file",
    "data:text/html,<b>hi</b>",
    "mailto:someone@example.test",
])
def test_non_web_schemes_are_rejected(url):
    obs = inspect_url(url)
    assert not obs.accepted
    assert "http" in obs.rejected_reason


@pytest.mark.parametrize("text", [
    "example.com",              # URL-like text, but no scheme
    "www.example.com/offer",
    "not a url at all",
    "",
    "   ",
    "http://",                  # no hostname
    "https://exa mple.test",    # space inside
    "https://example.test:99999/",  # invalid port
    "http://[::1",              # broken IPv6 bracket
])
def test_malformed_or_url_like_text_is_rejected_without_crashing(text):
    obs = inspect_url(text)
    assert not obs.accepted
    assert obs.rejected_reason


def test_overlong_url_is_rejected_and_not_echoed_in_full():
    url = "https://example.test/" + "a" * (MAX_URL_LENGTH + 10)
    obs = inspect_url(url)
    assert not obs.accepted
    assert "longer than" in obs.rejected_reason
    assert len(obs.url) <= 100


@pytest.mark.parametrize("bad", [None, 123, ["https://example.test"], b"https://example.test"])
def test_non_string_input_is_rejected(bad):
    assert not inspect_url(bad).accepted


def test_inspect_url_never_touches_the_network(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    obs = inspect_url("https://bit.ly/abc")
    assert obs.accepted


def test_tool_source_imports_no_networking_modules():
    # Check real import statements (not words in comments or docstrings).
    source = (Path(__file__).parent.parent / "tools" / "inspect_url.py").read_text()
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module)
    assert imported <= {"ipaddress", "urllib.parse", "core.schemas"}
