"""Public-only HTTP transport: verify DNS and connect to the verified numeric address.

TLS remains owned by httpcore, which retains the original hostname for SNI and
certificate verification. No process-global DNS patching or TLS bypass is used.
The backend integration is pinned to the tested httpx/httpcore versions.
"""

import ipaddress
import socket

import anyio
import httpx
from httpcore._backends.auto import AutoBackend
from httpcore._backends.sync import SyncBackend

from researchops.core.access_context import check_operation, current_access
from researchops.core.config import get_settings

MAX_RESPONSE_BYTES = 4 * 1024 * 1024


def bounded_timeout(timeout):
    context = current_access.get()
    if not context or not context.operation:
        return timeout
    remaining = context.store.check_operation(context.operation)
    return min(timeout, remaining) if timeout is not None else remaining


class DeadlineStream:
    def __init__(self, stream):
        self.stream = stream

    def read(self, max_bytes, timeout=None):
        return self.stream.read(max_bytes, timeout=bounded_timeout(timeout))

    def write(self, buffer, timeout=None):
        return self.stream.write(buffer, timeout=bounded_timeout(timeout))

    def close(self):
        self.stream.close()

    def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        return DeadlineStream(
            self.stream.start_tls(ssl_context, server_hostname, timeout=bounded_timeout(timeout))
        )

    def get_extra_info(self, info):
        return self.stream.get_extra_info(info)


class AsyncDeadlineStream:
    def __init__(self, stream):
        self.stream = stream

    async def read(self, max_bytes, timeout=None):
        return await self.stream.read(max_bytes, timeout=bounded_timeout(timeout))

    async def write(self, buffer, timeout=None):
        return await self.stream.write(buffer, timeout=bounded_timeout(timeout))

    async def aclose(self):
        await self.stream.aclose()

    async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        return AsyncDeadlineStream(
            await self.stream.start_tls(
                ssl_context, server_hostname, timeout=bounded_timeout(timeout)
            )
        )

    def get_extra_info(self, info):
        return self.stream.get_extra_info(info)


class BoundedStream(httpx.SyncByteStream):
    def __init__(self, stream):
        self.stream = stream

    def __iter__(self):
        size = 0
        for chunk in self.stream:
            context = current_access.get()
            if context and context.operation:
                check_operation()
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                raise httpx.ReadError("Outbound response exceeds the byte limit")
            yield chunk

    def close(self):
        self.stream.close()


class BoundedAsyncStream(httpx.AsyncByteStream):
    def __init__(self, stream):
        self.stream = stream

    async def __aiter__(self):
        size = 0
        async for chunk in self.stream:
            context = current_access.get()
            if context and context.operation:
                check_operation()
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                raise httpx.ReadError("Outbound response exceeds the byte limit")
            yield chunk

    async def aclose(self):
        await self.stream.aclose()


def public_addresses(host: str, port: int):
    if port not in {80, 443}:
        raise httpx.ConnectError("Outbound port is not allowed")
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addresses = list(dict.fromkeys(item[4][0] for item in records))
        if not addresses or any(
            not ipaddress.ip_address(address).is_global for address in addresses
        ):
            raise httpx.ConnectError("Outbound destination is not public")
    except (socket.gaierror, ValueError) as exc:
        raise httpx.ConnectError("Outbound destination could not be validated") from exc
    return addresses


def validate_request(request):
    if request.url.scheme not in {"http", "https"} or request.url.username or request.url.password:
        raise httpx.UnsupportedProtocol("Outbound URL is not allowed")
    if request.url.port not in {None, 80, 443}:
        raise httpx.UnsupportedProtocol("Outbound port is not allowed")
    context = current_access.get()
    if context and context.operation:
        check_operation()
    # Keep the transport byte cap meaningful; never expand an unbounded compressed body.
    request.headers["Accept-Encoding"] = "identity"


class VerifiedSyncBackend(SyncBackend):
    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        addresses = public_addresses(host, port)
        # Numeric destination avoids a second hostname lookup (DNS rebinding).
        return DeadlineStream(
            super().connect_tcp(
                addresses[0], port, bounded_timeout(timeout), local_address, socket_options
            )
        )


class VerifiedAsyncBackend(AutoBackend):
    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        addresses = await anyio.to_thread.run_sync(public_addresses, host, port)
        return AsyncDeadlineStream(
            await super().connect_tcp(
                addresses[0], port, bounded_timeout(timeout), local_address, socket_options
            )
        )


class PublicHTTPTransport(httpx.HTTPTransport):
    def __init__(self):
        super().__init__(trust_env=False, retries=0)
        self._pool._network_backend = VerifiedSyncBackend()

    def handle_request(self, request):
        validate_request(request)
        response = super().handle_request(request)
        if response.headers.get("content-encoding", "identity").lower() != "identity":
            response.close()
            raise httpx.ReadError("Compressed outbound responses are not allowed")
        response.stream = BoundedStream(response.stream)
        return response


class PublicAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    def __init__(self):
        super().__init__(trust_env=False, retries=0)
        self._pool._network_backend = VerifiedAsyncBackend()

    async def handle_async_request(self, request):
        validate_request(request)
        response = await super().handle_async_request(request)
        if response.headers.get("content-encoding", "identity").lower() != "identity":
            await response.aclose()
            raise httpx.ReadError("Compressed outbound responses are not allowed")
        response.stream = BoundedAsyncStream(response.stream)
        return response


def outbound_client(**kwargs):
    if get_settings().deployment_mode == "public":
        if kwargs.get("proxy"):
            raise ValueError("公网出站策略不允许代理绕过已验证的目标连接")
        kwargs.pop("proxy", None)
        kwargs["trust_env"] = False
        kwargs["transport"] = PublicHTTPTransport()
        kwargs["follow_redirects"] = False
    return httpx.Client(**kwargs)


def outbound_async_client(**kwargs):
    if get_settings().deployment_mode == "public":
        if kwargs.get("proxy"):
            raise ValueError("公网出站策略不允许代理绕过已验证的目标连接")
        kwargs.pop("proxy", None)
        kwargs["trust_env"] = False
        kwargs["transport"] = PublicAsyncHTTPTransport()
        kwargs["follow_redirects"] = False
    return httpx.AsyncClient(**kwargs)
