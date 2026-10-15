"""Trusted per-request/operation context, copied explicitly into background execution."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from researchops.services.access_store import AccessStore


@dataclass(frozen=True)
class AccessContext:
    principal: str
    store: AccessStore
    operation: str | None = None


current_access: ContextVar[AccessContext | None] = ContextVar("researchops_access", default=None)


def authorize_resource(kind, resource):
    context = current_access.get()
    if context:
        context.store.authorize(kind, resource, context.principal)


def bind_resource(kind, resource):
    context = current_access.get()
    if context:
        context.store.bind(kind, resource, context.principal)


def check_operation():
    from researchops.services.access_store import AccessError

    context = current_access.get()
    if context:
        if not context.operation:
            raise AccessError("OPERATION_REQUIRED", "任务缺少执行授权。", 503)
        context.store.check_operation(context.operation)


def model_attempt(request_bytes):
    from researchops.services.access_store import AccessError

    context = current_access.get()
    if not context:
        return None
    if not context.operation:
        raise AccessError("OPERATION_REQUIRED", "任务缺少执行授权。", 503)
    return context.store.attempt(context.operation, request_bytes)
