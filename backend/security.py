"""Transport limits apply before multipart parsing/spooling, including chunked bodies."""

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
