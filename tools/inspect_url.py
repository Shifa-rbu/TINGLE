"""inspect_url: looks at the TEXT of a URL only.

It never opens the link. This file deliberately imports no networking module
(no socket, requests, urllib.request, http) and a test checks that.
The output is a list of neutral observations, not a safe/unsafe verdict.
"""

import ipaddress
from urllib.parse import urlsplit

from core.schemas import UrlObservation

MAX_URL_LENGTH = 2000

# Well-known URL shorteners. A short link hides where it really goes.
SHORTENER_HOSTS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly",
    "rb.gy", "ow.ly", "shorturl.at", "tiny.cc", "buff.ly",
}


def _reject(url, reason):
    shown = url[:100] if isinstance(url, str) else ""
    return UrlObservation(url=shown, accepted=False, rejected_reason=reason)


def inspect_url(url):
    """Return a UrlObservation for `url`. Never raises for bad input."""
    if not isinstance(url, str):
        return _reject(url, "not text")
    url = url.strip()
    if not url:
        return _reject(url, "empty")
    if len(url) > MAX_URL_LENGTH:
        return _reject(url, f"longer than {MAX_URL_LENGTH} characters")
    if any(ch.isspace() or ord(ch) < 32 for ch in url):
        return _reject(url, "contains spaces or control characters")

    try:
        parts = urlsplit(url)
        hostname = parts.hostname
        port = parts.port  # raises ValueError if the port is invalid
    except ValueError:
        return _reject(url, "malformed URL")

    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        return _reject(url, "only http and https links are inspected")
    if not hostname:
        return _reject(url, "no hostname found")

    observations = [f"Scheme: {scheme}", f"Real hostname: {hostname}"]
    flags = []

    if scheme == "https":
        observations.append("Uses https. This only means the connection is encrypted; it does not mean the site is trustworthy.")
    else:
        observations.append("Uses plain http (not encrypted).")

    bare_host = hostname[4:] if hostname.startswith("www.") else hostname
    if bare_host in SHORTENER_HOSTS:
        flags.append(f"{hostname} is a well-known link shortener, so the final destination is hidden")

    try:
        ipaddress.ip_address(hostname)
        flags.append("the hostname is a raw IP address instead of a name")
        is_ip = True
    except ValueError:
        is_ip = False

    if parts.username is not None or "@" in parts.netloc:
        flags.append(f"the link contains '@'; the part before it is not the real site (real host: {hostname})")

    if any(label.startswith("xn--") for label in hostname.split(".")):
        flags.append("the hostname uses punycode (xn--), which can disguise look-alike characters")

    if port is not None and port not in (80, 443):
        flags.append(f"the link uses an unusual port ({port})")

    if hostname.count(".") >= 4:
        flags.append("the hostname has many parts (subdomains), which can bury the real site name")

    if not is_ip and "." not in hostname:
        flags.append("the hostname has no dot, which is unusual for a public website")

    return UrlObservation(
        url=url,
        accepted=True,
        hostname=hostname,
        scheme=scheme,
        observations=observations,
        flags=flags,
    )
