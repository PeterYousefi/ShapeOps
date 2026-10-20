"""Synthetic output fixtures exercise schema failures, not model performance."""
from copy import deepcopy
import pytest
from pydantic import ValidationError
from backend.responses import InferenceResult


def response():
    return {"faces": [{"id": 0, "surface": "Planar", "prediction": "Planar", "confidence": 1.0,
             "probabilities": {"Planar": 1.0}, "comparison_confidence": None, "area": 1.0,
             "edges": 3, "positions": [0.0] * 9, "candidate": None, "disagreement": False}],
            "face_count": 1, "edge_count": 3, "volume": 0.0, "bounds": [1.0, 1.0, 1.0],
            "name": "Schema fixture", "source": "sample", "trace_id": "a" * 32,
            "model": "primary", "checksum": "b" * 64, "latency_ms": 2.0, "parse_ms": 0.0,
            "execution_ms": 1.0, "confidence": 1.0, "ood": False, "ood_score": -1.0,
            "ood_contributions": [{"feature": "Face count", "deviation": 0.0}],
            "disagreements": 0, "comparison_model": None}


def test_valid_output_roundtrip_preserves_face_ids_and_comparison():
    payload = response()
    assert InferenceResult.model_validate(payload).model_dump() == payload
    compared = deepcopy(payload)
    compared["comparison_model"] = "alternate"
    compared["disagreements"] = 1
    compared["faces"][0].update(candidate="Cylindrical", comparison_confidence=.8, disagreement=True)
    assert InferenceResult.model_validate(compared).model_dump() == compared


@pytest.mark.parametrize("path,value", [
    (("face_count",), 2), (("confidence",), .5), (("ood_score",), float("nan")),
    (("ood",), True), (("disagreements",), 1), (("comparison_model",), "alternate"),
    (("source",), "production"), (("latency_ms",), -1.0),
    (("faces", 0, "id"), 3), (("faces", 0, "id"), True),
    (("faces", 0, "confidence"), 1.1), (("faces", 0, "probabilities"), {"Planar": .5}),
    (("faces", 0, "positions"), [0.0] * 10),
    (("faces", 0, "positions"), [float("inf")] * 9),
    (("faces", 0, "candidate"), "Cylindrical"), (("faces", 0, "features"), [0.0] * 6),
])
def test_inconsistent_nonfinite_or_internal_output_is_rejected(path, value):
    payload = response()
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        InferenceResult.model_validate(payload)
