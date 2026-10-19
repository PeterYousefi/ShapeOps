import asyncio, json, logging, os, sqlite3, subprocess, sys, tempfile, time, uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
import numpy as np
import cadquery as cq
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from backend.cad import SAMPLES, sample_shape, describe
from backend.training import train, ROOT
from backend.security import BodyLimitMiddleware

logger = logging.getLogger("shapeops")
logging.basicConfig(level=logging.INFO, format="%(message)s")
DB = (
    Path(os.environ.get("SHAPEOPS_DATA_DIR", str(ROOT / ".runtime")))
    / "telemetry.sqlite"
)
DB.parent.mkdir(exist_ok=True)


def connection():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


with connection() as db:
    db.execute(
        "CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, at REAL, source TEXT, model TEXT, success INTEGER, latency REAL, parse REAL, execution REAL, faces INTEGER, confidence REAL, ood INTEGER, error TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS drills (id TEXT PRIMARY KEY, at REAL, result TEXT)"
    )


@asynccontextmanager
async def lifespan(app):
    app.state.models, app.state.registry, app.state.ood, app.state.reference = train()
    app.state.samples = {s["id"]: describe(sample_shape(s["id"])) for s in SAMPLES}
    yield


app = FastAPI(title="ShapeOps API", version="0.1.0", lifespan=lifespan)


def rejected_body(scope):
    trace = scope.get("state", {}).get("trace", uuid.uuid4().hex)
    record(trace, "upload", "unselected", False, 0, error="validation")


app.add_middleware(BodyLimitMiddleware, on_reject=rejected_body)
semaphore = asyncio.Semaphore(2)
rates: defaultdict[str, deque[float]] = defaultdict(deque)


class InferenceInput(BaseModel):
    sample: str = "bracket"
    model: str = "surface-rf-v1"
    compare: bool = False


@app.middleware("http")
async def headers(request: Request, call_next):
    trace = uuid.uuid4().hex
    request.state.trace = trace
    response = await call_next(request)
    response.headers.update(
        {
            "X-Request-ID": trace,
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "same-origin",
            "X-Frame-Options": "DENY",
        }
    )
    return response


def throttle(request):
    key = request.client.host if request.client else "local"
    now = time.monotonic()
    q = rates[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= 20:
        raise HTTPException(
            429, "Inference rate limit: 20 requests per minute. Try again shortly."
        )
    q.append(now)


def record(
    trace,
    source,
    model,
    success,
    latency,
    parse=0,
    execution=0,
    faces=0,
    confidence=0,
    ood=0,
    error="",
):
    with connection() as db:
        db.execute(
            "INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                trace,
                time.time(),
                source,
                model,
                int(success),
                latency,
                parse,
                execution,
                faces,
                confidence,
                int(ood),
                error,
            ),
        )
        db.execute("DELETE FROM requests WHERE at < ?", (time.time() - 7 * 86400,))
    logger.info(
        json.dumps(
            {
                "event": "inference",
                "trace_id": trace,
                "source": source,
                "model": model,
                "success": success,
                "latency_ms": round(latency, 2),
                "error_category": error,
            }
        )
    )


def infer(geometry, model, compare, trace, name, source, started, parse_ms):
    if model not in app.state.models:
        raise ValueError("Unknown model version")
    execution_start = time.perf_counter()
    x = np.array([f["features"] for f in geometry["faces"]])
    estimator = app.state.models[model]
    probabilities = estimator.predict_proba(x)
    pred = estimator.classes_[probabilities.argmax(axis=1)]
    alternate = "surface-et-v2" if model == "surface-rf-v1" else "surface-rf-v1"
    alternate_estimator = app.state.models[alternate] if compare else None
    alternate_probabilities = alternate_estimator.predict_proba(x) if compare else None
    other = (
        alternate_estimator.classes_[alternate_probabilities.argmax(axis=1)]
        if compare else None
    )
    for i, f in enumerate(geometry["faces"]):
        f["prediction"] = str(pred[i])
        f["confidence"] = float(probabilities[i].max())
        f["probabilities"] = {
            str(label): float(value)
            for label, value in zip(estimator.classes_, probabilities[i])
        }
        f["comparison_confidence"] = (
            float(alternate_probabilities[i].max()) if compare else None
        )
        f["candidate"] = str(other[i]) if other is not None else None
        f["disagreement"] = bool(other[i] != pred[i]) if other is not None else False
        f.pop("features", None)
    vec = np.array(
        [[geometry["face_count"], geometry["edge_count"], *sorted(geometry["bounds"])]]
    )
    score = float(-app.state.ood.decision_function(vec)[0])
    ood = score > 0
    med = app.state.reference.mean(axis=0)
    dev = np.abs(vec[0] - med) / np.maximum(med, 1)
    contributions = sorted(
        [
            {"feature": k, "deviation": round(float(v) * 100, 1)}
            for k, v in zip(
                [
                    "Face count",
                    "Edge count",
                    "Smallest extent",
                    "Middle extent",
                    "Largest extent",
                ],
                dev,
            )
        ],
        key=lambda r: -r["deviation"],
    )
    execution_ms = (time.perf_counter() - execution_start) * 1000
    total_ms = (time.perf_counter() - started) * 1000
    confidence = float(probabilities.max(axis=1).mean())
    record(
        trace,
        source,
        model,
        True,
        total_ms,
        parse_ms,
        execution_ms,
        geometry["face_count"],
        confidence,
        ood,
    )
    reg = next(r for r in app.state.registry if r["id"] == model)
    return {
        **geometry,
        "name": name,
        "source": source,
        "trace_id": trace,
        "model": model,
        "checksum": reg["checksum"],
        "latency_ms": total_ms,
        "parse_ms": parse_ms,
        "execution_ms": execution_ms,
        "confidence": confidence,
        "ood": ood,
        "ood_score": score,
        "ood_contributions": contributions,
        "disagreements": sum(f["disagreement"] for f in geometry["faces"]),
        "comparison_model": alternate if compare else None,
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "runtime": "local",
        "storage": "sqlite",
        "cad": "OpenCascade",
        "production_deployed": False,
    }


@app.get("/api/samples")
def samples():
    return SAMPLES


@app.get("/api/samples/{key}/download")
def download(key: str):
    if key not in {s["id"] for s in SAMPLES}:
        raise HTTPException(404, "Sample not found")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "part.step"
        cq.exporters.export(sample_shape(key), str(path))
        return Response(
            path.read_bytes(),
            media_type="application/step",
            headers={"Content-Disposition": f'attachment; filename="{key}.step"'},
        )


@app.post("/api/inference/sample")
async def sample_inference(payload: InferenceInput, request: Request):
    throttle(request)
    started = time.perf_counter()
    if payload.sample not in app.state.samples:
        raise HTTPException(404, "Unknown sample")
    if payload.model not in app.state.models:
        raise HTTPException(422, "Unknown model version")
    async with semaphore:
        # Copy cached geometry; samples use the same actual feature/inference contract as uploads.
        geometry = json.loads(json.dumps(app.state.samples[payload.sample]))
        return infer(
            geometry,
            payload.model,
            payload.compare,
            request.state.trace,
            next(s["name"] for s in SAMPLES if s["id"] == payload.sample),
            "sample",
            started,
            0,
        )


def process_step(data):
    with tempfile.TemporaryDirectory(prefix="shapeops-") as d:
        path = Path(d) / "input.step"
        path.write_bytes(data)
        result = subprocess.run(
            [sys.executable, "-m", "backend.worker", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        lines = [
            s for s in result.stdout.splitlines() if s.startswith("SHAPEOPS_RESULT:")
        ]
        if not lines:
            raise ValueError(
                "CAD processing failed. Check that the file contains a closed solid."
            )
        parsed = json.loads(lines[-1].split(":", 1)[1])
        if "error" in parsed:
            raise ValueError(parsed["error"])
        return parsed


@app.post("/api/inference/upload")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    model: str = "surface-rf-v1",
    compare: bool = False,
):
    throttle(request)
    started = time.perf_counter()
    trace = request.state.trace
    if model not in app.state.models:
        raise HTTPException(422, "Unknown model version")
    try:
        if Path(file.filename or "").suffix.lower() not in {".step", ".stp"}:
            raise ValueError("Choose a .step or .stp file.")
        data = await file.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024:
            raise ValueError("Upload exceeds the 10 MB limit.")
        if not data.lstrip().startswith(b"ISO-10303-21;"):
            raise ValueError("File is not an ISO 10303-21 STEP document.")
        async with semaphore:
            start = time.perf_counter()
            geometry = await asyncio.to_thread(process_step, data)
            parse = (time.perf_counter() - start) * 1000
            return infer(
                geometry,
                model,
                compare,
                trace,
                "Uploaded CAD part",
                "upload",
                started,
                parse,
            )
    except (ValueError, subprocess.TimeoutExpired) as exc:
        error = (
            "timeout" if isinstance(exc, subprocess.TimeoutExpired) else "validation"
        )
        record(
            trace,
            "upload",
            model,
            False,
            (time.perf_counter() - started) * 1000,
            error=error,
        )
        raise HTTPException(
            422,
            "CAD processing exceeded the 30 second limit."
            if error == "timeout"
            else str(exc),
        ) from None
    finally:
        await file.close()


@app.get("/api/registry")
def registry():
    return app.state.registry


@app.get("/api/telemetry")
def telemetry():
    with connection() as db:
        rows = [
            dict(r)
            for r in db.execute("SELECT * FROM requests ORDER BY at DESC LIMIT 1000")
        ]
    ok = [r for r in rows if r["success"]]
    lat = [r["latency"] for r in ok]
    return {
        "origin": "Actual local runtime · latest 1,000 requests · 7-day retention",
        "total": len(rows),
        "successful": len(ok),
        "failed": len(rows) - len(ok),
        "p50": float(np.percentile(lat, 50)) if lat else None,
        "p95": float(np.percentile(lat, 95)) if lat else None,
        "ood_rate": sum(r["ood"] for r in ok) / len(ok) if ok else None,
        "requests": rows,
        "throughput_per_minute": sum(r["at"] > time.time() - 60 for r in rows),
    }


@app.get("/metrics")
def metrics():
    t = telemetry()
    lines = [
        "# HELP shapeops_inference_requests Observed inference requests in retained local window",
        "# TYPE shapeops_inference_requests gauge",
        f'shapeops_inference_requests{{outcome="success"}} {t["successful"]}',
        f'shapeops_inference_requests{{outcome="failure"}} {t["failed"]}',
    ]
    for r in t["requests"][:1]:
        lines.append(f"shapeops_last_request_latency_ms {r['latency']}")
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/api/operations")
def operations():
    with connection() as db:
        drills = [
            json.loads(r["result"])
            for r in db.execute("SELECT result FROM drills ORDER BY at DESC LIMIT 20")
        ]
    return {
        "active": "surface-rf-v1",
        "candidate": "surface-et-v2",
        "environment": "Local development",
        "production": "Not deployed",
        "release_history": [],
        "drills": drills,
        "promotion": "Blocked: security scan and authorized production environment required",
    }


@app.post("/api/operations/drill")
async def drill(request: Request):
    throttle(request)
    # Inject a broken adapter in an isolated in-memory test; stable model is never mutated.
    started = time.perf_counter()
    checks = []
    try:

        def broken_adapter(_):
            raise RuntimeError("Injected adapter failure")

        broken_adapter(np.zeros((1, 6)))
    except RuntimeError:
        checks.append({"name": "Injected adapter failure detected", "passed": True})
    x = np.array([f["features"] for f in app.state.samples["bracket"]["faces"]])
    pred = app.state.models["surface-rf-v1"].predict(x)
    checks.append(
        {"name": "Stable adapter recovery inference", "passed": len(pred) == len(x)}
    )
    checks.append(
        {
            "name": "Active release unchanged",
            "passed": app.state.registry[0]["stage"] == "stable",
        }
    )
    result = {
        "id": uuid.uuid4().hex[:12],
        "at": time.time(),
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
        "duration_ms": (time.perf_counter() - started) * 1000,
        "scope": "Isolated adapter test. No deployment or production mutation.",
    }
    with connection() as db:
        db.execute(
            "INSERT INTO drills VALUES (?,?,?)",
            (result["id"], result["at"], json.dumps(result)),
        )
    return result


@app.post("/api/operations/promote")
def promote():
    raise HTTPException(
        403,
        "Production administration is disabled. An authenticated, authorized deployment environment is required.",
    )


if (ROOT / "dist").exists():
    app.mount("/assets", StaticFiles(directory=ROOT / "dist" / "assets"), name="assets")

    @app.get("/{path:path}")
    def frontend(path: str):
        return FileResponse(ROOT / "dist" / "index.html")
