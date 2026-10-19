"""OpenCascade geometry contract: face order is shared by features and tessellation."""

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepLProp import BRepLProp_SLProps

LABELS = {
    "PLANE": "Planar",
    "CYLINDER": "Cylindrical",
    "CONE": "Conical",
    "SPHERE": "Spherical",
    "TORUS": "Toroidal",
}
SAMPLES = [
    {
        "id": "bracket",
        "name": "Mounting bracket",
        "description": "Pocketed plate · through holes · filleted edges",
    },
    {
        "id": "flange",
        "name": "Bearing flange",
        "description": "Circular housing · bolt pattern · center bore",
    },
    {
        "id": "housing",
        "name": "Sensor housing",
        "description": "Thin-wall enclosure · rounded corners",
    },
    {
        "id": "shaft",
        "name": "Stepped shaft",
        "description": "Turned part · concentric shoulders",
    },
    {
        "id": "manifold",
        "name": "Fluid manifold",
        "description": "Cross-drilled block · multiple ports",
    },
]


def sample_shape(key):
    if key == "bracket":
        s = cq.Workplane("XY").box(100, 72, 18).edges("|Z").fillet(7)
        s = s.faces(">Z").workplane().rect(52, 34).cutBlind(-10)
        s = (
            s.faces(">Z")
            .workplane()
            .pushPoints([(-38, -23), (-38, 23), (38, -23), (38, 23)])
            .hole(10)
        )
        return s.val()
    if key == "flange":
        s = (
            cq.Workplane("XY")
            .circle(40)
            .extrude(10)
            .faces(">Z")
            .workplane()
            .circle(23)
            .extrude(22)
        )
        s = s.faces(">Z").workplane().hole(26)
        for x, y in [(-29, 0), (29, 0), (0, 29), (0, -29)]:
            s = s.cut(cq.Workplane("XY").center(x, y).circle(4).extrude(10))
        return s.val()
    if key == "housing":
        return (
            cq.Workplane("XY")
            .box(85, 60, 35)
            .edges("|Z")
            .fillet(8)
            .faces(">Z")
            .shell(-4)
            .val()
        )
    if key == "shaft":
        return (
            cq.Workplane("XY")
            .circle(22)
            .extrude(14)
            .faces(">Z")
            .workplane()
            .circle(14)
            .extrude(40)
            .faces(">Z")
            .workplane()
            .circle(9)
            .extrude(20)
            .val()
        )
    if key == "manifold":
        return (
            cq.Workplane("XY")
            .box(78, 55, 40)
            .faces(">Z")
            .workplane()
            .pushPoints([(-22, 0), (0, 0), (22, 0)])
            .hole(12)
            .faces(">Y")
            .workplane()
            .hole(14)
            .val()
        )
    raise ValueError("Unknown sample model")


def features(face):
    """Numerical curvature descriptors, no surface-type labels as input."""
    surf = BRepAdaptor_Surface(face.wrapped)
    u0, u1, v0, v1 = (
        surf.FirstUParameter(),
        surf.LastUParameter(),
        surf.FirstVParameter(),
        surf.LastVParameter(),
    )
    vals = []
    for t in [0.25, 0.5, 0.75]:
        p = BRepLProp_SLProps(surf, u0 + (u1 - u0) * t, v0 + (v1 - v0) * t, 2, 1e-6)
        if p.IsCurvatureDefined():
            a, b = sorted([abs(p.MinCurvature()), abs(p.MaxCurvature())])
            vals.append([min(a, 100), min(b, 100)])
    if not vals:
        vals = [[0, 0]]
    aa = [v[0] for v in vals]
    bb = [v[1] for v in vals]
    return [
        sum(aa) / len(aa),
        sum(bb) / len(bb),
        max(aa) - min(aa),
        max(bb) - min(bb),
        face.Area(),
        len(face.Edges()),
    ]


def describe(shape, mesh=True):
    if not shape.isValid() or not shape.Solids():
        raise ValueError(
            "A valid closed solid is required. Surface-only STEP files are not supported."
        )
    faces = shape.Faces()
    if len(faces) > 600:
        raise ValueError("Geometry exceeds the 600-face processing limit.")
    box = shape.BoundingBox()
    if max(box.xlen, box.ylen, box.zlen) > 10000:
        raise ValueError("Geometry exceeds the 10,000 mm extent limit.")
    result = []
    for i, f in enumerate(faces):
        item = {
            "id": i,
            "surface": LABELS.get(f.geomType(), "Other"),
            "area": round(f.Area(), 3),
            "edges": len(f.Edges()),
            "features": features(f),
        }
        if mesh:
            vertices, triangles = f.tessellate(0.15, 0.15)
            item["positions"] = [
                round(q, 5)
                for tri in triangles
                for j in tri
                for q in vertices[j].toTuple()
            ]
            if len(item["positions"]) > 900000:
                raise ValueError("Face tessellation exceeds the rendering limit.")
        result.append(item)
    return {
        "faces": result,
        "face_count": len(faces),
        "edge_count": len(shape.Edges()),
        "volume": round(shape.Volume(), 2),
        "bounds": [box.xlen, box.ylen, box.zlen],
    }
