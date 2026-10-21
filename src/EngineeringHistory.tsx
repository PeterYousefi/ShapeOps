import { useEffect, useState } from "react";
import { Database, Download, FileBox, RefreshCw, ShieldCheck } from "lucide-react";
import type {
  CandidateHistory,
  DriftHistory,
  FailureHistory,
  ReleasesHistory,
  TrainingHistory,
} from "./types";

function useHistory<T>(url: string, refreshKey: number) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let disposed = false;
    let pending = false;
    let controller: AbortController | undefined;
    async function load() {
      if (pending) return;
      pending = true;
      if (!disposed) setLoading(true);
      controller = new AbortController();
      const timeout = window.setTimeout(() => controller?.abort(), 10000);
      try {
        const response = await fetch(url, {
          signal: controller.signal,
          cache: "no-store",
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const value = (await response.json()) as T;
        if (!disposed) {
          setData(value);
          setError("");
        }
      } catch (failure) {
        if (!disposed)
          setError(
            `History could not be refreshed (${(failure as Error).name === "AbortError" ? "request timed out" : (failure as Error).message}).`,
          );
      } finally {
        window.clearTimeout(timeout);
        pending = false;
        if (!disposed) setLoading(false);
      }
    }
    void load();
    return () => {
      disposed = true;
      controller?.abort();
    };
  }, [url, revision, refreshKey]);
  return {
    data,
    error,
    loading,
    retry: () => setRevision((value) => value + 1),
  };
}

const date = (value: number) => new Date(value * 1000).toLocaleString();
const number = (value: number) =>
  value.toLocaleString(undefined, { maximumFractionDigits: 2 });
function Status({
  warning,
  children,
}: {
  warning?: boolean;
  children: React.ReactNode;
}) {
  return (
    <span className={`history-status ${warning ? "warning" : ""}`}>
      {children}
    </span>
  );
}
function Notice({
  error,
  stale,
  retry,
}: {
  error: string;
  stale: boolean;
  retry: () => void;
}) {
  return (
    <div className="history-notice" role="status">
      <p>
        {error} {stale && "Last saved response is shown; it may be stale."}
      </p>
      <button className="text-button" onClick={retry}>
        <RefreshCw size={13} /> Retry history
      </button>
    </div>
  );
}
function Blank({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="history-empty">
      <FileBox size={23} aria-hidden="true" />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function measured(name: string, value: number) {
  if (name.includes("fraction")) return `${number(value * 100)}%`;
  if (name.includes("extent")) return `${number(value)} mm`;
  if (name.includes("area")) return `${number(value)} mm²`;
  return number(value);
}

export function DriftInspector({ refreshKey }: { refreshKey: number }) {
  const remote = useHistory<DriftHistory>("/api/drift?limit=100", refreshKey);
  const [selected, setSelected] = useState("");
  const [expanded, setExpanded] = useState(false);
  const rows = remote.data?.observations ?? [];
  const current = rows.find((row) => row.id === selected) ?? rows[0];
  const features = current
    ? [...current.features].sort((a, b) => b.deviation - a.deviation)
    : [];
  function download() {
    if (!current) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(current, null, 2)], {
        type: "application/json",
      }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `shapeops-screening-${current.id}.json`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }
  return (
    <section
      className="panel engineering-history"
      aria-label="Geometry screening history"
    >
      <div className="panel-header">
        <div className="panel-title">
          <FileBox size={16} />
          <h2>Geometry screening history</h2>
        </div>
        <span className="muted">Saved evidence</span>
      </div>
      {remote.error && (
        <Notice
          error={remote.error}
          stale={!!remote.data}
          retry={remote.retry}
        />
      )}
      {remote.loading && !remote.data ? (
        <p className="history-loading" role="status">
          Loading retained geometry…
        </p>
      ) : !current ? (
        !remote.error && (
          <Blank title="No geometry evidence recorded">
            Run a sample or upload in Inference Studio. Earlier requests are not
            backfilled.
          </Blank>
        )
      ) : (
        <>
          <div className="history-controls">
            <label htmlFor="geometry-observation">Inspect request</label>
            <select
              id="geometry-observation"
              value={current.id}
              onChange={(event) => setSelected(event.target.value)}
            >
              {rows.map((row) => (
                <option key={row.id} value={row.id}>
                  {date(row.at)} · {row.source} · {row.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </div>
          <div className="history-summary">
            <Status warning={current.warning}>
              {current.warning
                ? "Geometry warning"
                : "Below screening threshold"}
            </Status>
            <Status warning={current.ood}>
              {current.ood ? "ML OOD warning" : "ML OOD not flagged"}
            </Status>
          </div>
          <dl className="history-facts">
            <div>
              <dt>Input / model</dt>
              <dd>
                {current.source === "sample"
                  ? "Sample geometry"
                  : "Uploaded geometry"}{" "}
                · <span className="mono">{current.model}</span>
              </dd>
            </div>
            <div>
              <dt>Reference</dt>
              <dd>
                {current.reference_parts} owned procedural parts · screening
                only
              </dd>
            </div>
            <div>
              <dt>ML OOD score</dt>
              <dd>{current.ood_score.toFixed(4)} · flag above 0</dd>
            </div>
          </dl>
          <div className="history-features">
            <div className="history-feature-heading">
              <span>FEATURE / MEASURED</span>
              <span>DEVIATION / SCALE</span>
            </div>
            {(expanded ? features : features.slice(0, 5)).map((feature) => (
              <div className="history-feature" key={feature.name}>
                <div>
                  <strong>{feature.name}</strong>
                  <span>
                    {measured(feature.name, feature.value)}{" "}
                    <small>
                      · reference{" "}
                      {measured(feature.name, feature.reference_mean)}
                    </small>
                  </span>
                </div>
                <div>
                  <strong>{number(feature.deviation)}×</strong>
                  <div className="history-track" aria-hidden="true">
                    <i
                      className={
                        feature.deviation >= current.threshold ? "warning" : ""
                      }
                      style={{
                        width: `${Math.min(feature.deviation / (current.threshold * 2), 1) * 100}%`,
                      }}
                    />
                    <b />
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="history-actions">
            <button
              className="text-button"
              onClick={() => setExpanded((value) => !value)}
              aria-expanded={expanded}
            >
              {expanded
                ? "Show top contributors"
                : `Inspect all ${features.length} features`}
            </button>
            <button className="text-button" onClick={download}>
              <Download size={13} /> Export evidence
            </button>
          </div>
          <details className="history-method">
            <summary>Reference method & limitations</summary>
            <p>
              {current.reference_scope}. A warning means any absolute
              standardized deviation is at least {current.threshold}. Scale is
              the larger of reference standard deviation, 5% of its mean, or
              0.000001. Bars cap at {current.threshold * 2}×; numbers retain the
              actual value. ML OOD is a separate model signal.
            </p>
            <p>
              Per-input screening, not industrial population-drift significance.
              Latest 100 retained observations; request retention is 1,000 rows
              / seven days. Refreshes every 15 seconds.
            </p>
            <dl>
              <dt>Reference / method hash</dt>
              <dd>
                <code>{current.reference_id}</code>
              </dd>
              <dt>Request identity</dt>
              <dd>
                <code>{current.id}</code>
              </dd>
            </dl>
          </details>
        </>
      )}
    </section>
  );
}

export function RegistryHistory({ refreshKey }: { refreshKey: number }) {
  const jobs = useHistory<CandidateHistory>(
    "/api/registry/candidate-jobs?limit=20",
    refreshKey,
  );
  const runs = useHistory<TrainingHistory>(
    "/api/registry/runs?limit=20",
    refreshKey,
  );
  const failures = useHistory<FailureHistory>(
    "/api/registry/failures?limit=20",
    refreshKey,
  );
  const [mode, setMode] = useState<"jobs" | "runs" | "failures">("jobs");
  const [selectedJob, setSelectedJob] = useState("");
  const [selectedRun, setSelectedRun] = useState("");
  const remote = mode === "jobs" ? jobs : mode === "runs" ? runs : failures;
  const job =
    jobs.data?.jobs.find((row) => row.id === selectedJob) ?? jobs.data?.jobs[0];
  const run =
    runs.data?.runs.find((row) => row.id === selectedRun) ?? runs.data?.runs[0];
  return (
    <section
      className="panel engineering-history registry-history"
      aria-label="Training execution history"
    >
      <div className="panel-header">
        <div className="panel-title">
          <Database size={16} />
          <h2>Training execution history</h2>
        </div>
        <span className="muted">Actual local records</span>
      </div>
      <div
        className="history-tabs"
        role="group"
        aria-label="Training history type"
      >
        {(
          [
            ["jobs", "Candidate jobs"],
            ["runs", "Completed runs"],
            ["failures", "Initialization failures"],
          ] as const
        ).map(([id, title]) => (
          <button
            key={id}
            aria-pressed={mode === id}
            onClick={() => setMode(id)}
          >
            {title}
          </button>
        ))}
      </div>
      {remote.error && (
        <Notice
          error={remote.error}
          stale={!!remote.data}
          retry={remote.retry}
        />
      )}
      {remote.loading && !remote.data ? (
        <p className="history-loading" role="status">
          Loading saved training history…
        </p>
      ) : mode === "jobs" ? (
        job ? (
          <div className="history-explorer">
            <div className="history-list" aria-label="Candidate jobs">
              {jobs.data?.jobs.map((row) => (
                <button
                  key={row.id}
                  aria-pressed={row.id === job.id}
                  onClick={() => setSelectedJob(row.id)}
                >
                  <span className="mono">{row.id.slice(0, 12)}</span>
                  <strong>{row.status.replaceAll("_", " ")}</strong>
                  <small>{date(row.started_at)}</small>
                </button>
              ))}
            </div>
            <div className="history-detail">
              <Status warning={job.status !== "succeeded"}>
                {job.status.replaceAll("_", " ")}
              </Status>
              <h3>{job.candidate?.id ?? "No candidate result saved"}</h3>
              <p>{job.scope}</p>
              <dl>
                <dt>Started</dt>
                <dd>{date(job.started_at)}</dd>
                <dt>Finished</dt>
                <dd>
                  {job.finished_at === null
                    ? "Not recorded"
                    : date(job.finished_at)}
                </dd>
                <dt>Job identity</dt>
                <dd>
                  <code>{job.id}</code>
                </dd>
                {job.candidate && (
                  <>
                    <dt>Training run</dt>
                    <dd>
                      <code>{job.candidate.run_id}</code>
                    </dd>
                    <dt>Immutable package</dt>
                    <dd>
                      <code>{job.candidate.package_id}</code>
                    </dd>
                    <dt>Security evidence</dt>
                    <dd>
                      {job.candidate.gates.security
                        ? "Recorded as passed; release authorization still required"
                        : "Not approved · no production promotion"}
                    </dd>
                  </>
                )}
              </dl>
              <p className="history-caveat">
                A saved running state does not prove the worker is still alive.
                Jobs are isolated from serving models.
              </p>
            </div>
          </div>
        ) : (
          !remote.error && (
            <Blank title="No candidate jobs saved">
              Create an isolated job from the trusted local command line. This
              public interface cannot start training or promote a model.
              <code>.venv/bin/python -m backend.candidate_job</code>
            </Blank>
          )
        )
      ) : mode === "runs" ? (
        run ? (
          <div className="history-explorer">
            <div className="history-list" aria-label="Completed runs">
              {runs.data?.runs.map((row) => (
                <button
                  key={row.id}
                  aria-pressed={row.id === run.id}
                  onClick={() => setSelectedRun(row.id)}
                >
                  <span className="mono">{row.id.slice(0, 12)}</span>
                  <strong>{row.models.length} packages</strong>
                  <small>{date(row.completed_at)}</small>
                </button>
              ))}
            </div>
            <div className="history-detail">
              <Status>Completed model snapshots</Status>
              <h3>Preserved training lineage</h3>
              <p>
                {date(run.started_at)} → {date(run.completed_at)}
              </p>
              <code>{run.id}</code>
              {run.models.map((model) => (
                <div className="history-package" key={model.model_id}>
                  <strong>{model.model_id}</strong>
                  <code>{model.package_id}</code>
                </div>
              ))}
              <p className="history-caveat">
                These are completed local model snapshots, not production
                releases. A later initialization failure may be recorded
                separately.
              </p>
            </div>
          </div>
        ) : (
          !remote.error && (
            <Blank title="No completed runs recorded">
              Completed local baseline training will appear here with its actual
              package identities.
            </Blank>
          )
        )
      ) : failures.data?.failures.length ? (
        <ol className="history-failures">
          {failures.data.failures.map((row) => (
            <li key={row.id}>
              <Status warning>{row.category}</Status>
              <div>
                <strong>{date(row.failed_at)}</strong>
                <p>Initialization started {date(row.started_at)}</p>
                <code>{row.id}</code>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        !remote.error && (
          <Blank title="No handled initialization failures recorded">
            This journal captures handled exceptions only. Process kills and
            unavailable storage may leave no failure record.
          </Blank>
        )
      )}
      <div className="panel-foot">
        Read-only local history · latest 20 records per category · no production
        release authority
      </div>
    </section>
  );
}

export function ReleaseHistory({ refreshKey }: { refreshKey: number }) {
  const remote = useHistory<ReleasesHistory>(
    "/api/operations/releases?limit=20",
    refreshKey,
  );
  const [selectedId, setSelectedId] = useState("");
  const releases = remote.data?.releases ?? [];
  const selected = releases.find((r) => r.id === selectedId) ?? releases[0];

  const download = () => {
    if (!selected) return;
    const blob = new Blob([JSON.stringify(selected, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `shapeops-release-${selected.id.slice(0, 16)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section
      className="panel engineering-history release-history"
      aria-label="Release authorization audit journal"
    >
      <div className="panel-header">
        <div className="panel-title">
          <ShieldCheck size={16} />
          <h2>Release authorization audit journal</h2>
          {releases.length > 0 && <span className="count">{releases.length}</span>}
        </div>
        <span className="muted">Append-only SQLite audit journal</span>
      </div>

      {remote.error && (
        <Notice
          error={remote.error}
          stale={!!remote.data}
          retry={remote.retry}
        />
      )}

      {remote.loading && !remote.data ? (
        <p className="history-loading" role="status">
          Loading release decisions…
        </p>
      ) : releases.length === 0 ? (
        <Blank title="No release decisions recorded">
          No candidate promotion decisions have been evaluated yet. Authenticated
          candidate release decisions evaluated via POST /api/operations/promote
          or the operator release CLI are committed to this append-only audit
          journal with timing-safe token authentication and immutable triggers.
        </Blank>
      ) : (
        <div className="history-explorer">
          <div className="history-list" aria-label="Release decisions">
            {releases.map((row) => (
              <button
                key={row.id}
                aria-pressed={row.id === selected.id}
                onClick={() => setSelectedId(row.id)}
              >
                <div className="history-list-top">
                  <span className="mono">{row.candidate_id}</span>
                  <Status warning={row.status !== "approved"}>
                    {row.status === "approved" ? "Approved" : "Rejected"}
                  </Status>
                </div>
                <small>
                  {row.operator} · {date(row.at)}
                </small>
              </button>
            ))}
          </div>

          <div className="history-detail">
            <div className="history-detail-header">
              <div>
                <Status warning={selected.status !== "approved"}>
                  {selected.status === "approved"
                    ? "Decision: Approved"
                    : "Decision: Rejected"}
                </Status>
                <h3>{selected.candidate_id}</h3>
              </div>
              <button
                className="text-button"
                onClick={download}
                title="Export verified decision JSON"
              >
                <Download size={13} /> Export decision
              </button>
            </div>

            <p className="history-rationale">
              <strong>Rationale:</strong> {selected.rationale}
            </p>

            <div className="history-gates-section">
              <h4>Evaluated release gates</h4>
              <div className="history-gates-grid">
                {Object.entries(selected.gates).map(([name, passed]) => (
                  <div
                    key={name}
                    className={`history-gate-pill ${passed ? "pass" : "fail"}`}
                  >
                    <span className="gate-icon">{passed ? "✓" : "✗"}</span>
                    <span className="gate-name">
                      {name.replace(/_/g, " ")}
                    </span>
                    <span className="gate-status">
                      {passed ? "PASS" : "FAIL"}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <dl>
              <dt>Decision ID</dt>
              <dd>
                <code>{selected.id}</code>
              </dd>
              <dt>Evaluated at</dt>
              <dd>{date(selected.at)}</dd>
              <dt>Operator identity</dt>
              <dd>
                <code>{selected.operator}</code>
              </dd>
              <dt>Package checksum</dt>
              <dd>
                <code>{selected.package_id}</code>
              </dd>
            </dl>
          </div>
        </div>
      )}
      <div className="panel-foot">
        Append-only SQLite audit journal · immutable triggers · timing-safe token authentication
      </div>
    </section>
  );
}
