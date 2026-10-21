"""Verify actual CI inference -> Prometheus -> provisioned Grafana query flow."""
import json
import math
from pathlib import Path
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = 'http://127.0.0.1:18000'
GRAFANA = 'http://127.0.0.1:13000'


def request(url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=5) as response:
        return json.load(response)


def wait_for(function, seconds: int = 120):
    deadline = time.monotonic() + seconds
    while True:
        try:
            return function()
        except (URLError, ValueError, KeyError, AssertionError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)


def vector_value(payload: dict) -> float:
    if payload.get('status') != 'success' or payload.get('warnings'):
        raise ValueError('Prometheus query did not succeed cleanly')
    data = payload['data']
    rows = data['result']
    if data['resultType'] != 'vector' or len(rows) != 1:
        raise ValueError('Expected exactly one actual metric series')
    value = float(rows[0]['value'][1])
    if not math.isfinite(value):
        raise ValueError('Metric value must be finite')
    return value


def validate_dashboard(payload: dict, specification: dict) -> list[str]:
    dashboard = payload['dashboard']
    if dashboard['uid'] != specification['uid'] or not payload['meta']['provisioned']:
        raise ValueError('Expected the file-provisioned ShapeOps dashboard')
    actual = dashboard['panels']
    expected = specification['panels']
    if not expected or len(actual) != len(expected):
        raise ValueError('Dashboard panel coverage mismatch')
    queries = []
    for panel, reference in zip(actual, expected):
        if panel['datasource']['uid'] != 'prometheus' or panel['targets'] != reference['targets']:
            raise ValueError('Dashboard datasource or query mismatch')
        queries.extend(target['expr'] for target in panel['targets'])
    return queries


def main() -> None:
    wait_for(lambda: request(API + '/api/health'))
    health = wait_for(lambda: request(GRAFANA + '/api/health'))
    before = request(API + '/api/telemetry')
    inference = request(API + '/api/inference/sample', {'sample': 'flange', 'compare': True})
    after = request(API + '/api/telemetry')
    if inference['source'] != 'sample' or after['successful'] != before['successful'] + 1:
        raise ValueError('Real sample inference did not produce matching telemetry')
    specification = json.loads(Path('monitoring/dashboard.json').read_text())
    dashboard = wait_for(lambda: request(GRAFANA + '/api/dashboards/uid/' + specification['uid']))
    queries = validate_dashboard(dashboard, specification)
    expected = {
        'shapeops_inference_requests{outcome="success"}': float(after['successful']),
        'shapeops_inference_requests{outcome="failure"}': float(after['failed']),
        'shapeops_last_request_latency_ms': float(after['requests'][0]['latency']),
    }
    if set(queries) != set(expected):
        raise ValueError('Every dashboard query must have an actual telemetry expectation')
    values = {}
    for query in ['up{job="shapeops"}', *queries]:
        wanted = 1.0 if query.startswith('up{') else expected[query]
        def matching():
            payload = request(GRAFANA + '/api/datasources/proxy/uid/prometheus/api/v1/query?' + urlencode({'query': query}))
            value = vector_value(payload)
            if not math.isclose(value, wanted, abs_tol=1e-8):
                raise ValueError('Scraped value does not match actual API telemetry yet')
            return value
        values[query] = wait_for(matching, seconds=60)
    evidence = {'scope': 'CI smoke traffic only; not production telemetry',
                'grafana_version': health['version'], 'trace_id': inference['trace_id'],
                'dashboard_uid': dashboard['dashboard']['uid'], 'values': values,
                'verified_at': time.time()}
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/monitoring-runtime.json').write_text(json.dumps(evidence, indent=2, allow_nan=False))
    print('Actual inference, Prometheus scrape and all provisioned Grafana panel queries verified')


if __name__ == '__main__':
    main()
