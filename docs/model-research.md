# Research decision: own procedural baseline

Reviewed upstream sources on 2026-10-19:

- [BRepNet repository and README](https://github.com/AutodeskAILab/BRepNet): topological message-passing research implementation; README describes pretrained checkpoints, per-face logits and an OpenCascade pipeline. It lists CC BY-NC-SA 4.0 and a Conda/PyTorch/occwl environment. It describes a 3.2 GB segmentation archive and preprocessing up to ten minutes under its documented conditions; those are upstream descriptions, not ShapeOps measurements.
- [Fusion 360 Gallery Dataset](https://github.com/AutodeskAILab/Fusion360GalleryDataset): segmentation labels describe modeling operations such as Extrude/Fillet/Chamfer. The README points to a separate dataset license and lists segmentation downloads. Dataset redistribution was not approved or attempted.
- [OpenCascade meshing documentation](https://github.com/Open-Cascade-SAS/OCCT/blob/master/dox/user_guides/mesh/mesh.md): B-rep faces retain their triangulations, supporting a face-indexed viewer contract.

Decision: do not bundle BRepNet code, checkpoints, or Gallery data. A public broadly redistributable portfolio should not assume noncommercial research licensing permits its intended use. The current research integration has not been CPU-benchmarked; compatibility, memory and image-size suitability remain unverified. No claim that a pretrained model is unavailable is made.

Instead, ShapeOps generates original analytic solids with CadQuery/OpenCascade, extracts numerical principal curvature samples and topology measurements, and trains seeded scikit-learn estimators. Original training code and original procedural datasets are MIT-licensed; third-party runtime licenses remain separate. The target is **analytic surface class**, not manufacturing operation. This is an explicitly narrower baseline with the same replaceable face-level serving contract.

Held-out evaluation groups are separated by procedural parameter group. Good synthetic performance does not establish industrial generalization or calibrated confidence. Broader reference data, a documented licensed checkpoint integration and real-world evaluation are future improvements.
