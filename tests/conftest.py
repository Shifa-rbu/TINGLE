import ipaddress
import socket

import pytest

# Keep references to the real functions so the guard can pass local calls through.
_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_create_connection = socket.create_connection
_real_getaddrinfo = socket.getaddrinfo


def _is_local(host):
    """True only for this computer itself: localhost, 127.x.x.x or ::1."""
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(str(host).split("%")[0]).is_loopback
    except ValueError:
        return False  # any other hostname or address is external


def _address_is_local(address):
    if isinstance(address, (str, bytes)):  # a Unix socket path: never leaves this computer
        return True
    return _is_local(address[0])


def _blocked():
    raise AssertionError("a test tried to use the network")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Every test runs with external networking blocked: no outside connections or DNS lookups.

    Loopback (127.0.0.1 / ::1 / localhost) stays allowed, because asyncio and Streamlit's test
    harness need it. On Windows, socket.socketpair() works by connecting to 127.0.0.1.
    """
    def connect(self, address):
        if not _address_is_local(address):
            _blocked()
        return _real_connect(self, address)

    def connect_ex(self, address):
        if not _address_is_local(address):
            _blocked()
        return _real_connect_ex(self, address)

    def create_connection(address, *args, **kwargs):
        if not _is_local(address[0]):
            _blocked()
        return _real_create_connection(address, *args, **kwargs)

    def getaddrinfo(host, *args, **kwargs):
        if host is not None and not _is_local(host):
            _blocked()
        return _real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
