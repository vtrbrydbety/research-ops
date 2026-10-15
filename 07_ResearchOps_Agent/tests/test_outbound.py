"""No network: verify destination pinning and original TLS identity at the transport."""

import socket
import ssl

import httpx
import pytest
from httpcore._backends.sync import SyncBackend

from researchops.core.outbound import PublicHTTPTransport, public_addresses


@pytest.mark.parametrize(
    "address", ["127.0.0.1", "10.1.1.1", "169.254.169.254", "::1", "fc00::1", "fe80::1"]
)
def test_forbids_non_public_destinations(monkeypatch, address):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [(2, 1, 6, "", (address, 443))])
    with pytest.raises(httpx.ConnectError):
        public_addresses("untrusted.test", 443)


def test_mixed_public_and_private_dns_is_denied(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **kw: [(2, 1, 6, "", ("1.1.1.1", 443)), (2, 1, 6, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(httpx.ConnectError):
        public_addresses("mixed.test", 443)


def test_numeric_connection_preserves_tls_hostname_and_host_header(monkeypatch):
    lookups, connections, writes, tls = [], [], [], []

    def dns(*args, **kwargs):
        lookups.append(args)
        return [(2, 1, 6, "", ("1.1.1.1" if len(lookups) == 1 else "127.0.0.1", 443))]

    class Stream:
        def read(self, max_bytes, timeout=None):
            return b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok"

        def write(self, buffer, timeout=None):
            writes.append(buffer)

        def close(self):
            pass

        def get_extra_info(self, info):
            return None

        def start_tls(self, ssl_context, server_hostname=None, timeout=None):
            tls.append((ssl_context, server_hostname))
            return self

    def connect(self, host, port, *args, **kwargs):
        connections.append((host, port))
        return Stream()

    monkeypatch.setattr(socket, "getaddrinfo", dns)
    monkeypatch.setattr(SyncBackend, "connect_tcp", connect)
    with httpx.Client(transport=PublicHTTPTransport()) as client:
        assert client.get("https://paper.example/").text == "ok"
    assert len(lookups) == 1
    assert connections == [("1.1.1.1", 443)]
    assert tls[0][1] == "paper.example"
    assert tls[0][0].verify_mode == ssl.CERT_REQUIRED
    assert tls[0][0].check_hostname is True
    assert b"Host: paper.example" in b"".join(writes)


def test_redirect_cannot_reach_private_origin(monkeypatch):
    def dns(host, *a, **kw):
        return [(2, 1, 6, "", ("127.0.0.1" if host == "internal.test" else "1.1.1.1", 80))]

    class Stream:
        def read(self, *args, **kwargs):
            return b"HTTP/1.1 302 Found\r\nLocation: http://internal.test/\r\nContent-Length: 0\r\n\r\n"

        def write(self, *args, **kwargs):
            pass

        def close(self):
            pass

        def get_extra_info(self, info):
            return None

    calls = []

    def connect(self, host, *args, **kwargs):
        calls.append(host)
        return Stream()

    monkeypatch.setattr(socket, "getaddrinfo", dns)
    monkeypatch.setattr(SyncBackend, "connect_tcp", connect)
    with httpx.Client(transport=PublicHTTPTransport(), follow_redirects=True) as client:
        with pytest.raises(httpx.ConnectError):
            client.get("http://public.test/")
    assert calls == ["1.1.1.1"]


@pytest.mark.parametrize("url", ["https://user:secret@public.test/", "https://public.test:8000/"])
def test_credentials_and_nonstandard_ports_are_rejected(url):
    with httpx.Client(transport=PublicHTTPTransport()) as client:
        with pytest.raises(httpx.UnsupportedProtocol):
            client.get(url)


def test_async_backend_pins_numeric_address(monkeypatch):
    import asyncio

    from httpcore._backends.auto import AutoBackend

    from researchops.core.outbound import VerifiedAsyncBackend

    connections = []
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *a, **kw: [(10, 1, 6, "", ("2606:4700:4700::1111", 443))]
    )

    async def connect(self, host, port, *args, **kwargs):
        connections.append((host, port))
        return "stream"

    monkeypatch.setattr(AutoBackend, "connect_tcp", connect)
    assert asyncio.run(VerifiedAsyncBackend().connect_tcp("public.example", 443)).stream == "stream"
    assert connections == [("2606:4700:4700::1111", 443)]


def test_response_byte_limit_without_content_length(monkeypatch):
    from researchops.core import outbound

    monkeypatch.setattr(outbound, "MAX_RESPONSE_BYTES", 4)
    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        lambda self, request: httpx.Response(200, stream=httpx.ByteStream(b"12345")),
    )
    with httpx.Client(transport=PublicHTTPTransport()) as client:
        with pytest.raises(httpx.ReadError, match="byte limit"):
            client.get("https://public.test/")


def test_compression_cannot_bypass_byte_limit(monkeypatch):
    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        lambda self, request: httpx.Response(
            200, headers={"Content-Encoding": "gzip"}, stream=httpx.ByteStream(b"compressed")
        ),
    )
    with httpx.Client(transport=PublicHTTPTransport()) as client:
        with pytest.raises(httpx.ReadError, match="Compressed"):
            client.get("https://public.test/")
