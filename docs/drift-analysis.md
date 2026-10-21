# Window-Level Geometry Drift Analysis

ShapeOps provides both per-request screening and aggregate window-level distribution analysis for CAD geometry.

While per-request screening flags isolated abnormal parts, window-level distribution analysis evaluates population shifts across retained inference requests to detect systematic distribution drift in input CAD geometries over time.

## Methodology

### 1. Extracted Geometry Features

For every closed STEP solid, fourteen topology and spatial distribution descriptors are extracted:
- `Face count`: Total topological faces in the B-rep model.
- `Edge count`: Total topological edges in the solid.
- `Smallest extent`: Minimum bounding box dimension along principal axes.
- `Middle extent`: Intermediate bounding box dimension.
- `Largest extent`: Maximum bounding box dimension.
- `Aspect ratio`: Ratio of largest to smallest extent ($L_{max} / \max(L_{min}, 10^{-6})$).
- `Edges per face`: Average edge count per face ($N_{edges} / N_{faces}$).
- `Total face area`: Surface integral sum over all face tessellations ($\sum A_i$).
- `Planar face fraction`: Fraction of analytic planar surfaces ($N_{planar} / N_{faces}$).
- `Cylindrical face fraction`: Fraction of analytic cylindrical surfaces ($N_{cylindrical} / N_{faces}$).
- `Conical face fraction`: Fraction of analytic conical surfaces ($N_{conical} / N_{faces}$).
- `Spherical face fraction`: Fraction of analytic spherical surfaces ($N_{spherical} / N_{faces}$).
- `Toroidal face fraction`: Fraction of analytic toroidal surfaces ($N_{toroidal} / N_{faces}$).
- `Other face fraction`: Fraction of other classified surfaces ($N_{other} / N_{faces}$).

### 2. Reference Distribution

The baseline distribution is derived from the canonical owned sample solids (e.g. mounting bracket, flange, bearing housing, stepped shaft, manifold block). For each feature $j$:
- Reference mean: $\mu_{ref, j}$
- Reference standard deviation: $\sigma_{ref, j}$
- Reference scale floor: $s_{ref, j} = \max(\sigma_{ref, j}, \max(|\mu_{ref, j}| \times 0.05, 10^{-6}))$

The 5% relative floor prevents division by zero or inflated sensitivity on near-zero-variance reference parameters.

### 3. Statistical Drift Tests

For each feature $j$ across the observed window $Y = [y_1, \dots, y_m]$:
1. **Standardized Mean Shift:**
   $$\Delta_j = \frac{|\mu_{obs, j} - \mu_{ref, j}|}{s_{ref, j}}$$
   A standardized absolute mean shift at or above the configured threshold (default: $3.0$) raises a screening flag; it does not establish statistical significance.

2. **Two-Sample Kolmogorov-Smirnov Distance ($D_{KS}$):**
   The non-parametric empirical maximum vertical distance between the empirical cumulative distribution functions (ECDF) of the observed window $F_{obs}(x)$ and the baseline reference $F_{ref}(x)$:
   $$D_{KS} = \sup_{x} |F_{obs}(x) - F_{ref}(x)| \in [0, 1]$$
   Evaluated at all unified evaluation points $x \in Y_{obs} \cup X_{ref}$. A distance $D_{KS} \ge 0.5$ triggers a distribution screening flag.

### 4. Summary & Screening Flags
- Feature Alert: $\text{Alert}_j = (\Delta_j \ge \text{threshold}_{shift}) \lor (D_{KS, j} \ge \text{threshold}_{KS})$
- Population Drift Detected: $\text{DriftDetected} = \bigvee_j \text{Alert}_j$
- OOD prevalence: reports separate sample and upload counts plus the fraction flagged by the ML Isolation Forest. No feature-to-OOD correlation coefficient is calculated.

## Interpretation limits

This report is deterministic descriptive screening for a bounded retained window. The KS statistic is the maximum empirical CDF distance, without a p-value; samples from repeated/related requests may not be independent. The baseline has five owned procedural parts. The default thresholds are heuristics, not validated alert thresholds. No confidence intervals, multiple-testing correction, effect-size validation, operator alert routing or industrial acceptance are provided. Upload/sample source categories and geometry features are preserved, but this is not a causal or feature-to-OOD correlation analysis. An observation window mixing incompatible reference hashes, reference counts, feature contracts or screening thresholds is rejected.

The analysis snapshot is limited to the latest configured number of saved observations inside the inclusive seven-day request-retention window at the recorded analysis time. Future-dated rows and observations over 16 KiB are excluded or rejected; the emitted report records the window cutoff. Reads use one SQLite transaction and do not run migrations or retention cleanup.

## CLI Usage

The trusted-local evaluation tool runs in one read-only SQLite transaction without mutating active serving state:

```bash
python -m backend.drift_report \
  --database .runtime/telemetry.sqlite \
  --output artifacts/drift-report.json \
  --limit 1000 \
  --shift-threshold 3.0 \
  --ks-threshold 0.5
```

### Safety and Resource Controls
- **Read-Only Mode:** SQLite connection enforces `mode=ro` and `PRAGMA query_only=ON`.
- **Atomic Publication:** Reports write to a temporary staging file and link via `os.link` with permission `0600`, preventing partial reads and protecting against overwriting existing files.
- **Byte Budget:** Maximum report size is capped at 256 KiB; windows are bounded to at most 1,000 retained observations.
- **Fail-Closed:** Missing tables, non-regular database files, incompatible reference populations, oversized observations, and non-finite metrics immediately abort with a nonzero status and no source mutations.
