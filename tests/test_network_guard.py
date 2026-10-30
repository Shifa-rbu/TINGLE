"""Checks the network guard in conftest.py: local loopback works, anything external is blocked.

Blocked calls raise before any real connection is attempted, so these tests never touch the network.
"""

import socket

import pytest

BLOCKED = "a test tried to use the network"


# ---- external access stays blocked -------------------------------------------

@pytest.mark.parametrize("address", [
    ("93.184.216.34", 80),   # a public IPv4 address
    ("2606:2800:220:1::1", 80),  # a public IPv6 address
    ("example.com", 443),    # a hostname
    ("10.0.0.5", 80),        # private LAN address: not loopback, so also blocked
])
def test_connecting_to_external_addresses_is_blocked(address):
    # The guard looks at the address before the operating system is involved, so a plain IPv4 socket
    # is enough here, even for the IPv6 address (and it works on machines without IPv6).
    with socket.socket() as s:
        with pytest.raises(AssertionError, match=BLOCKED):
            s.connect(address)
        with pytest.raises(AssertionError, match=BLOCKED):
            s.connect_ex(address)


def test_create_connection_to_external_host_is_blocked():
    with pytest.raises(AssertionError, match=BLOCKED):
        socket.create_connection(("example.com", 80), timeout=1)


@pytest.mark.parametrize("host", ["example.com", "api.anthropic.com", "93.184.216.34"])
def test_dns_lookup_of_external_hosts_is_blocked(host):
    with pytest.raises(AssertionError, match=BLOCKED):
        socket.getaddrinfo(host, 443)


def test_http_libraries_cannot_reach_out():
    import urllib.request
    with pytest.raises(Exception):
        urllib.request.urlopen("http://example.com", timeout=1)


# ---- local loopback works (what asyncio and Streamlit need) --------------------

def test_socketpair_works():
    a, b = socket.socketpair()
    with a, b:
        a.sendall(b"ping")
        assert b.recv(4) == b"ping"


def test_windows_style_fallback_socketpair_works():
    # On Windows, socket.socketpair() is this pure-Python version: it connects to 127.0.0.1.
    a, b = socket._fallback_socketpair()
    with a, b:
        a.sendall(b"pong")
        assert b.recv(4) == b"pong"


def test_loopback_connection_works():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with socket.create_connection(server.getsockname(), timeout=2) as client:
            conn, _ = server.accept()
            with conn:
                client.sendall(b"hi")
                assert conn.recv(2) == b"hi"


def test_asyncio_event_loop_can_be_created():
    import asyncio
    loop = asyncio.new_event_loop()
    loop.close()
