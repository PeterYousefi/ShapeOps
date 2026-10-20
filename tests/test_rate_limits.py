import asyncio
from backend.security import RateLimitMiddleware


def test_rolling_window_rejects_before_receive_and_recovers():
    async def scenario():
        clock = [100.0]
        consumed = []
        messages = []

        async def inner(scope, receive, send):
            consumed.append(await receive())

        async def receive():
            return {"type": "http.request", "body": b"multipart body"}

        async def send(message):
            messages.append(message)

        app = RateLimitMiddleware(inner, clock=lambda: clock[0])
        scope = {"type": "http", "method": "POST", "path": "/api/inference/upload", "client": ("peer", 1)}
        for _ in range(20):
            await app(scope, receive, send)
        clock[0] = 100.1
        await app(scope, receive, send)
        assert len(consumed) == 20
        assert messages[0]["status"] == 429
        assert (b"retry-after", b"60") in messages[0]["headers"]
        # Spoofed forwarded headers do not reset the peer's rate history.
        await app({**scope, "headers": [(b"x-forwarded-for", b"new-peer")]}, receive, send)
        assert len(consumed) == 20
        clock[0] = 160.0
        await app(scope, receive, send)
        assert len(consumed) == 21
        assert len(app.clients["peer"]) == 1
    asyncio.run(scenario())


def test_bounded_peer_map_fails_closed_and_expires_idle_peers():
    async def scenario():
        now = [0.0]
        calls = []
        messages = []

        async def inner(scope, receive, send):
            calls.append(scope["path"])

        async def send(message):
            messages.append(message)

        app = RateLimitMiddleware(inner, max_clients=2, clock=lambda: now[0])
        scope = {"type": "http", "method": "POST", "path": "/api/inference/sample"}
        for peer in ("a", "b", "c"):
            await app({**scope, "client": (peer, 1)}, None, send)
        assert len(app.clients) == 2 and set(app.clients) == {"a", "b"}
        assert len(calls) == 2 and messages[0]["status"] == 503
        # Existing peers and unprotected health reads still work at map capacity.
        await app({**scope, "client": ("a", 2)}, None, send)
        await app({**scope, "path": "/api/health", "method": "GET"}, None, send)
        assert len(calls) == 4
        now[0] = 60
        await app({**scope, "client": ("c", 1)}, None, send)
        assert set(app.clients) == {"c"}
    asyncio.run(scenario())


def test_all_protected_routes_share_limit_and_failed_requests_count():
    async def scenario():
        calls = []
        messages = []

        async def inner(scope, receive, send):
            calls.append(scope["path"])
            raise ValueError("invalid body")

        async def send(message):
            messages.append(message)

        app = RateLimitMiddleware(inner, limit=2)
        scope = {"type": "http", "method": "POST"}
        for path in ("/api/inference/sample", "/api/operations/drill"):
            try:
                await app({**scope, "path": path}, None, send)
            except ValueError:
                pass
        await app({**scope, "path": "/api/inference/upload"}, None, send)
        assert len(calls) == 2 and messages[0]["status"] == 429
        assert len(app.clients["local"]) == 2
    asyncio.run(scenario())
