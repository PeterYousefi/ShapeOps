"""Protocol fixtures are synthetic validation inputs, not inference results."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from backend.contracts import validate_geometry


def geometry():
    return {"faces": [{"id": 0, "surface": "Planar", "area": 1.0, "edges": 3,
                       "features": [0, 0, 0, 0, 1, 3],
                       "positions": [0, 0, 0, 1, 0, 0, 0, 1, 0]}],
            "face_count": 1, "edge_count": 3, "volume": 0, "bounds": [1, 1, .001]}


def test_preserves_original_face_arrays_and_allows_rounded_zero_volume():
    source = geometry()
    assert validate_geometry(source) is source
    assert validate_geometry(source)["faces"][0] is source["faces"][0]


@pytest.mark.parametrize("path,replacement", [
    (("face_count",), 2), (("face_count",), True), (("face_count",), 601),
    (("edge_count",), -1), (("volume",), float("nan")),
    (("bounds",), [1, 2]), (("bounds",), [1, 2, 10001]),
    (("bounds",), [1, 2, float("inf")]), (("faces",), []),
    (("faces", 0, "id"), 1), (("faces", 0, "id"), False),
    (("faces", 0, "surface"), "invented"), (("faces", 0, "area"), -1),
    (("faces", 0, "edges"), 3.2), (("faces", 0, "features"), [0] * 5),
    (("faces", 0, "features"), [0, 0, 0, 0, float("inf"), 1]),
    (("faces", 0, "positions"), []), (("faces", 0, "positions"), [0] * 8),
    (("faces", 0, "positions"), [0] * 8 + [True]),
    (("faces", 0, "positions"), [0] * 8 + [10 ** 1000]),
])
def test_rejects_inconsistent_or_nonfinite_geometry(path, replacement):
    source = geometry()
    target = source
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    with pytest.raises(ValueError, match="geometry contract"):
        validate_geometry(source)


def test_rejects_extra_fields_missing_fields_duplicate_ids_and_mesh_budget():
    for source in ({}, {**geometry(), "private": "unexpected"}, []):
        with pytest.raises(ValueError):
            validate_geometry(source)
    source = geometry()
    source["faces"].append(deepcopy(source["faces"][0]))
    source["face_count"] = 2
    with pytest.raises(ValueError):
        validate_geometry(source)
    source = geometry()
    source["faces"][0]["positions"] = [0] * 900009
    with pytest.raises(ValueError):
        validate_geometry(source)
    source["faces"] = [deepcopy(source["faces"][0]) for _ in range(6)]
    source["face_count"] = 6
    for index, face in enumerate(source["faces"]):
        face["id"] = index
        face["positions"] = [0] * 900000
    with pytest.raises(ValueError):
        validate_geometry(source)


def test_parent_rejects_invalid_contract_and_cleans_temp_files(monkeypatch):
    import backend.app as module
    directories = []

    def run(command, **options):
        output = Path(command[-1])
        directories.append(output.parent)
        invalid = geometry()
        invalid["faces"][0]["id"] = 8
        output.write_text(json.dumps(invalid))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", run)
    with pytest.raises(ValueError, match="resource limits"):
        module.process_step(b"ISO-10303-21;")
    assert directories and all(not path.exists() for path in directories)
