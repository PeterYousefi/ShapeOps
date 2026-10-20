"""Validate the native worker boundary without renumbering parsed CAD faces."""
import math
from typing import Literal, TypedDict, cast

Surface = Literal["Planar", "Cylindrical", "Conical", "Spherical", "Toroidal", "Other"]


class GeometryFace(TypedDict):
    id: int
    surface: Surface
    area: float
    edges: int
    features: list[float]
    positions: list[float]


class Geometry(TypedDict):
    faces: list[GeometryFace]
    face_count: int
    edge_count: int
    volume: float
    bounds: list[float]


def number(value: object) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def integer(value: object, minimum: int, maximum: int | None = None) -> bool:
    return type(value) is int and value >= minimum and (maximum is None or value <= maximum)


def validate_geometry(value: object) -> Geometry:
    """Reject an inconsistent protocol result; retain original arrays and face IDs."""
    failure = "Invalid CAD worker geometry contract."
    if not isinstance(value, dict) or set(value) != {"faces", "face_count", "edge_count", "volume", "bounds"}:
        raise ValueError(failure)
    faces = value["faces"]
    bounds = value["bounds"]
    if (not integer(value["face_count"], 1, 600)
            or not isinstance(faces, list) or len(faces) != value["face_count"]
            or not integer(value["edge_count"], 0)
            or not number(value["volume"]) or value["volume"] < 0
            or not isinstance(bounds, list) or len(bounds) != 3
            or any(not number(v) or not 0 <= v <= 10000 for v in bounds)):
        raise ValueError(failure)
    total = 0
    for index, face in enumerate(faces):
        if not isinstance(face, dict) or set(face) != {"id", "surface", "area", "edges", "features", "positions"}:
            raise ValueError(failure)
        if (not integer(face["id"], 0) or face["id"] != index
                or face["surface"] not in ("Planar", "Cylindrical", "Conical", "Spherical", "Toroidal", "Other")
                or not number(face["area"]) or face["area"] < 0
                or not integer(face["edges"], 0)):
            raise ValueError(failure)
        features, positions = face["features"], face["positions"]
        if (not isinstance(features, list) or len(features) != 6
                or any(not number(v) or v < 0 for v in features)
                or not isinstance(positions, list) or not positions
                or len(positions) > 900000 or len(positions) % 9
                or any(not number(v) for v in positions)):
            raise ValueError(failure)
        total += len(positions)
        if total > 4500000:
            raise ValueError(failure)
    return cast(Geometry, value)
