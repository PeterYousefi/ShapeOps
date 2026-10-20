"""Transport and admission limits before multipart parsing/spooling."""

import asyncio

from fastapi import HTTPException
from starlette.responses import JSONResponse

MAX_BODY_BYTES = 10 * 1024 * 1024 + 64 * 1024  # bounded multipart envelope


class BodyLimitMiddleware:
    def __init__(self, app, on_reject=None):
        self.app = app
        self.on_reject = on_reject

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/api/inference/upload":
            await self.app(scope, receive, send)
            return
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
            declared = MAX_BODY_BYTES + 1
        if declared > MAX_BODY_BYTES or declared < 0:
            reject()
            await JSONResponse(
                {
                    "detail": "Upload body exceeds the 10 MB file limit and multipart allowance."
                },
                status_code=413,
            )(scope, receive, send)
            return
        received = 0

        async def bounded_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_BODY_BYTES:
                    reject()
                    raise HTTPException(
                        413,
                        "Upload body exceeds the 10 MB file limit and multipart allowance.",
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
