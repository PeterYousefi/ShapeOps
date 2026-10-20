"""Exercise overload without consuming request bodies or starting CAD workers."""
import asyncio
import pytest
from backend.security import AdmissionMiddleware


def test_admission_rejects_before_body_and_recovers():
    async def scenario():
        release = asyncio.Event()
        entered = asyncio.Queue()
        reads = 0

        async def receive():
            nonlocal reads
            reads += 1
            return {"type": "http.request", "body": b"upload"}

        async def downstream(scope, receive, send):
            await entered.put(True)
            await release.wait()

        responses = []

        async def send(message):
            responses.append(message)

        app = AdmissionMiddleware(downstream, capacity=2)
        scope = {"type": "http", "method": "POST", "path": "/api/inference/upload"}
        first = asyncio.create_task(app(scope, receive, send))
        second = asyncio.create_task(app(scope, receive, send))
        await entered.get()
        await entered.get()
        await app(scope, receive, send)
        assert reads == 0
        assert responses[0]["status"] == 503
        assert (b"retry-after", b"2") in responses[0]["headers"]
        # Read-only health remains available under inference overload.
        health = asyncio.create_task(app({**scope, "path": "/api/health"}, receive, send))
        await entered.get()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert app.active == 1
        release.set()
        await asyncio.gather(second, health)
        await app(scope, receive, send)
        assert app.active == 0
    asyncio.run(scenario())


def test_admission_releases_on_downstream_failure():
    async def scenario():
        async def fail(*args):
            raise RuntimeError("downstream")
        app = AdmissionMiddleware(fail, capacity=1)
        scope = {"type": "http", "method": "POST", "path": "/api/inference/sample"}
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await app(scope, None, None)
            assert app.active == 0
    asyncio.run(scenario())


def test_repeated_cancellation_keeps_native_worker_reserved():
    import threading
    from backend.security import run_worker

    async def scenario():
        started = threading.Event()
        release = threading.Event()

        def native():
            started.set()
            assert release.wait(5)
            raise ValueError("private native failure")

        task = asyncio.create_task(run_worker(native))
        try:
            while not started.is_set():
                await asyncio.sleep(0.001)
            for _ in range(2):
                task.cancel()
                await asyncio.sleep(0)
                assert not task.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            release.set()
    asyncio.run(scenario())
