import { ChevronLeft, ChevronRight, X } from "lucide-react";
import type { Face, Result } from "./types";
import { COLORS } from "./types";
const percent = (n: number) => `${(n * 100).toFixed(1)}%`;
export default function PredictionDetails({
  result,
  face,
  onSelect,
  onClear,
  primaryLabel,
  comparisonLabel,
}: {
  result: Result | null;
  face: Face | undefined;
  onSelect: (id: number) => void;
  onClear: () => void;
  primaryLabel: string;
  comparisonLabel: string;
}) {
  if (!result)
    return (
      <div className="inspection-empty">
        <h3>No analysis yet</h3>
        <p>
          Run a sample or upload STEP geometry to inspect surfaces and model
          probabilities.
        </p>
      </div>
    );
  const groups = Object.keys(COLORS)
    .map((label) => {
      const faces = result.faces.filter((f) => f.prediction === label);
      return {
        label,
        count: faces.length,
        confidence:
          faces.reduce((n, f) => n + f.confidence, 0) / (faces.length || 1),
        first: faces[0]?.id,
      };
    })
    .filter((g) => g.count);
  const bins = [0, 0, 0, 0];
  result.faces.forEach(
    (f) => bins[Math.min(3, Math.floor(f.confidence * 4))]++,
  );
  return (
    <>
      {face ? (
        <section className="face-details" aria-label="Selected face details">
          <div className="face-selection-heading">
            <span className="eyebrow">SELECTED FACE</span>
            <button aria-label="Clear face selection" onClick={onClear}>
              <X size={14} />
            </button>
          </div>
          <div className="face-stepper">
            <button
              aria-label="Previous face"
              onClick={() =>
                onSelect(
                  result.faces[
                    (result.faces.indexOf(face) + result.faces.length - 1) %
                      result.faces.length
                  ].id,
                )
              }
            >
              <ChevronLeft size={16} />
            </button>
            <h3>Face {String(face.id + 1).padStart(3, "0")}</h3>
            <button
              aria-label="Next face"
              onClick={() =>
                onSelect(
                  result.faces[
                    (result.faces.indexOf(face) + 1) % result.faces.length
                  ].id,
                )
              }
            >
              <ChevronRight size={16} />
            </button>
          </div>
          <div className="prediction-class">
            <i style={{ background: COLORS[face.prediction] }} />
            {face.prediction}
            <strong>{percent(face.confidence)}</strong>
          </div>
          <p className="probability-note">
            {primaryLabel} · uncalibrated probability
          </p>
          <div
            className="confidence-bar"
            role="meter"
            aria-label="Selected face confidence"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Number((face.confidence * 100).toFixed(1))}
          >
            <i style={{ width: percent(face.confidence) }} />
          </div>
          {face.probabilities && (
            <details className="class-probabilities">
              <summary>Class probabilities</summary>
              {Object.entries(face.probabilities)
                .sort((a, b) => b[1] - a[1])
                .map(([label, value]) => (
                  <div key={label}>
                    <span>{label}</span>
                    <span className="probability-track">
                      <i
                        style={{
                          width: percent(value),
                          background: COLORS[label],
                        }}
                      />
                    </span>
                    <b>{percent(value)}</b>
                  </div>
                ))}
            </details>
          )}
          {face.candidate && (
            <div
              className={
                "face-comparison " + (face.disagreement ? "changed" : "")
              }
            >
              <span>{comparisonLabel}</span>
              <strong>
                {face.candidate}
                {face.comparison_confidence != null && (
                  <small>{percent(face.comparison_confidence)}</small>
                )}
              </strong>
              <p>
                {face.disagreement
                  ? "Class changed between models"
                  : "Both models agree on this surface"}
              </p>
            </div>
          )}
          <dl>
            <div>
              <dt>Face identifier</dt>
              <dd className="mono">face:{face.id}</dd>
            </div>
            <div>
              <dt>Surface area</dt>
              <dd>{face.area.toFixed(2)} mm²</dd>
            </div>
            <div>
              <dt>Boundary edges</dt>
              <dd>{face.edges}</dd>
            </div>
            <div>
              <dt>CAD surface type</dt>
              <dd>{face.surface}</dd>
            </div>
            <div>
              <dt>Part surface share</dt>
              <dd>
                {percent(
                  face.area / result.faces.reduce((n, f) => n + f.area, 0),
                )}
              </dd>
            </div>
          </dl>
        </section>
      ) : (
        <>
          <span className="eyebrow">INFERENCE SUMMARY</span>
          <h3>Surface predictions</h3>
          <p className="probability-note">{primaryLabel}</p>
          <div className="summary-confidence">
            <strong>{percent(result.confidence)}</strong>
            <span>
              Mean face confidence
              <small>Uncalibrated model probabilities</small>
            </span>
          </div>
        </>
      )}
      <details className="class-breakdown" open={!face}>
        <summary>
          Class breakdown <span>{result.face_count} faces</span>
        </summary>
        <div className="stacked-classes" aria-hidden="true">
          {groups.map((g) => (
            <i
              key={g.label}
              style={{
                width: percent(g.count / result.face_count),
                background: COLORS[g.label],
              }}
            />
          ))}
        </div>
        {groups.map((g) => (
          <button
            key={g.label}
            onClick={() => onSelect(g.first)}
            aria-label={`Inspect ${g.label} surfaces`}
          >
            <i style={{ background: COLORS[g.label] }} />
            <span>
              {g.label}
              <small>{percent(g.confidence)} mean confidence</small>
            </span>
            <strong>{g.count}</strong>
            <span>{Math.round((g.count / result.face_count) * 100)}%</span>
          </button>
        ))}
        <div className="confidence-distribution">
          <span>Face confidence distribution</span>
          <div>
            {bins.map((n, i) => (
              <span key={i}>
                <i
                  style={{
                    height: `${Math.max(2, (n / result.face_count) * 32)}px`,
                  }}
                />
                <b>{n}</b>
                <small>
                  {i * 25}–{(i + 1) * 25}%
                </small>
              </span>
            ))}
          </div>
        </div>
      </details>
    </>
  );
}
