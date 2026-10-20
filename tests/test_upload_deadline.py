"""Synthetic slow transport exercises real multipart cleanup and admission recovery."""
import asyncio
import json
import pytest
from fastapi import FastAPI, File, UploadFile
from backend.security import AdmissionMiddleware, BodyLimitMiddleware


def application(timeout, rejects):
    app = FastAPI()

    @app.post('/api/inference/upload')
    async def upload(file: UploadFile = File(...)):
        try:
            return {'bytes': len(await file.read())}
        finally:
            await file.close()

    bounded = BodyLimitMiddleware(app, on_reject=lambda scope: rejects.append(True), body_timeout=timeout)
    return AdmissionMiddleware(bounded, capacity=1)


def scope(path='/api/inference/upload'):
    return {'type': 'http', 'method': 'POST', 'path': path, 'query_string': b'',
            'headers': [(b'content-type', b'multipart/form-data; boundary=fixture')],
            'scheme': 'http', 'server': ('test', 80), 'client': ('127.0.0.1', 1)}


PREFIX = b'--fixture\r\nContent-Disposition: form-data; name="file"; filename="unit.step"\r\nContent-Type: application/octet-stream\r\n\r\n'
SUFFIX = b'\r\n--fixture--\r\n'


def test_partial_spooled_upload_times_out_closes_file_and_releases_admission(monkeypatch):
    import starlette.formparsers as parsers
    created = []
    original = parsers.SpooledTemporaryFile

    def tracked(*args, **kwargs):
        file = original(*args, **kwargs)
        created.append(file)
        return file

    monkeypatch.setattr(parsers, 'SpooledTemporaryFile', tracked)

    async def scenario():
        rejects, messages = [], []
        app = application(.05, rejects)
        first = True

        async def receive():
            nonlocal first
            if first:
                first = False
                return {'type': 'http.request', 'body': PREFIX + b'x' * (2 * 1024 * 1024), 'more_body': True}
            await asyncio.Event().wait()

        async def send(message):
            messages.append(message)

        await asyncio.wait_for(app(scope(), receive, send), 2)
        assert messages[0]['status'] == 408
        assert 'deadline' in json.loads(messages[1]['body'])['detail']
        assert created and any(file._rolled for file in created)
        assert all(file.closed for file in created)
        assert rejects == [True] and app.active == 0
        messages.clear()

        async def complete():
            return {'type': 'http.request', 'body': PREFIX + b'valid fixture bytes' + SUFFIX, 'more_body': False}

        await app(scope(), complete, send)
        assert messages[0]['status'] == 200
        assert json.loads(messages[1]['body']) == {'bytes': 19}
        assert app.active == 0 and all(file.closed for file in created)
    asyncio.run(scenario())


def test_trickled_chunks_cannot_renew_absolute_deadline():
    async def scenario():
        rejects, messages = [], []
        app = application(.06, rejects)
        reads = 0

        async def receive():
            nonlocal reads
            await asyncio.sleep(.015)
            reads += 1
            return {'type': 'http.request', 'body': PREFIX if reads == 1 else b'x', 'more_body': True}

        async def send(message):
            messages.append(message)

        await asyncio.wait_for(app(scope(), receive, send), 1)
        assert messages[0]['status'] == 408
        assert 1 <= reads < 10 and rejects == [True] and app.active == 0
    asyncio.run(scenario())


def test_completed_body_does_not_limit_inference_execution():
    async def scenario():
        async def downstream(scope, receive, send):
            await receive()
            await asyncio.sleep(.04)
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        app = BodyLimitMiddleware(downstream, body_timeout=.01)
        async def receive():
            return {'type': 'http.request', 'body': b'complete', 'more_body': False}
        messages = []
        async def send(message):
            messages.append(message)
        await app(scope(), receive, send)
        assert messages[0]['status'] == 200
    asyncio.run(scenario())


@pytest.mark.parametrize('timeout', [0, -1, float('nan'), float('inf')])
def test_invalid_deadline_configuration(timeout):
    with pytest.raises(ValueError):
        BodyLimitMiddleware(None, body_timeout=timeout)


def test_disconnect_cancellation_releases_admission_without_timeout_rejection():
    async def scenario():
        rejects, messages = [], []
        app = application(1, rejects)
        waiting = asyncio.Event()
        async def receive():
            waiting.set()
            await asyncio.Event().wait()
        async def send(message):
            messages.append(message)
        task = asyncio.create_task(app(scope(), receive, send))
        await waiting.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert app.active == 0 and rejects == [] and messages == []
    asyncio.run(scenario())


def test_non_upload_routes_keep_their_existing_receive_behavior():
    async def scenario():
        async def downstream(scope, receive, send):
            await receive()
        async def receive():
            await asyncio.sleep(.02)
            return {'type': 'http.request', 'body': b'{}'}
        app = BodyLimitMiddleware(downstream, body_timeout=.001)
        await app(scope('/api/inference/sample'), receive, None)
    asyncio.run(scenario())


def test_expired_budget_rejects_even_an_immediately_available_chunk():
    from fastapi import HTTPException
    async def scenario():
        async def downstream(scope, receive, send):
            await asyncio.sleep(.02)
            await receive()
        async def receive():
            return {'type': 'http.request', 'body': b'buffered'}
        app = BodyLimitMiddleware(downstream, body_timeout=.001)
        with pytest.raises(HTTPException) as error:
            await app(scope(), receive, None)
        assert error.value.status_code == 408
    asyncio.run(scenario())
