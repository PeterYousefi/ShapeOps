# Training, model cards and governance

Run `.venv/bin/python -m backend.training`. Runtime startup performs the same seeded training to provide a credential-free working platform. The current application does not load untrusted pickles.

Seed 42 generates 100 parameter groups of boxes, cylinders, cones, spheres and tori using CadQuery/OpenCascade. Features are principal-curvature samples, their variation, face area and edge count. Nonfinite descriptors, wrong feature width or missing classes abort training. Groups 0–79 train; groups 80–99 form the holdout. There are 1,200 training faces and 300 holdout faces in the current generation.

`surface-rf-v1` uses 24 balanced Random Forest trees, maximum depth 3 and all features per split. `surface-et-v2` uses 64 Extra Trees, maximum depth 12. Both achieve 1.0 macro F1 on this limited analytic holdout; held-out log losses differ (approximately 0.11356 vs 0.00995), and composite sample confidence/disagreement behavior differs. These are actual synthetic evaluation results, not evidence of industrial accuracy or calibrated confidence.

Canonical tree-node fields and values are hashed with SHA-256; the structured-field encoding avoids nondeterministic padding bytes. Artifacts are packaged under `.runtime/models/<tree-hash>/`: `trees.json`, `estimator.joblib` and `manifest.json`. Both canonical-tree and packaged-estimator digests are recorded. Source snapshots, requirements-lock hashes and Git state identify actual code/environment provenance. Do not commit runtime binary packages. The tracked evaluation report provides readable evidence; historical immutable registry run records, arbitrary candidate creation and long-lived promotion history are not yet a complete lifecycle service.

The pure governance function requires macro F1 ≥ 0.85, compatible schema/runtime, approved licensing and a passing security scan. All gates plus authorization are required for eligibility. A regression test verifies that a poor-quality candidate is rejected. Security remains false because image scanning and deployment review are unfinished; passing a dependency audit alone does not clear the release. The promotion route always returns 403 in this local application.

Limitations: analytic synthetic data, uncalibrated probabilities, possible topology/area correlations and weak free-form surface generalization. The OOD Isolation Forest sees perturbed descriptors of five representative solids only. It is a reproducible screening demonstration, not validated production drift detection. Deviations from mean reference descriptors are diagnostic context, not causal model explanations. Production quality metrics need labeled real-world evaluation; they cannot be inferred from request confidence.

## Studio probability inspection

Inference responses include each face’s primary estimator class probabilities and, when comparison is requested, the other estimator’s actual maximum probability as `comparison_confidence`. The legacy `candidate` field identifies the alternate estimator’s class, including when the primary model is itself the candidate. The UI labels both sides from completed-result model IDs and registry stages, not pending toolbar selections. Probabilities are not calibrated accuracy estimates. Class breakdowns count the real returned faces, and confidence distributions group those returned probabilities.
