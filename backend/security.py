"""Transport and admission limits before multipart parsing/spooling."""

import asyncio
import math
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException
from starlette.responses import JSONResponse

MAX_JSON_BYTES = 64 * 1024
MAX_BODY_BYTES = 10 * 1024 * 1024 + 64 * 1024  # bounded multipart envelope


class BodyLimitMiddleware:
    def __init__(self, app, on_reject=None, body_timeout: float = 30):
        if not math.isfinite(body_timeout) or body_timeout <= 0:
            raise ValueError("Upload body deadline must be positive and finite")
        self.body_timeout = body_timeout
        self.app = app
        self.on_reject = on_reject

    async def __call__(self, scope, receive, send):
        upload = scope.get("path") == "/api/inference/upload"
        sample = scope.get("path") == "/api/inference/sample" and scope.get("method") == "POST"
        if scope["type"] != "http" or not (upload or sample):
            await self.app(scope, receive, send)
            return
        limit = MAX_BODY_BYTES if upload else MAX_JSON_BYTES
        size_detail = ("Upload body exceeds the 10 MB file limit and multipart allowance." if upload
                       else "Sample inference JSON body exceeds the 64 KiB limit.")
        timeout_detail = ("Upload body deadline exceeded. Retry the upload." if upload
                          else "Sample inference body deadline exceeded. Retry the request.")
        headers = dict(scope.get("headers", []))
        rejected = False

        def reject():
            nonlocal rejected
            if not rejected and self.on_reject:
                self.on_reject(scope)
            rejected = True

        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = limit + 1
        if declared > limit or declared < 0:
            reject()
            await JSONResponse(
                {
                    "detail": size_detail
                },
                status_code=413,
            )(scope, receive, send)
            return
        received = 0
        deadline = time.monotonic() + self.body_timeout

        async def bounded_receive():
            nonlocal received
            try:
                # One absolute body budget; small chunks cannot reset the clock.
                if time.monotonic() >= deadline:
                    raise TimeoutError
                async with asyncio.timeout_at(deadline):
                    message = await receive()
            except TimeoutError:
                reject()
                # The pinned multipart parser closes spools on stream exceptions.
                raise HTTPException(408, timeout_detail) from None
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    reject()
                    raise HTTPException(
                        413,
                        size_detail,
                    )
            return message

        await self.app(scope, bounded_receive, send)


class AdmissionMiddleware:
    """Per-process, zero-wait admission before body parsing; no client/IP storage."""

    PATHS = frozenset({
        "/api/inference/upload", "/api/inference/sample", "/api/operations/drill"
    })

    def __init__(self, app, capacity=4):
        self.app = app
        self.capacity = capacity
        self.active = 0

    async def __call__(self, scope, receive, send):
        if (scope["type"] != "http" or scope.get("method") != "POST"
                or scope["path"] not in self.PATHS):
            await self.app(scope, receive, send)
            return
        # No await between the check and reservation on the ASGI event loop.
        if self.active >= self.capacity:
            await JSONResponse(
                {"detail": "Inference capacity is busy. Retry shortly."},
                status_code=503, headers={"Retry-After": "2"},
            )(scope, receive, send)
            return
        self.active += 1
        try:
            await self.app(scope, receive, send)
        finally:
            self.active -= 1


async def run_worker(function, *args):
    """Keep the caller alive until its bounded thread exits, even on repeated cancel."""
    task = asyncio.create_task(asyncio.to_thread(function, *args))
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            break
    if cancelled:
        # Retrieve exceptions without exposing native diagnostics or orphaning work.
        if not task.cancelled():
            task.exception()
        raise asyncio.CancelledError
    return task.result()


class RateLimitMiddleware:
    """Per-process rolling-window throttle before admission or body consumption."""

    def __init__(self, app, limit: int = 20, window: int = 60,
                 max_clients: int = 4096, clock: Callable[[], float] = time.monotonic) -> None:
        if min(limit, window, max_clients) < 1:
            raise ValueError("Rate-limit budgets must be positive")
        self.app = app
        self.limit = limit
        self.window = window
        self.max_clients = max_clients
        self.clock = clock
        self.clients: dict[str, deque[float]] = {}

    async def __call__(self, scope, receive, send):
        if (scope["type"] != "http" or scope.get("method") != "POST"
                or scope["path"] not in AdmissionMiddleware.PATHS):
            await self.app(scope, receive, send)
            return
        now = self.clock()
        cutoff = now - self.window
        # Bound storage even when many distinct peers attempt requests. Never evict
        # an active peer to admit a new one, which would reset abuse history.
        for peer, history in list(self.clients.items()):
            if history[-1] <= cutoff:
                del self.clients[peer]
        client = scope.get("client")
        key = client[0] if client else "local"
        history = self.clients.get(key)
        if history is None:
            if len(self.clients) >= self.max_clients:
                await JSONResponse(
                    {"detail": "Local rate-limit capacity is busy. Retry shortly."},
                    status_code=503, headers={"Retry-After": str(self.window)},
                )(scope, receive, send)
                return
            history = self.clients[key] = deque()
        while history and history[0] <= cutoff:
            history.popleft()
        if len(history) >= self.limit:
            retry = max(1, math.ceil(history[0] + self.window - now))
            await JSONResponse(
                {"detail": f"Inference rate limit: {self.limit} requests per {self.window} seconds. Try again shortly."},
                status_code=429, headers={"Retry-After": str(retry)},
            )(scope, receive, send)
            return
        # Check and record without yielding; all attempted protected POSTs count,
        # including invalid bodies and admission overloads. Forwarded headers do
        # not select the key here; trusted proxy policy belongs to the ASGI server.
        history.append(now)
        await self.app(scope, receive, send)
