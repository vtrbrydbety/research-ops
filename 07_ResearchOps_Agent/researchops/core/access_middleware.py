"""Fail-closed ASGI perimeter; forwarded headers require the original TCP peer."""

import ipaddress
import secrets
import sqlite3
from urllib.parse import urlsplit

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from researchops.core.access_context import AccessContext, current_access
from researchops.services.access_store import AccessError, digest

COOKIE_NAME = "__Host-researchops_session"
SESSION_PATH = "/api/v1/access/session"
EXCHANGE_PATH = "/api/v1/access/sessions"
PUBLIC_FILES = {
    "/mvp",
    "/mvp/",
    "/mvp/index.html",
    "/mvp/mvp-api.js",
    "/mvp/ui.js",
    "/mvp/access.js",
    "/mvp/access.css",
    "/mvp/styles.css",
}


def error_response(exc: AccessError):
    headers = {"Retry-After": str(exc.retry_after)} if exc.status in {429, 503} else {}
    return JSONResponse(
        {"error_code": exc.code, "message": str(exc), "details": [], "task_id": None},
        status_code=exc.status,
        headers=headers,
    )


class AccessMiddleware:
    def __init__(self, app, *, settings, store_provider):
        self.app, self.settings, self.store_provider = app, settings, store_provider

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or self.settings.deployment_mode == "local":
            return await self.app(scope, receive, send)
        from starlette.requests import Request

        config = self.settings
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        path, method = scope["path"], scope["method"]
        response_started = False

        async def secured_send(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                security_headers = {
                    "x-content-type-options": "nosniff",
                    "x-frame-options": "DENY",
                    "referrer-policy": "no-referrer",
                    "permissions-policy": "camera=(), microphone=(), geolocation=()",
                    "strict-transport-security": "max-age=31536000",
                    "content-security-policy": "default-src 'self'; script-src 'self'; "
                    "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; "
                    "font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
                    "form-action 'self'",
                    "cache-control": "no-store",
                }
                pairs = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.decode().lower() not in security_headers
                ]
                message["headers"] = pairs + [
                    (k.encode(), v.encode()) for k, v in security_headers.items()
                ]
            await send(message)

        marker = None
        try:
            origin_host = urlsplit(config.public_origin).netloc
            host = headers.get("host", "")
            allowed = {origin_host}
            if path == "/health":
                allowed |= {
                    "127.0.0.1",
                    f"127.0.0.1:{config.api_port}",
                    "localhost",
                    f"localhost:{config.api_port}",
                    f"[::1]:{config.api_port}",
                }
            if host not in allowed:
                raise AccessError("INVALID_HOST", "不允许的访问地址。", 400)
            body = bytearray()
            try:
                content_length = int(headers.get("content-length", "0"))
            except ValueError:
                raise AccessError("INVALID_REQUEST", "请求格式无效。", 400) from None
            if content_length < 0 or content_length > config.request_max_bytes:
                raise AccessError("REQUEST_TOO_LARGE", "请求内容过大。", 413)
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if len(body) > config.request_max_bytes:
                    raise AccessError("REQUEST_TOO_LARGE", "请求内容过大。", 413)
                if not message.get("more_body", False):
                    break
            sent = False

            async def replay():
                nonlocal sent
                if not sent:
                    sent = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            if method in {"GET", "HEAD"} and (path in PUBLIC_FILES or path == "/health"):
                return await self.app(scope, replay, secured_send)
            if path in {"/docs", "/redoc", "/openapi.json"}:
                raise AccessError("RESOURCE_NOT_FOUND", "资源不存在。", 404)
            store = self.store_provider()
            if path == EXCHANGE_PATH and method == "POST":
                if headers.get("origin") != config.public_origin:
                    raise AccessError("ORIGIN_REJECTED", "请求来源无效。", 403)
                if headers.get("content-type", "").split(";")[0].strip() != "application/json":
                    raise AccessError("INVALID_CONTENT_TYPE", "请使用 JSON 请求。", 415)
                peer = (scope.get("client") or ("unknown",))[0]
                address = peer
                if peer in config.trusted_proxy_ips:
                    forwarded = headers.get("cf-connecting-ip")
                    if forwarded:
                        try:
                            address = str(ipaddress.ip_address(forwarded))
                        except ValueError:
                            raise AccessError("INVALID_REQUEST", "请求格式无效。", 400) from None
                await run_in_threadpool(
                    store.rate_limit,
                    [
                        ("login:" + digest(address), config.login_ip_limit, 600),
                        ("login:*", config.login_global_limit, 60),
                    ],
                )
            else:
                request = Request(scope)
                session = await run_in_threadpool(
                    store.authenticate, request.cookies.get(COOKIE_NAME)
                )
                if method not in {"GET", "HEAD", "OPTIONS"}:
                    if headers.get("origin") != config.public_origin:
                        raise AccessError("ORIGIN_REJECTED", "请求来源无效。", 403)
                    if not secrets.compare_digest(
                        headers.get("x-csrf-token", "").encode("latin-1"),
                        session["csrf_token"].encode(),
                    ):
                        raise AccessError("CSRF_REJECTED", "会话校验失败，请重新进入。", 403)
                await run_in_threadpool(
                    store.rate_limit,
                    [
                        (
                            "business:" + session["principal_id"],
                            config.business_principal_limit,
                            60,
                        ),
                        ("business:*", config.business_global_limit, 60),
                    ],
                )
                scope.setdefault("state", {})["access_session"] = session
                marker = current_access.set(AccessContext(session["principal_id"], store))
            await self.app(scope, replay, secured_send)
        except AccessError as exc:
            await error_response(exc)(scope, receive, secured_send)
        except (sqlite3.Error, OSError, RuntimeError):
            if response_started:
                raise
            await error_response(AccessError("SECURITY_UNAVAILABLE", "服务暂时不可用。", 503))(
                scope, receive, secured_send
            )
        finally:
            if marker is not None:
                current_access.reset(marker)
