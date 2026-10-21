"""Synthetic transport verifies real JSON parsing limits without CAD workers."""
import asyncio
import json
import pytest
from fastapi import FastAPI
from backend.security import AdmissionMiddleware, BodyLimitMiddleware, MAX_JSON_BYTES


@pytest.mark.parametrize('kind', ['declared', 'chunked', 'stalled', 'valid'])
def test_sample_json_body_limits_and_admission_recovery(kind):
    async def scenario():
        app = FastAPI()
        @app.post('/api/inference/sample')
        async def sample(payload: dict):
            return payload
        rejects, messages = [], []
        middleware = AdmissionMiddleware(BodyLimitMiddleware(app, body_timeout=.03, on_reject=lambda scope: rejects.append(True)), capacity=1)
        reads = 0
        scope = {'type': 'http', 'method': 'POST', 'path': '/api/inference/sample', 'query_string': b'',
                 'headers': [(b'content-type', b'application/json')], 'scheme': 'http',
                 'server': ('test', 80), 'client': ('127.0.0.1', 1)}
        if kind == 'declared':
            scope['headers'].append((b'content-length', str(MAX_JSON_BYTES + 1).encode()))
        async def receive():
            nonlocal reads
            reads += 1
            if kind == 'stalled':
                await asyncio.Event().wait()
            if kind == 'chunked':
                return {'type': 'http.request', 'body': b'x' * (MAX_JSON_BYTES // 2 + 1), 'more_body': reads == 1}
            return {'type': 'http.request', 'body': b'{"sample":"flange"}', 'more_body': False}
        async def send(message):
            messages.append(message)
        await asyncio.wait_for(middleware(scope, receive, send), 2)
        assert messages[0]['status'] == {'declared': 413, 'chunked': 413, 'stalled': 408, 'valid': 200}[kind]
        assert rejects == ([] if kind == 'valid' else [True])
        assert middleware.active == 0
        if kind == 'declared':
            assert reads == 0
        if kind == 'valid':
            assert json.loads(messages[1]['body']) == {'sample': 'flange'}
    asyncio.run(scenario())
