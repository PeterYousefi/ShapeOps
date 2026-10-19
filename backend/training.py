"""Reproducible surface-classification baseline on owned procedural solids."""

import hashlib, json, subprocess, platform
from pathlib import Path
import numpy as np
import cadquery as cq
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    IsolationForest,
)
from sklearn.metrics import accuracy_score, f1_score, log_loss
import sklearn
import joblib
from backend.governance import evaluate_gates
from backend.cad import features, LABELS, describe, sample_shape

ROOT = Path(__file__).resolve().parents[1]


def train():
    rng = np.random.default_rng(42)
    x = []
    y = []
    groups = []
    for i in range(100):
        r = float(rng.uniform(2, 35))
        h = float(rng.uniform(5, 70))
        shapes = [
            cq.Solid.makeBox(r, h, r * 0.8),
            cq.Solid.makeCylinder(r, h),
            cq.Solid.makeCone(r, r * 0.3, h),
            cq.Solid.makeSphere(r),
            cq.Solid.makeTorus(r + 5, 2),
        ]
        for s in shapes:
            for f in s.Faces():
                label = LABELS.get(f.geomType(), "Other")
                if label == "Other":
                    continue
                x.append(features(f))
                y.append(label)
                groups.append(i)
    x = np.array(x)
    y = np.array(y)
    # Split by generated parameter set to avoid identical solid leakage.
    train_mask = np.array(groups) < 80
    test_mask = ~train_mask
    digest = hashlib.sha256(
        json.dumps(
            {"x": x.tolist(), "y": y.tolist(), "groups": groups}, sort_keys=True
        ).encode()
    ).hexdigest()
    models = {}
    records = []
    configs = [
        (
            "surface-rf-v1",
            "stable",
            RandomForestClassifier(
                n_estimators=24,
                max_depth=3,
                max_features=1.0,
                class_weight="balanced",
                random_state=42,
            ),
        ),
        (
            "surface-et-v2",
            "candidate",
            ExtraTreesClassifier(n_estimators=64, max_depth=12, random_state=42),
        ),
    ]
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        commit = "uncommitted"
    for name, stage, model in configs:
        model.fit(x[train_mask], y[train_mask])
        pred = model.predict(x[test_mask])
        # Hash a canonical representation of the actual trained trees, not a filename.
        trees = [
            {
                "nodes": {
                    field: t.tree_.__getstate__()["nodes"][field].tolist()
                    for field in t.tree_.__getstate__()["nodes"].dtype.names
                },
                "values": t.tree_.value.tolist(),
            }
            for t in model.estimators_
        ]
        canonical = json.dumps(trees, sort_keys=True).encode()
        sha = hashlib.sha256(canonical).hexdigest()
        package_dir = (
            Path(
                __import__("os").environ.get(
                    "SHAPEOPS_DATA_DIR", str(ROOT / ".runtime")
                )
            )
            / "models"
            / sha
        )
        package_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = package_dir / "trees.json"
        if artifact_path.exists() and artifact_path.read_bytes() != canonical:
            raise RuntimeError("Immutable artifact collision")
        artifact_path.write_bytes(canonical)
        joblib.dump(model, package_dir / "estimator.joblib")
        package_sha = hashlib.sha256(
            (package_dir / "estimator.joblib").read_bytes()
        ).hexdigest()
        record = {
            "id": name,
            "stage": stage,
            "framework": f"scikit-learn {sklearn.__version__}",
            "runtime": f"Python {platform.python_version()} · CPU",
            "algorithm": type(model).__name__,
            "parameters": model.get_params(),
            "checksum": sha,
            "package_checksum": package_sha,
            "heldout_log_loss": float(
                log_loss(
                    y[test_mask],
                    model.predict_proba(x[test_mask]),
                    labels=model.classes_,
                )
            ),
            "dataset_hash": digest,
            "license": "MIT (ShapeOps procedural data and training code)",
            "training_rows": int(train_mask.sum()),
            "evaluation_rows": int(test_mask.sum()),
            "accuracy": float(accuracy_score(y[test_mask], pred)),
            "macro_f1": float(f1_score(y[test_mask], pred, average="macro")),
            "git_commit": commit,
            "classes": model.classes_.tolist(),
            "features": [
                "min curvature",
                "max curvature",
                "min curvature range",
                "max curvature range",
                "area",
                "edge count",
            ],
            "limitations": "Analytic surface baseline on synthetic solids. Not manufacturing-feature segmentation. Probabilities are uncalibrated; synthetic held-out metrics do not establish performance on industrial CAD.",
            "gates": evaluate_gates(
                float(f1_score(y[test_mask], pred, average="macro")), True, True, False
            ),
        }
        (package_dir / "manifest.json").write_text(json.dumps(record, indent=2))
        models[name] = model
        records.append(record)
    reference = np.array(
        [
            [d["face_count"], d["edge_count"], *sorted(d["bounds"])]
            for d in [
                describe(sample_shape(s), False)
                for s in ["bracket", "flange", "housing", "shaft", "manifold"]
            ]
        ]
    )
    # Small procedural reference: screening only, no claim of production drift calibration.
    jitter = np.maximum(
        reference[rng.integers(0, 5, 250)] * (1 + rng.normal(0, 0.12, (250, 5))), 0.01
    )
    ood = IsolationForest(random_state=42, contamination=0.05).fit(jitter)
    report = {
        "seed": 42,
        "dataset_hash": digest,
        "models": records,
        "reference": reference.tolist(),
        "scope": "Owned procedural analytic CAD. Parameter-group held-out split.",
    }
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts" / "evaluation.json").write_text(json.dumps(report, indent=2))
    return models, records, ood, reference


if __name__ == "__main__":
    _, records, _, _ = train()
    print(
        json.dumps(
            [
                {
                    "id": r["id"],
                    "accuracy": r["accuracy"],
                    "macro_f1": r["macro_f1"],
                    "checksum": r["checksum"],
                }
                for r in records
            ],
            indent=2,
        )
    )
