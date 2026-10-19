import React, { useState, useEffect, useCallback, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Box,
  Boxes,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Code2,
  Command,
  Copy,
  Cpu,
  Database,
  ExternalLink,
  FileBox,
  FileUp,
  GitBranch,
  GitCompareArrows,
  Hexagon,
  Info,
  LayoutDashboard,
  Loader2,
  Menu,
  PanelLeftClose,
  Play,
  Radio,
  Search,
  Server,
  ShieldCheck,
  Terminal,
  TriangleAlert,
  Workflow,
  X,
  Zap,
} from "lucide-react";
import Viewer from "./Viewer";
import type { Result, Registry, Telemetry, Operations } from "./types";
import { COLORS } from "./types";
import "./styles.css";
import "./lab.css";
const NAV = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Inference Studio", icon: Box },
  { name: "Model Registry", icon: Boxes },
  { name: "Observability", icon: Activity },
  { name: "Operations", icon: Workflow },
  { name: "Documentation", icon: BookOpen },
];
const SAMPLES = [
  {
    id: "bracket",
    name: "Mounting bracket",
    kind: "MACHINED PART",
    description: "Pocketed plate with through holes",
  },
  {
    id: "flange",
    name: "Bearing flange",
    kind: "ROTATIONAL PART",
    description: "Circular housing with a bolt pattern",
  },
  {
    id: "housing",
    name: "Sensor housing",
    kind: "ENCLOSURE",
    description: "Thin-wall shell with rounded corners",
  },
  {
    id: "shaft",
    name: "Stepped shaft",
    kind: "TURNED PART",
    description: "Concentric shoulders and stepped diameters",
  },
  {
    id: "manifold",
    name: "Fluid manifold",
    kind: "MACHINED PART",
    description: "Cross-drilled block with multiple ports",
  },
];
const EMPTY: Telemetry = {
  total: 0,
  successful: 0,
  failed: 0,
  p50: null,
  p95: null,
  ood_rate: null,
  origin: "Actual local runtime",
  requests: [],
  throughput_per_minute: 0,
};
async function get<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok)
    throw new Error(
      `Service returned ${res.status}. Check the local API and retry.`,
    );
  return res.json();
}
const ms = (v: number | null | undefined) =>
  v == null ? "—" : `${v < 10 ? v.toFixed(1) : Math.round(v)} ms`;
const pct = (v: number | null | undefined) =>
  v == null ? "—" : `${(v * 100).toFixed(1)}%`;
const ago = (at: number) => {
  const s = Math.floor(Date.now() / 1000 - at);
  return s < 60
    ? "Just now"
    : s < 3600
      ? `${Math.floor(s / 60)}m ago`
      : `${Math.floor(s / 3600)}h ago`;
};
function Badge({
  children,
  tone = "green",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return (
    <span className={"badge " + tone}>
      <span />
      {children}
    </span>
  );
}
function SectionTitle({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="section-title">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h2>{title}</h2>
      </div>
      {children}
    </div>
  );
}
function Empty({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="empty">
      <Activity size={28} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function Stat({
  label,
  value,
  foot,
  icon: Icon,
  color = "cyan",
}: {
  label: string;
  value: string | number;
  foot: string;
  icon: typeof Activity;
  color?: string;
}) {
  return (
    <div className="stat">
      <div className="stat-top">
        <span>{label}</span>
        <Icon size={16} className={color} />
      </div>
      <strong>{value}</strong>
      <div className="stat-foot">
        <span className={"tiny-dot " + color} />
        {foot}
      </div>
    </div>
  );
}
function App() {
  const [page, setPage] = useState(() => {
      const p = decodeURIComponent(location.hash.slice(1));
      return NAV.some((n) => n.name === p) ? p : "Overview";
    }),
    [collapsed, setCollapsed] = useState(false),
    [mobile, setMobile] = useState(false),
    [registrySelection, setRegistrySelection] = useState("surface-rf-v1"),
    [result, setResult] = useState<Result | null>(null),
    [resultFilename, setResultFilename] = useState<string | null>(null),
    [selected, setSelected] = useState<number | null>(null),
    [sample, setSample] = useState("bracket"),
    [model, setModel] = useState("surface-rf-v1"),
    [compare, setCompare] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [apiError, setApiError] = useState(""),
    [registry, setRegistry] = useState<Registry[]>([]),
    [telemetry, setTelemetry] = useState<Telemetry>(EMPTY),
    [ops, setOps] = useState<Operations | null>(null),
    [modal, setModal] = useState<string | null>(null),
    [viewMode, setViewMode] = useState("prediction"),
    [uploadProgress, setUploadProgress] = useState<number | null>(null),
    [file, setFile] = useState<File | null>(null),
    [search, setSearch] = useState(""),
    [drilling, setDrilling] = useState(false),
    [copied, setCopied] = useState(false),
    [doc, setDoc] = useState("Quick start");
  const input = useRef<HTMLInputElement>(null);
  const selectFace = useCallback((id: number) => setSelected(id), []);
  const navigate = useCallback((name: string) => {
    setPage(name);
    location.hash = encodeURIComponent(name);
    setMobile(false);
    setSearch("");
  }, []);
  const refresh = useCallback(async () => {
    try {
      const [t, r, o] = await Promise.all([
        get<Telemetry>("/api/telemetry"),
        get<Registry[]>("/api/registry"),
        get<Operations>("/api/operations"),
      ]);
      setTelemetry(t);
      setRegistry(r);
      setOps(o);
      setApiError("");
    } catch (e) {
      setApiError((e as Error).message);
    }
  }, []);
  const run = useCallback(
    async (s = "bracket", m = "surface-rf-v1", c = false) => {
      setBusy(true);
      setError("");
      try {
        const res = await fetch("/api/inference/sample", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sample: s, model: m, compare: c }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Inference failed");
        setResult(data);
        setResultFilename(null);
        setSelected(null);
        await refresh();
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );
  useEffect(() => {
    void refresh();
    void run();
    const id = setInterval(() => void refresh(), 15000);
    const hash = () => {
      const p = decodeURIComponent(location.hash.slice(1));
      if (NAV.some((n) => n.name === p)) setPage(p);
    };
    window.addEventListener("hashchange", hash);
    return () => {
      clearInterval(id);
      window.removeEventListener("hashchange", hash);
    };
  }, [refresh, run]);
  useEffect(() => {
    if (!modal) return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>("[role=dialog]");
    const focusable = () =>
      Array.from(
        dialog?.querySelectorAll<HTMLElement>(
          'button:not(:disabled),a[href],input,select,[tabindex="0"]',
        ) || [],
      ).filter((e) => e.offsetParent !== null);
    const frame = requestAnimationFrame(() => {
      const input = dialog?.querySelector<HTMLInputElement>("input");
      (input || focusable()[0])?.focus();
    });
    const trap = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const items = focusable();
      if (!items.length) return;
      const first = items[0],
        last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", trap);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("keydown", trap);
      previous?.focus();
    };
  }, [modal]);
  useEffect(() => {
    document.documentElement.dataset.theme = "light";
    localStorage.setItem("shapeops-theme", "light");
  }, []);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setModal(null);
        setMobile(false);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setModal("search");
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  function upload(f: File) {
    setFile(f);
    setError("");
    if (!/\.(step|stp)$/i.test(f.name)) {
      setError("Choose a .step or .stp CAD file.");
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError("File exceeds the 10 MB limit.");
      return;
    }
    setBusy(true);
    setUploadProgress(0);
    const data = new FormData();
    data.append("file", f);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/inference/upload?model=${model}&compare=${compare}`);
    xhr.timeout = 45000;
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable)
        setUploadProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      try {
        const value = JSON.parse(xhr.responseText);
        if (xhr.status >= 400)
          throw new Error(value.detail || "Upload failed.");
        setResult(value);
        setResultFilename(f.name);
        setSelected(null);
        void refresh();
      } catch (e) {
        setError((e as Error).message);
      }
      setBusy(false);
      setUploadProgress(null);
    };
    xhr.onerror = () => {
      setError("Connection interrupted. Check the API and retry.");
      setBusy(false);
      setUploadProgress(null);
    };
    xhr.ontimeout = () => {
      setError("Processing timed out. Try a smaller solid.");
      setBusy(false);
      setUploadProgress(null);
    };
    xhr.send(data);
  }
  function downloadReport() {
    if (!result) return;
    const { faces, ...rest } = result;
    const blob = new Blob(
      [
        JSON.stringify(
          { ...rest, faces: faces.map(({ positions, ...f }) => f) },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "shapeops-inference-report.json";
    a.click();
    URL.revokeObjectURL(url);
  }
  const active = registry.find((r) => r.id === model) || registry[0];
  const face = result?.faces.find((f) => f.id === selected);
  const histogram = Object.keys(COLORS)
    .map((label) => ({
      label,
      count: result?.faces.filter((f) => f.prediction === label).length || 0,
    }))
    .filter((r) => r.count > 0);
  const heading = (
    <div className="page-heading">
      <div>
        <div className="breadcrumb">
          SHAPEOPS LAB <ChevronRight size={11} />{" "}
          {page === "Inference Studio"
            ? "GEOMETRY / ANALYSIS"
            : "ENGINEERING WORKSPACE"}
        </div>
        <h1>{page === "Overview" ? "Workspace overview" : page}</h1>
        <p>
          {
            (
              {
                Overview:
                  "From CAD geometry to operational intelligence. One connected workspace.",
                "Inference Studio":
                  "A working surface for geometry, predictions and model comparison.",
                "Model Registry":
                  "Versioned artifacts, reproducible lineage, explicit release gates.",
                Observability:
                  "A clear view of service health, model behavior, and input quality.",
                Operations:
                  "Understand every release. Validate every recovery.",
                Documentation:
                  "Everything you need to explore, build, and operate ShapeOps.",
              } as Record<string, string>
            )[page]
          }
        </p>
      </div>
      <div className="heading-actions">
        {page === "Overview" ? (
          <>
            <button
              className="button secondary"
              onClick={() => {
                setDoc("Quick start");
                navigate("Documentation");
              }}
            >
              <BookOpen size={15} /> Quick start
            </button>
            <button
              className="button primary"
              onClick={() => navigate("Inference Studio")}
            >
              <Box size={16} /> Open studio <ArrowUpRight size={15} />
            </button>
          </>
        ) : page === "Inference Studio" ? (
          <button
            className="button secondary"
            disabled={!result}
            onClick={downloadReport}
          >
            <ArrowDownToLine size={15} /> Export report
          </button>
        ) : (
          <button className="button secondary" onClick={() => void refresh()}>
            <Activity size={15} /> Refresh data
          </button>
        )}
      </div>
    </div>
  );
  function recentTable(limit = 5) {
    return telemetry.requests.length ? (
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>TRACE / MODEL</th>
              <th>INPUT</th>
              <th>STATUS</th>
              <th>LATENCY</th>
              <th>TIME</th>
            </tr>
          </thead>
          <tbody>
            {telemetry.requests.slice(0, limit).map((r) => (
              <tr key={r.id}>
                <td>
                  <button
                    className="text-button mono"
                    onClick={() => setModal(`trace:${r.id}`)}
                  >
                    {r.id.slice(0, 8)} <ArrowUpRight size={11} />
                  </button>
                  <small>{r.model}</small>
                </td>
                <td>
                  <span className="input-type">
                    <FileBox size={14} />
                    {r.source === "sample" ? "Sample CAD" : "STEP upload"}
                  </span>
                  <small>{r.faces || "—"} faces</small>
                </td>
                <td>
                  <Badge tone={r.success ? "green" : "red"}>
                    {r.success ? "Success" : "Failed"}
                  </Badge>
                </td>
                <td className="mono">{ms(r.latency)}</td>
                <td className="muted">{ago(r.at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    ) : (
      <Empty title="Your first request starts here">
        Run a sample in Inference Studio to see real request telemetry.
      </Empty>
    );
  }
  function chart() {
    const rows = [...telemetry.requests].reverse();
    const max = Math.max(...rows.map((r) => r.latency), 1);
    return (
      <div className="chart">
        <div className="chart-y">
          <span>{ms(max)}</span>
          <span>{ms(max / 2)}</span>
          <span>0 ms</span>
        </div>
        <div className="chart-plot">
          <div className="chart-grid" />
          {rows.length ? (
            <svg
              viewBox="0 0 600 140"
              preserveAspectRatio="none"
              role="img"
              aria-label="Measured inference latency by request"
            >
              <defs>
                <linearGradient id="area" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#5cc8ba" stopOpacity=".22" />
                  <stop offset="100%" stopColor="#5cc8ba" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path
                d={`M 0 140 ${rows.map((r, i) => `L ${rows.length === 1 ? 300 : (i / (rows.length - 1)) * 600} ${135 - (r.latency / max) * 110}`).join(" ")} L 600 140 Z`}
                fill="url(#area)"
              />
              <polyline
                points={rows
                  .map(
                    (r, i) =>
                      `${rows.length === 1 ? 300 : (i / (rows.length - 1)) * 600},${135 - (r.latency / max) * 110}`,
                  )
                  .join(" ")}
                fill="none"
                stroke="#68d5c3"
                strokeWidth="2"
              />
              {rows.map((r, i) => (
                <circle
                  key={r.id}
                  cx={rows.length === 1 ? 300 : (i / (rows.length - 1)) * 600}
                  cy={135 - (r.latency / max) * 110}
                  r="3.5"
                  fill="#68d5c3"
                >
                  <title>
                    {ms(r.latency)} · {r.id.slice(0, 8)}
                  </title>
                </circle>
              ))}
            </svg>
          ) : (
            <div className="chart-no-data">No requests recorded</div>
          )}
          <div className="chart-x">
            <span>Oldest request</span>
            <span>
              {rows.length} measured request{rows.length === 1 ? "" : "s"}
            </span>
            <span>Latest</span>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div
      className={
        "app " +
        (collapsed ? "sidebar-collapsed " : "") +
        (mobile ? "mobile-open" : "")
      }
    >
      <div className="mobile-scrim" onClick={() => setMobile(false)} />
      <aside className="sidebar">
        <a
          className="brand"
          href="#Overview"
          onClick={() => navigate("Overview")}
          aria-label="ShapeOps home"
        >
          <span className="brand-mark">
            <Hexagon size={27} />
            <Box size={15} />
          </span>
          <span>
            shape<span className="brand-ops">ops</span>
            <small>DIGITAL ENGINEERING LAB</small>
          </span>
        </a>
        <button
          className="workspace-switch"
          onClick={() => setModal("workspace")}
        >
          <span className="workspace-icon">S</span>
          <span>
            ShapeOps workspace<small>Personal workspace</small>
          </span>
          <ChevronDown size={14} />
        </button>
        <div className="nav-label">LAB WORKSPACE</div>
        <nav>
          {NAV.map(({ name, icon: Icon }) => (
            <button
              key={name}
              aria-label={name}
              aria-current={page === name ? "page" : undefined}
              title={collapsed ? name : undefined}
              className={"nav-item " + (page === name ? "selected" : "")}
              onClick={() => navigate(name)}
            >
              <Icon size={18} />
              <span>{name}</span>
              {name === "Inference Studio" && (
                <span className="nav-new">3D</span>
              )}
              {page === name && <span className="nav-indicator" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <div>
              <span className="tiny-dot" /> Local environment{" "}
              <ArrowUpRight size={13} />
            </div>
            <p>Real inference. Your machine.</p>
            <span className="mono">
              CPU runtime <span>●</span>
            </span>
          </div>
          <button
            className="nav-item"
            onClick={() => {
              setDoc("5-minute walkthrough");
              navigate("Documentation");
            }}
          >
            <BookOpen size={17} />
            <span>Lab guide</span>
          </button>
          <button
            className="nav-item collapse-btn"
            aria-label={collapsed ? "Expand navigation" : "Collapse sidebar"}
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? (
              <ChevronRight size={17} />
            ) : (
              <PanelLeftClose size={17} />
            )}
            <span>Collapse sidebar</span>
          </button>
          <div className="profile">
            <div className="avatar">SE</div>
            <div>
              ShapeOps engineer<small>Local developer</small>
            </div>
            <button
              aria-label="Workspace information"
              onClick={() => setModal("workspace")}
            >
              <ChevronDown size={14} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="topbar-path">
            <button
              className="mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={20} />
            </button>
            <span className="topbar-logo">
              <Hexagon size={15} />
            </span>
            <span>Workspace</span>
            <span className="slash">/</span>
            <strong>{page}</strong>
          </div>
          <div className="topbar-right">
            <button
              className="search-trigger"
              onClick={() => setModal("search")}
            >
              <Search size={14} />
              <span>Find anything...</span>
              <kbd>⌘ K</kbd>
            </button>
            <span className="top-divider" />
            <span className="system-state">
              <span className={"tiny-dot " + (apiError ? "red" : "")} />
              {apiError ? "API unavailable" : "Local runtime online"}
            </span>
            <button
              className="help-icon"
              aria-label="Platform information"
              onClick={() => setModal("about")}
            >
              <Info size={17} />
            </button>
          </div>
        </header>
        <main className={"page-" + page.toLowerCase().replaceAll(" ", "-")}>
          {heading}
          {apiError && (
            <div className="alert red">
              <TriangleAlert size={16} />
              {apiError}
              <button onClick={() => void refresh()}>Retry</button>
            </div>
          )}
          {error && (
            <div className="alert red" role="alert">
              <TriangleAlert size={16} />
              <span>{error}</span>
              <button
                onClick={() =>
                  file ? upload(file) : void run(sample, model, compare)
                }
              >
                Retry
              </button>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={14} />
              </button>
            </div>
          )}
          {page === "Overview" && (
            <>
              <div className="overview-stats">
                <Stat
                  label="Inference requests"
                  value={telemetry.total}
                  foot={`${telemetry.successful} successful · ${telemetry.failed} failed`}
                  icon={Activity}
                />
                <Stat
                  label="P95 inference latency"
                  value={ms(telemetry.p95)}
                  foot="Measured local runtime"
                  icon={Zap}
                  color="blue"
                />
                <Stat
                  label="Registered models"
                  value={registry.length}
                  foot={
                    registry.length
                      ? `${registry.filter((r) => r.stage === "stable").length} stable · ${registry.filter((r) => r.stage === "candidate").length} candidate`
                      : "Registry unavailable"
                  }
                  icon={Boxes}
                  color="purple"
                />
                <Stat
                  label="Runtime status"
                  value={apiError ? "Unavailable" : "Operational"}
                  foot="Local environment · CPU"
                  icon={Server}
                />
              </div>
              <div className="overview-main">
                <section className="panel studio-preview">
                  <div className="panel-header">
                    <div className="panel-title">
                      <Box size={17} />
                      <h2>Inference Studio</h2>
                      <span className="subtle-badge">LIVE WORKSPACE</span>
                    </div>
                    <button
                      className="icon-button"
                      aria-label="Open Inference Studio"
                      onClick={() => navigate("Inference Studio")}
                    >
                      <ArrowUpRight size={17} />
                    </button>
                  </div>
                  <div className="preview-model-info">
                    <div>
                      <span className="eyebrow">GEOMETRY EXPLORER</span>
                      <h3>Understand every surface.</h3>
                      <p>Real CAD. Face-level predictions. Full visibility.</p>
                    </div>
                    <Badge tone="blue">Sample geometry</Badge>
                  </div>
                  <Viewer
                    result={result}
                    selected={selected}
                    onSelect={selectFace}
                    compact
                  />
                  <div className="preview-bottom">
                    <div className="mini-legend">
                      {histogram.map((h) => (
                        <span key={h.label}>
                          <i style={{ background: COLORS[h.label] }} />
                          {h.label}
                          <b>{h.count}</b>
                        </span>
                      ))}
                    </div>
                    <button
                      className="button secondary small"
                      onClick={() => navigate("Inference Studio")}
                    >
                      Explore model <ArrowRight size={14} />
                    </button>
                  </div>
                </section>
                <div className="overview-side">
                  <section className="panel active-model">
                    <div className="panel-header">
                      <div className="panel-title">
                        <Cpu size={17} />
                        <h2>Active model</h2>
                      </div>
                      <Badge>Stable</Badge>
                    </div>
                    <div className="active-model-body">
                      <div className="model-symbol">
                        <Boxes size={27} />
                      </div>
                      <h3>Surface classifier</h3>
                      <p className="mono">surface-rf-v1</p>
                      <div className="model-meta">
                        <span>
                          Framework<strong>scikit-learn</strong>
                        </span>
                        <span>
                          Execution<strong>CPU inference</strong>
                        </span>
                        <span>
                          Held-out macro F1
                          <strong>
                            {active ? pct(registry[0]?.macro_f1) : "—"}
                          </strong>
                        </span>
                      </div>
                      <div className="data-note">
                        <Info size={13} />
                        <span>
                          Procedural analytic surfaces.
                          <br />
                          Synthetic evaluation, not industrial accuracy.
                        </span>
                      </div>
                      <button
                        className="text-button"
                        onClick={() => navigate("Model Registry")}
                      >
                        View model & lineage <ArrowRight size={14} />
                      </button>
                    </div>
                  </section>
                  <section className="candidate-strip">
                    <span className="eyebrow">CANDIDATE / EVALUATION</span>
                    <h3>
                      {registry.find((r) => r.stage === "candidate")?.id ||
                        "Unavailable"}
                    </h3>
                    <p>
                      {registry.find((r) => r.stage === "candidate")
                        ?.algorithm || "Registry unavailable"}{" "}
                      · awaiting release gates
                    </p>
                    <button
                      className="text-button"
                      onClick={() => {
                        setRegistrySelection(
                          registry.find((r) => r.stage === "candidate")?.id ||
                            "surface-et-v2",
                        );
                        navigate("Model Registry");
                      }}
                    >
                      Inspect candidate <ArrowRight size={13} />
                    </button>
                  </section>
                  <section className="walkthrough-card">
                    <div className="walkthrough-icon">
                      <Command size={18} />
                    </div>
                    <div className="eyebrow">TAKE THE GUIDED TOUR</div>
                    <h3>
                      Five minutes.
                      <br />
                      The whole pipeline.
                    </h3>
                    <p>
                      From your first CAD model to a verified recovery drill.
                    </p>
                    <button
                      className="text-button"
                      onClick={() => {
                        setDoc("5-minute walkthrough");
                        navigate("Documentation");
                      }}
                    >
                      Start walkthrough <ArrowRight size={14} />
                    </button>
                  </section>
                </div>
              </div>
              <div className="overview-lower">
                <section className="panel">
                  <div className="panel-header">
                    <div className="panel-title">
                      <Activity size={16} />
                      <h2>Inference activity</h2>
                    </div>
                    <span className="chart-key">
                      <i />
                      Request latency
                    </span>
                  </div>
                  {chart()}
                  <div className="panel-foot">
                    <span className="tiny-dot" /> Actual local requests{" "}
                    <span className="muted">· includes labeled samples</span>
                    <button
                      className="text-button"
                      onClick={() => navigate("Observability")}
                    >
                      Observability <ArrowUpRight size={13} />
                    </button>
                  </div>
                </section>
                <section className="panel system-panel">
                  <div className="panel-header">
                    <div className="panel-title">
                      <ShieldCheck size={16} />
                      <h2>System health</h2>
                    </div>
                    <span className="mono muted">LOCAL</span>
                  </div>
                  {[
                    ["API service", "FastAPI"],
                    ["Geometry engine", "OpenCascade"],
                    ["Model serving", "scikit-learn"],
                    ["Telemetry storage", "SQLite"],
                  ].map(([name, sub]) => (
                    <div className="health-row" key={name}>
                      <div>
                        <span>{name}</span>
                        <small>{sub}</small>
                      </div>
                      <span className={apiError ? "muted" : "green"}>
                        <span
                          className={"tiny-dot " + (apiError ? "red" : "")}
                        />
                        {apiError ? "Unknown" : "Ready"}
                      </span>
                    </div>
                  ))}
                </section>
              </div>
              <section className="panel lab-event-stream">
                <SectionTitle title="Recent operational events" />
                {ops?.drills.length ? (
                  ops.drills.slice(0, 3).map((d) => (
                    <div className="lab-event" key={d.id}>
                      <CheckCircle2 size={17} />
                      <div>
                        <strong>
                          Isolated recovery drill{" "}
                          {d.passed ? "passed" : "failed"}
                        </strong>
                        <small>
                          {d.checks.length} checks · {ms(d.duration_ms)} ·{" "}
                          {ago(d.at)}
                        </small>
                      </div>
                      <button
                        className="text-button"
                        onClick={() => navigate("Operations")}
                      >
                        Inspect <ArrowRight size={13} />
                      </button>
                    </div>
                  ))
                ) : (
                  <Empty title="No operational events recorded">
                    Run an isolated recovery drill in Operations to create a
                    real event.
                  </Empty>
                )}
              </section>
              <section className="panel recent-panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <Terminal size={16} />
                    <h2>Recent CAD analyses</h2>
                    <span className="count">{telemetry.total}</span>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => navigate("Observability")}
                  >
                    View all requests <ArrowRight size={13} />
                  </button>
                </div>
                {recentTable(3)}
              </section>
            </>
          )}
          {page === "Inference Studio" && (
            <>
              <div className="studio-toolbar">
                <div className="toolbar-left">
                  <div className="field-inline">
                    <label htmlFor="sample">INPUT</label>
                    <select
                      id="sample"
                      value={sample}
                      onChange={(e) => {
                        setSample(e.target.value);
                        setFile(null);
                      }}
                    >
                      {SAMPLES.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    className="button secondary"
                    disabled={busy}
                    onClick={() => input.current?.click()}
                  >
                    <FileUp size={15} /> Upload STEP
                  </button>
                  <input
                    ref={input}
                    type="file"
                    accept=".step,.stp"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files?.[0]) upload(e.target.files[0]);
                      e.target.value = "";
                    }}
                  />
                </div>
                <div className="toolbar-right">
                  <select
                    aria-label="Model version"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                  >
                    {registry.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.id} · {r.stage}
                      </option>
                    ))}
                  </select>
                  <label className="compare-toggle">
                    <input
                      type="checkbox"
                      checked={compare}
                      onChange={(e) => setCompare(e.target.checked)}
                    />
                    <GitCompareArrows size={15} />
                    Compare
                  </label>
                  <button
                    className="button primary"
                    disabled={busy}
                    onClick={() =>
                      file ? upload(file) : void run(sample, model, compare)
                    }
                  >
                    {busy ? (
                      <Loader2 size={15} className="spin" />
                    ) : (
                      <Play size={14} />
                    )}{" "}
                    {busy ? "Processing…" : "Run inference"}
                  </button>
                </div>
              </div>
              {uploadProgress !== null && (
                <div className="upload-progress">
                  <span>
                    {uploadProgress < 100
                      ? `Uploading ${uploadProgress}%`
                      : "Upload complete. Parsing geometry and running inference…"}
                  </span>
                  <progress value={uploadProgress} max={100} />
                </div>
              )}
              <div className="lab-section-label">
                <span>01 / GEOMETRY WORKSPACE</span>
                <span>FACE-LEVEL SURFACE ANALYSIS</span>
              </div>
              <div className="studio-layout">
                <section className="panel studio-canvas-panel">
                  <div className="studio-canvas-header">
                    <div className="panel-title">
                      <FileBox size={16} />
                      <h2>
                        {resultFilename || result?.name || "CAD workspace"}
                      </h2>
                      <Badge
                        tone={result?.source === "sample" ? "blue" : "green"}
                      >
                        {result?.source === "sample"
                          ? "Sample CAD"
                          : "Uploaded CAD"}
                      </Badge>
                    </div>
                    <select
                      aria-label="Viewport coloring"
                      value={viewMode}
                      onChange={(e) => setViewMode(e.target.value)}
                    >
                      <option value="prediction">Prediction colors</option>
                      <option value="solid">Solid geometry</option>
                      <option value="disagreements">Disagreements</option>
                    </select>
                  </div>
                  <Viewer
                    result={result}
                    selected={selected}
                    onSelect={selectFace}
                    mode={viewMode}
                  />
                  <div className="canvas-info">
                    <div className="mini-legend">
                      {histogram.map((h) => (
                        <button
                          key={h.label}
                          onClick={() => {
                            const f = result?.faces.find(
                              (f) => f.prediction === h.label,
                            );
                            if (f) setSelected(f.id);
                          }}
                        >
                          <i style={{ background: COLORS[h.label] }} />
                          {h.label}
                          <b>{h.count}</b>
                        </button>
                      ))}
                    </div>
                    <span className="mono muted">
                      {result?.bounds.map((b) => b.toFixed(1)).join(" × ")} mm
                    </span>
                  </div>
                </section>
                <aside className="inspector panel">
                  <div className="panel-header">
                    <div className="panel-title">
                      <LayersIcon />
                      <h2>Prediction inspector</h2>
                    </div>
                    <span className="count">{result?.face_count || 0}</span>
                  </div>
                  <div className="inspector-body">
                    <span className="eyebrow">
                      {face ? "SELECTED FACE" : "INFERENCE SUMMARY"}
                    </span>
                    <h3>
                      {face
                        ? `Face ${String(face.id + 1).padStart(3, "0")}`
                        : "Geometry intelligence"}
                    </h3>
                    <p>
                      {face
                        ? "Actual B-rep face and model output."
                        : "Click a surface in the viewport or select a face below."}
                    </p>
                    {face ? (
                      <>
                        <div className="prediction-class">
                          <i style={{ background: COLORS[face.prediction] }} />
                          {face.prediction}
                        </div>
                        <div className="confidence-label">
                          <span>Model confidence</span>
                          <strong>{pct(face.confidence)}</strong>
                        </div>
                        <div className="confidence-bar">
                          <i style={{ width: pct(face.confidence) }} />
                        </div>
                        <dl>
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
                            <dt>Face identifier</dt>
                            <dd className="mono">face:{face.id}</dd>
                          </div>
                          {face.candidate && (
                            <div>
                              <dt>Comparison</dt>
                              <dd>{face.candidate}</dd>
                            </div>
                          )}
                        </dl>
                      </>
                    ) : (
                      <dl>
                        <div>
                          <dt>Predicted faces</dt>
                          <dd>{result?.face_count || "—"}</dd>
                        </div>
                        <div>
                          <dt>Boundary edges</dt>
                          <dd>{result?.edge_count || "—"}</dd>
                        </div>
                        <div>
                          <dt>Mean confidence</dt>
                          <dd>{pct(result?.confidence)}</dd>
                        </div>
                        <div>
                          <dt>Solid volume</dt>
                          <dd>
                            {result
                              ? `${Math.round(result.volume).toLocaleString()} mm³`
                              : "—"}
                          </dd>
                        </div>
                      </dl>
                    )}
                    <div className="inspector-separator" />
                    <div className="eyebrow">EXECUTION DETAILS</div>
                    <dl>
                      <div>
                        <dt>Total latency</dt>
                        <dd>{ms(result?.latency_ms)}</dd>
                      </div>
                      <div>
                        <dt>CAD preprocessing</dt>
                        <dd>
                          {result?.source === "sample"
                            ? "Cached geometry"
                            : ms(result?.parse_ms)}
                        </dd>
                      </div>
                      <div>
                        <dt>Model execution</dt>
                        <dd>{ms(result?.execution_ms)}</dd>
                      </div>
                      <div>
                        <dt>Model version</dt>
                        <dd className="mono">
                          {result?.model.replace("surface-", "") || "—"}
                        </dd>
                      </div>
                      {result?.comparison_model && (
                        <div>
                          <dt>Disagreements</dt>
                          <dd>
                            {result.disagreements} / {result.face_count}
                          </dd>
                        </div>
                      )}
                    </dl>
                    <div
                      className={"ood-note " + (result?.ood ? "warning" : "")}
                    >
                      <ShieldCheck size={16} />
                      <div>
                        <strong>
                          {result?.ood
                            ? "Outside reference distribution"
                            : "Within reference distribution"}
                        </strong>
                        <p>
                          Procedural geometry screening · not a calibrated
                          industrial OOD guarantee.
                        </p>
                      </div>
                    </div>
                    <div className="trace-id">
                      <span>TRACE ID</span>
                      <button
                        onClick={() => {
                          if (result) {
                            void navigator.clipboard.writeText(result.trace_id);
                            setCopied(true);
                            setTimeout(() => setCopied(false), 1500);
                          }
                        }}
                      >
                        {result?.trace_id.slice(0, 16) || "—"}
                        {copied ? <Check size={12} /> : <Copy size={12} />}
                      </button>
                    </div>
                  </div>
                </aside>
              </div>
              <div className="lab-section-label">
                <span>02 / FACE EXPLORER</span>
                <span>LINKED TO VIEWPORT SELECTION</span>
              </div>
              <section className="panel faces-panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <Boxes size={16} />
                    <h2>Face predictions</h2>
                    <span className="count">{result?.face_count || 0}</span>
                  </div>
                  <span className="muted">
                    Select a row to highlight its surface
                  </span>
                </div>
                <div className="table-scroll face-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>FACE</th>
                        <th>PREDICTED CLASS</th>
                        <th>CONFIDENCE</th>
                        <th>AREA (mm²)</th>
                        <th>EDGES</th>
                        {compare && <th>COMPARISON</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {result?.faces.map((f) => (
                        <tr
                          key={f.id}
                          className={selected === f.id ? "selected-row" : ""}
                          onClick={() => setSelected(f.id)}
                        >
                          <td>
                            <button
                              className="text-button mono"
                              onClick={() => setSelected(f.id)}
                            >
                              Face {String(f.id + 1).padStart(3, "0")}
                            </button>
                          </td>
                          <td>
                            <span className="class-label">
                              <i style={{ background: COLORS[f.prediction] }} />
                              {f.prediction}
                            </span>
                          </td>
                          <td>
                            <span className="table-confidence">
                              <i style={{ width: pct(f.confidence) }} />
                              {pct(f.confidence)}
                            </span>
                          </td>
                          <td className="mono">{f.area.toFixed(2)}</td>
                          <td>{f.edges}</td>
                          {compare && (
                            <td>
                              {f.candidate ? (
                                <Badge
                                  tone={f.disagreement ? "amber" : "green"}
                                >
                                  {f.disagreement ? f.candidate : "Agreement"}
                                </Badge>
                              ) : (
                                "Run comparison"
                              )}
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <div className="privacy-note">
                <ShieldCheck size={14} />
                Uploads are processed temporarily and deleted after success or
                failure. STEP / STP · up to 10 MB · 600 faces · closed solids.
              </div>
            </>
          )}
          {page === "Model Registry" && (
            <>
              <div className="info-banner">
                <GitBranch size={18} />
                <div>
                  <strong>Inspect the artifact. Follow its lineage.</strong>
                  <span>
                    Immutable trained-tree checksums, dataset hashes, held-out
                    evaluation, and source provenance.
                  </span>
                </div>
                <Badge tone="blue">Local registry</Badge>
              </div>
              <div className="lab-section-label">
                <span>01 / RELEASE EXPLORER</span>
                <span>REGISTERED ARTIFACTS · NOT A DEPLOYMENT HISTORY</span>
              </div>
              <div
                className="release-selector"
                aria-label="Registered model versions"
              >
                {registry.map((r, index) => (
                  <button
                    key={r.id}
                    aria-pressed={registrySelection === r.id}
                    onClick={() => setRegistrySelection(r.id)}
                  >
                    <span className="release-index">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span>
                      <strong>{r.id}</strong>
                      <small>
                        {r.algorithm} · {r.stage}
                      </small>
                    </span>
                    <GitBranch size={18} />
                  </button>
                ))}
              </div>
              <div className="registry-grid">
                {registry
                  .filter((r) => r.id === registrySelection)
                  .map((r) => (
                    <section
                      key={r.id}
                      className="panel model-card release-selected"
                    >
                      <div className="model-card-top">
                        <div className="model-symbol">
                          <Boxes size={27} />
                        </div>
                        <Badge tone={r.stage === "stable" ? "green" : "purple"}>
                          {r.stage === "stable"
                            ? "Stable baseline"
                            : "Candidate"}
                        </Badge>
                      </div>
                      <div className="eyebrow">
                        ANALYTIC SURFACE CLASSIFICATION
                      </div>
                      <h2>{r.id}</h2>
                      <p>
                        {r.algorithm} · {r.framework}
                      </p>
                      <div className="model-metrics">
                        <div>
                          <strong>{pct(r.macro_f1)}</strong>
                          <span>Held-out macro F1</span>
                        </div>
                        <div>
                          <strong>{r.evaluation_rows}</strong>
                          <span>Evaluation faces</span>
                        </div>
                        <div>
                          <strong>{r.training_rows}</strong>
                          <span>Training faces</span>
                        </div>
                      </div>
                      <div className="data-note">
                        <Info size={14} />
                        {r.limitations}
                      </div>
                      <dl>
                        <div>
                          <dt>Artifact SHA-256</dt>
                          <dd className="mono">{r.checksum.slice(0, 16)}…</dd>
                        </div>
                        <div>
                          <dt>Runtime</dt>
                          <dd>{r.runtime}</dd>
                        </div>
                        <div>
                          <dt>Training seed</dt>
                          <dd>42 · deterministic</dd>
                        </div>
                      </dl>
                      <div className="model-card-actions">
                        <button
                          className="button secondary"
                          onClick={() => setModal(`model:${r.id}`)}
                        >
                          <FileBox size={14} /> Model card
                        </button>
                        <button
                          className="text-button"
                          onClick={() => {
                            setModel(r.id);
                            navigate("Inference Studio");
                          }}
                        >
                          Use in studio <ArrowRight size={14} />
                        </button>
                      </div>
                    </section>
                  ))}
              </div>
              <section className="panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <GitCompareArrows size={17} />
                    <h2>Version comparison</h2>
                  </div>
                  <span className="muted">
                    Genuinely distinct trained estimators
                  </span>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>PROPERTY</th>
                        {registry.map((r) => (
                          <th key={r.id}>{r.id}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        ["Algorithm", ...registry.map((r) => r.algorithm)],
                        [
                          "Trees",
                          ...registry.map((r) =>
                            String(r.parameters.n_estimators),
                          ),
                        ],
                        [
                          "Maximum depth",
                          ...registry.map((r) =>
                            String(r.parameters.max_depth),
                          ),
                        ],
                        [
                          "Held-out macro F1",
                          ...registry.map((r) => pct(r.macro_f1)),
                        ],
                        [
                          "Held-out log loss",
                          ...registry.map((r) => r.heldout_log_loss.toFixed(5)),
                        ],
                        [
                          "License",
                          ...registry.map(
                            () => "MIT · original procedural data",
                          ),
                        ],
                        [
                          "Security gate",
                          ...registry.map(() => "Pending independent scan"),
                        ],
                      ].map((row) => (
                        <tr key={row[0]}>
                          {row.map((v, i) => (
                            <td key={i}>{v}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <section className="panel promotion-history">
                <SectionTitle title="Promotion history" />
                <Empty title="No production promotions recorded">
                  Stable and candidate are local registry designations.
                  Production release events appear only after an authorized
                  deployment.
                </Empty>
              </section>
              <section className="panel lineage-panel">
                <SectionTitle title="Reproducible lineage" />
                <div className="lineage-flow">
                  {[
                    {
                      icon: Database,
                      title: "Procedural dataset",
                      desc: "Analytic solids · owned geometry",
                    },
                    {
                      icon: Code2,
                      title: "Feature extraction",
                      desc: "Numerical curvature · area · topology",
                    },
                    {
                      icon: Cpu,
                      title: "Seeded training",
                      desc: "Parameter-group holdout",
                    },
                    {
                      icon: ShieldCheck,
                      title: "Evaluation & gates",
                      desc: "Quality · compatibility · license · security",
                    },
                  ].map((v, i) => (
                    <React.Fragment key={v.title}>
                      {i > 0 && <ArrowRight size={18} />}
                      <div>
                        <v.icon size={20} />
                        <h3>{v.title}</h3>
                        <p>{v.desc}</p>
                      </div>
                    </React.Fragment>
                  ))}
                </div>
              </section>
            </>
          )}
          {page === "Observability" && (
            <>
              <div className="data-origin">
                <span className="tiny-dot" />
                Actual runtime telemetry{" "}
                <span>
                  Latest 1,000 requests · 7-day retention · refreshes every 15
                  seconds
                </span>
                <Badge tone="blue">Local environment</Badge>
              </div>
              <div className="overview-stats">
                <Stat
                  label="Total requests"
                  value={telemetry.total}
                  foot={`${telemetry.successful} successful · ${telemetry.failed} failed`}
                  icon={Activity}
                />
                <Stat
                  label="P50 / P95 latency"
                  value={`${ms(telemetry.p50)} / ${ms(telemetry.p95)}`}
                  foot="Successful inference requests"
                  icon={Clock3}
                />
                <Stat
                  label="Request throughput"
                  value={`${telemetry.throughput_per_minute} / min`}
                  foot="Actual requests in the last minute"
                  icon={Zap}
                  color="blue"
                />
                <Stat
                  label="OOD input rate"
                  value={pct(telemetry.ood_rate)}
                  foot="Procedural reference screening"
                  icon={TriangleAlert}
                  color="amber"
                />
              </div>
              <h2 className="lab-group-title">01 / SERVICE HEALTH</h2>
              <div className="observability-grid">
                <section className="panel">
                  <div className="panel-header">
                    <div className="panel-title">
                      <Activity size={16} />
                      <h2>Service · request latency</h2>
                    </div>
                    <span className="chart-key">
                      <i />
                      Measured latency
                    </span>
                  </div>
                  {chart()}
                  <div className="panel-foot">
                    End-to-end inference latency · sample CAD preprocessing is
                    cached
                  </div>
                </section>
                <section className="panel">
                  <div className="panel-header">
                    <div className="panel-title">
                      <TriangleAlert size={16} />
                      <h2>Errors & model usage</h2>
                    </div>
                  </div>
                  <div className="bar-chart">
                    {registry.map((r) => {
                      const count = telemetry.requests.filter(
                        (q) => q.model === r.id,
                      ).length;
                      return (
                        <div key={r.id}>
                          <span className="mono">
                            {r.id.replace("surface-", "")}
                          </span>
                          <div>
                            <i
                              style={{
                                width: `${telemetry.total ? (count / telemetry.total) * 100 : 0}%`,
                              }}
                            />
                          </div>
                          <b>{count}</b>
                        </div>
                      );
                    })}
                  </div>
                  <div className="health-row">
                    <span>Validation failures</span>
                    <strong>
                      {
                        telemetry.requests.filter(
                          (r) => r.error === "validation",
                        ).length
                      }
                    </strong>
                  </div>
                  <div className="health-row">
                    <span>Processing timeouts</span>
                    <strong>
                      {
                        telemetry.requests.filter((r) => r.error === "timeout")
                          .length
                      }
                    </strong>
                  </div>
                  <div className="panel-foot">
                    <a
                      className="text-button"
                      href="/metrics"
                      target="_blank"
                      rel="noreferrer"
                    >
                      Prometheus metrics <ExternalLink size={13} />
                    </a>
                    <a
                      className="text-button"
                      href="/docs"
                      target="_blank"
                      rel="noreferrer"
                    >
                      API reference <ExternalLink size={13} />
                    </a>
                  </div>
                </section>
              </div>
              <div className="lab-monitoring-zones">
                <div>
                  <h2 className="lab-group-title">02 / MODEL BEHAVIOR</h2>
                  <section className="panel distribution-panel">
                    <div className="panel-header">
                      <div className="panel-title">
                        <Cpu size={16} />
                        <h2>Model · confidence distribution</h2>
                      </div>
                    </div>
                    <div className="bar-chart">
                      {["0–50%", "50–70%", "70–85%", "85–95%", "95–100%"].map(
                        (label, i) => {
                          const edges = [0, 0.5, 0.7, 0.85, 0.95, 1.001];
                          const count = telemetry.requests.filter(
                            (r) =>
                              r.success &&
                              r.confidence >= edges[i] &&
                              r.confidence < edges[i + 1],
                          ).length;
                          return (
                            <div key={label}>
                              <span>{label}</span>
                              <div>
                                <i
                                  style={{
                                    width: `${telemetry.successful ? (count / telemetry.successful) * 100 : 0}%`,
                                  }}
                                />
                              </div>
                              <b>{count}</b>
                            </div>
                          );
                        },
                      )}
                    </div>
                    <div className="data-note">
                      <Info size={13} />
                      Per-request mean probability. Uncalibrated classifier
                      confidence.
                    </div>
                  </section>
                </div>
                <div>
                  <h2 className="lab-group-title">
                    03 / DATA DISTRIBUTION & DRIFT
                  </h2>
                  <section className="panel">
                    <div className="panel-header">
                      <div className="panel-title">
                        <FileBox size={16} />
                        <h2>Data distribution & drift screening</h2>
                      </div>
                    </div>
                    <div className="data-quality">
                      <div>
                        <span>Latest face count</span>
                        <strong>{result?.face_count || "—"}</strong>
                      </div>
                      <div>
                        <span>Latest edge count</span>
                        <strong>{result?.edge_count || "—"}</strong>
                      </div>
                      <div>
                        <span>Reference status</span>
                        <Badge tone={result?.ood ? "amber" : "green"}>
                          {result?.ood
                            ? "Outside reference"
                            : "Within reference"}
                        </Badge>
                      </div>
                    </div>
                    <div className="distribution-contributors">
                      <span className="eyebrow">
                        LATEST INPUT · DEVIATION FROM REFERENCE MEAN
                      </span>
                      {result?.ood_contributions.slice(0, 3).map((c) => (
                        <div key={c.feature}>
                          <span>{c.feature}</span>
                          <strong>{c.deviation}%</strong>
                        </div>
                      ))}
                    </div>
                    <div className="data-note">
                      <Info size={13} />
                      Isolation Forest trained on perturbed descriptors of five
                      procedural sample solids. Industrial drift validity is
                      unestablished.
                    </div>
                  </section>
                </div>
              </div>
              <section className="panel recent-panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <Terminal size={16} />
                    <h2>Request explorer</h2>
                  </div>
                  <span className="muted">
                    Actual traces · no CAD content retained
                  </span>
                </div>
                {recentTable(20)}
              </section>
            </>
          )}
          {page === "Operations" && (
            <>
              <div className="info-banner">
                <ShieldCheck size={22} />
                <div>
                  <strong>A safe place to practice recovery.</strong>
                  <span>
                    Local controls execute isolated tests. Production promotion
                    requires authentication and explicit authorization.
                  </span>
                </div>
                <Badge tone="amber">Local only</Badge>
              </div>
              <div className="lab-section-label">
                <span>01 / VALIDATE → AUTHORIZE → RELEASE</span>
                <span>LOCAL CONTROL PLANE</span>
              </div>
              <div className="ops-grid">
                <section className="panel release-panel">
                  <div className="panel-header">
                    <div className="panel-title">
                      <GitBranch size={16} />
                      <h2>Rollout checkpoints</h2>
                    </div>
                    <Badge tone="amber">Not deployed</Badge>
                  </div>
                  <div className="release-pair">
                    <div>
                      <span className="eyebrow">STABLE BASELINE</span>
                      <h3>{ops?.active || "—"}</h3>
                      <Badge>Serving locally</Badge>
                    </div>
                    <ArrowRight size={20} />
                    <div>
                      <span className="eyebrow">CANDIDATE</span>
                      <h3>{ops?.candidate || "—"}</h3>
                      <Badge tone="purple">Evaluation complete</Badge>
                    </div>
                  </div>
                  <div className="gates">
                    {Object.entries(registry[1]?.gates || {}).map(
                      ([name, passed]) => (
                        <div key={name}>
                          {passed ? (
                            <CheckCircle2 size={17} className="green" />
                          ) : (
                            <Clock3 size={17} className="amber" />
                          )}
                          <div>
                            <strong>
                              {name[0].toUpperCase() + name.slice(1)} gate
                            </strong>
                            <span>
                              {
                                (
                                  {
                                    quality: "Held-out macro F1 ≥ 85%",
                                    compatibility:
                                      "Feature schema and CPU runtime compatible",
                                    license:
                                      "Original procedural dataset · MIT",
                                    security:
                                      "Independent dependency and image scans required",
                                  } as Record<string, string>
                                )[name]
                              }
                            </span>
                          </div>
                          <Badge tone={passed ? "green" : "amber"}>
                            {passed ? "Passed" : "Pending"}
                          </Badge>
                        </div>
                      ),
                    )}
                  </div>
                  <div className="data-note">
                    <Info size={14} />
                    {ops?.promotion ||
                      "Production release state is unavailable."}
                  </div>
                </section>
                <section className="panel drill-panel">
                  <div className="panel-header">
                    <div className="panel-title">
                      <Workflow size={17} />
                      <h2>Incident rehearsal</h2>
                    </div>
                    <span className="subtle-badge">ISOLATED</span>
                  </div>
                  <div className="drill-graphic">
                    <ShieldCheck size={43} />
                    <span />
                    <Activity size={23} />
                  </div>
                  <h3>
                    Test the failure.
                    <br />
                    Verify the recovery.
                  </h3>
                  <p>
                    Inject an adapter failure, detect it, run genuine
                    stable-model inference, and verify that release state stays
                    intact.
                  </p>
                  <button
                    className="button primary"
                    disabled={drilling}
                    onClick={async () => {
                      setDrilling(true);
                      setError("");
                      try {
                        const res = await fetch("/api/operations/drill", {
                          method: "POST",
                        });
                        const value = await res.json();
                        if (!res.ok) throw new Error(value.detail);
                        await refresh();
                      } catch (e) {
                        setError((e as Error).message);
                      } finally {
                        setDrilling(false);
                      }
                    }}
                  >
                    {drilling ? (
                      <Loader2 size={15} className="spin" />
                    ) : (
                      <Play size={15} />
                    )}{" "}
                    {drilling
                      ? "Executing checks…"
                      : "Run isolated incident drill"}
                  </button>
                  <small>
                    No infrastructure changes. No production impact.
                  </small>
                </section>
              </div>
              <section className="panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <CheckCircle2 size={17} />
                    <h2>Recorded drill outcomes</h2>
                    <span className="count">{ops?.drills.length || 0}</span>
                  </div>
                </div>
                {ops?.drills.length ? (
                  <div className="drill-results">
                    {ops.drills.map((d) => (
                      <div className="drill-record" key={d.id}>
                        <div className="drill-record-header">
                          <div>
                            <Badge tone={d.passed ? "green" : "red"}>
                              {d.passed ? "Recovered" : "Failed"}
                            </Badge>
                            <span className="mono">drill:{d.id}</span>
                          </div>
                          <span>
                            {ms(d.duration_ms)} · {ago(d.at)}
                          </span>
                        </div>
                        <div className="drill-checks">
                          {d.checks.map((c) => (
                            <span key={c.name}>
                              <CheckCircle2
                                size={14}
                                className={c.passed ? "green" : "red"}
                              />
                              {c.name}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Empty title="Ready when you are">
                    Run your first isolated drill to create an actual test
                    record.
                  </Empty>
                )}
              </section>
              <section className="panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <Server size={16} />
                    <h2>Production release history</h2>
                  </div>
                </div>
                <Empty title="No production deployments">
                  Azure has not been provisioned. Deployment revisions,
                  smoke-test records, traffic promotions and rollback events
                  appear only after an authorized deployment.
                </Empty>
              </section>
            </>
          )}
          {page === "Documentation" && (
            <div className="docs-layout">
              <aside className="panel docs-nav">
                <span className="eyebrow">GET STARTED</span>
                {[
                  "Quick start",
                  "5-minute walkthrough",
                  "CAD & uploads",
                  "Model methodology",
                  "Architecture",
                  "Security & privacy",
                  "Operations runbook",
                  "API reference",
                ].map((d) => (
                  <button
                    key={d}
                    className={doc === d ? "active" : ""}
                    onClick={() => setDoc(d)}
                  >
                    <BookOpen size={14} />
                    {d}
                    <ChevronRight size={12} />
                  </button>
                ))}
              </aside>
              <article className="panel doc-content">
                <div className="eyebrow">SHAPEOPS DOCUMENTATION</div>
                <h2>{doc}</h2>
                {doc === "Quick start" ? (
                  <>
                    <p className="doc-lead">
                      A complete CAD inference workflow, running on your
                      machine.
                    </p>
                    <div className="doc-callout">
                      <Info size={18} />
                      <p>
                        This workspace uses real OpenCascade geometry and
                        trained surface classifiers. Sample inputs are original
                        procedural parts. All operational metrics come from
                        requests executed by this runtime.
                      </p>
                    </div>
                    <h3>01 · Explore a part</h3>
                    <p>
                      Open Inference Studio. Choose one of five sample solids or
                      upload a closed-solid STEP file. The default mounting
                      bracket includes a pocket, cylindrical holes and rounded
                      corners.
                    </p>
                    <button
                      className="button primary"
                      onClick={() => navigate("Inference Studio")}
                    >
                      Open Inference Studio <ArrowRight size={14} />
                    </button>
                    <h3>02 · Run and inspect</h3>
                    <p>
                      Choose a model version and run inference. Drag to orbit,
                      scroll to zoom, or right-drag to pan. Click any face to
                      see its class, probability, area and boundary edges. The
                      face table provides the same selection with keyboard
                      support.
                    </p>
                    <h3>03 · Follow the evidence</h3>
                    <p>
                      Inspect the artifact checksum and training lineage in
                      Model Registry. See the actual request in Observability.
                      Execute an isolated incident drill in Operations.
                    </p>
                    <h3>Local development</h3>
                    <pre>
                      <code>
                        python3 -m venv .venv{"\n"}.venv/bin/pip install -r
                        requirements.txt{"\n"}npm ci{"\n"}.venv/bin/uvicorn
                        backend.app:app --port 8000{"\n"}npm run dev
                      </code>
                    </pre>
                  </>
                ) : doc === "5-minute walkthrough" ? (
                  <>
                    <p className="doc-lead">
                      Five minutes from geometry to operational confidence.
                    </p>
                    {[
                      {
                        time: "0:00–1:00",
                        title: "Inspect genuine CAD geometry",
                        text: "Open Studio, orbit the sample bracket and select a planar face. Upload your own STEP solid or download a sample and upload it again.",
                        action: "Inference Studio",
                      },
                      {
                        time: "1:00–2:00",
                        title: "Compare two trained models",
                        text: "Enable Compare and run inference. Inspect the disagreement count. Select disagreement coloring. Zero disagreements is a valid measured outcome.",
                        action: "Inference Studio",
                      },
                      {
                        time: "2:00–3:00",
                        title: "Verify the model lineage",
                        text: "Open both model cards. Compare algorithms, artifact hashes, dataset provenance, evaluation and limitations.",
                        action: "Model Registry",
                      },
                      {
                        time: "3:00–4:00",
                        title: "Follow real telemetry",
                        text: "Inspect your request trace, measured latency and OOD features. Failed uploads also create real telemetry.",
                        action: "Observability",
                      },
                      {
                        time: "4:00–5:00",
                        title: "Rehearse recovery safely",
                        text: "Run the isolated incident drill. Inspect actual failure detection, stable-model inference and release-isolation checks.",
                        action: "Operations",
                      },
                    ].map((v) => (
                      <div className="walkthrough-step" key={v.time}>
                        <span className="mono">{v.time}</span>
                        <h3>{v.title}</h3>
                        <p>{v.text}</p>
                        <button
                          className="text-button"
                          onClick={() => navigate(v.action)}
                        >
                          Open {v.action} <ArrowRight size={13} />
                        </button>
                      </div>
                    ))}
                  </>
                ) : doc === "CAD & uploads" ? (
                  <>
                    <p className="doc-lead">
                      Real STEP parsing, not filename-based answers.
                    </p>
                    <h3>Supported geometry</h3>
                    <p>
                      ISO 10303-21 .step and .stp files containing valid closed
                      solids, up to 10 MB, 600 faces and 10,000 mm extent.
                      OpenCascade validates topology and tessellates each face.
                      Surface-only models are unsupported.
                    </p>
                    <h3>Face correspondence</h3>
                    <p>
                      The same ordered B-rep face collection supplies geometry
                      descriptors, model rows, mesh positions and face
                      identifiers. Viewer raycasting returns this exact
                      identifier to the prediction inspector.
                    </p>
                    <h3>Original downloadable samples</h3>
                    <div className="sample-downloads">
                      {SAMPLES.map((s) => (
                        <a
                          key={s.id}
                          href={`/api/samples/${s.id}/download`}
                          className="sample-download"
                        >
                          <FileBox size={20} />
                          <div>
                            <strong>{s.name}</strong>
                            <span>{s.description}</span>
                          </div>
                          <ArrowDownToLine size={16} />
                        </a>
                      ))}
                    </div>
                    <h3>Upload privacy</h3>
                    <p>
                      Raw files are written to a temporary directory under a
                      fixed internal filename and removed after success, failure
                      or processing timeout. Filenames and raw CAD contents are
                      excluded from telemetry.
                    </p>
                  </>
                ) : doc === "Model methodology" ? (
                  <>
                    <p className="doc-lead">
                      A transparent baseline with explicit limits.
                    </p>
                    <h3>What the model predicts</h3>
                    <p>
                      Planar, cylindrical, conical, spherical and toroidal
                      surface classes using numerical curvature, curvature
                      variation, surface area and edge count. Surface-type
                      labels from the CAD kernel are evaluation targets, never
                      model inputs.
                    </p>
                    <h3>Training & evaluation</h3>
                    <p>
                      One hundred seeded parameter groups generate analytic
                      solids. Eighty groups train the estimators; twenty groups
                      are held out. A shallow Random Forest and deeper Extra
                      Trees model provide genuinely different versions. Metrics
                      describe synthetic held-out faces only.
                    </p>
                    <h3>What the model does not establish</h3>
                    <p>
                      Manufacturing-feature segmentation, calibrated confidence,
                      industrial generalization, or validated production drift
                      thresholds. This is not an implementation of Autodesk
                      BRepNet.
                    </p>
                    <h3>OOD screening</h3>
                    <p>
                      An Isolation Forest learns perturbed face-count,
                      edge-count and bounding-box descriptors from five sample
                      solids. The inspector reports deviations from the
                      reference mean as diagnostic context, not feature
                      attribution or validated drift causality.
                    </p>
                  </>
                ) : doc === "Architecture" ? (
                  <>
                    <p className="doc-lead">
                      A modular monolith with an explicit geometry contract.
                    </p>
                    <div className="architecture-diagram">
                      <div>
                        <Box />
                        React · TypeScript · Three.js
                      </div>
                      <ArrowDownToLine />
                      <div>
                        <Server />
                        FastAPI · typed API contracts
                      </div>
                      <ArrowDownToLine />
                      <div className="architecture-modules">
                        <span>
                          OpenCascade
                          <br />
                          CAD preprocessing
                        </span>
                        <span>
                          scikit-learn
                          <br />
                          Model inference
                        </span>
                        <span>
                          SQLite
                          <br />
                          Runtime telemetry
                        </span>
                      </div>
                    </div>
                    <h3>Local first</h3>
                    <p>
                      Vite proxies the API during development. A built frontend
                      is served by FastAPI in the deployment image. Upload
                      parsing executes in a bounded subprocess with a 30-second
                      timeout and temporary-file cleanup. No Azure credentials
                      are needed.
                    </p>
                    <h3>Planned production target</h3>
                    <p>
                      One Azure Container App with managed identity and storage.
                      Cloud provisioning and deployment remain disabled until
                      explicit approval. Production resource sizing and cold
                      starts require measurement before release.
                    </p>
                  </>
                ) : doc === "Security & privacy" ? (
                  <>
                    <p className="doc-lead">
                      Least privilege, small retention, honest boundaries.
                    </p>
                    <h3>Input controls</h3>
                    <p>
                      STEP extension and header checks, 10 MB upload limits,
                      topology validation, face and extent limits, bounded
                      parsing time and a 20-request-per-minute local rate limit.
                      Temporary raw files are removed on exit.
                    </p>
                    <h3>Administration</h3>
                    <p>
                      Production promotion is disabled. Public users cannot
                      mutate release state, execute arbitrary code or provision
                      resources. The incident rehearsal uses an isolated
                      injected adapter and never changes the stable estimator.
                    </p>
                    <h3>Retention</h3>
                    <p>
                      Telemetry stores request IDs, timing, model identifiers,
                      source category, counts, confidence, OOD flags and error
                      categories. It excludes uploaded filenames and file
                      contents. Records expire after seven days.
                    </p>
                    <h3>Before public production</h3>
                    <p>
                      Complete independent dependency and image security scans,
                      hardened worker memory/CPU limits, distributed abuse
                      controls, OIDC administrative authentication and an
                      authorized deployment review.
                    </p>
                  </>
                ) : doc === "Operations runbook" ? (
                  <>
                    <p className="doc-lead">
                      Detect, isolate, verify, recover.
                    </p>
                    <h3>API unavailable</h3>
                    <p>
                      Check /api/health and structured service logs. Confirm the
                      local API process is running. The UI reports unavailable
                      data instead of substituting sample telemetry.
                    </p>
                    <h3>Geometry rejected</h3>
                    <p>
                      Confirm a closed-solid STEP file within size and
                      complexity limits. Parsing failures return an actionable
                      validation error and are recorded as failures in
                      Observability.
                    </p>
                    <h3>Model regression</h3>
                    <p>
                      Compare the candidate against held-out evaluation and the
                      stable model. Quality, compatibility and licensing gates
                      are necessary; security validation and authorization are
                      also required before promotion.
                    </p>
                    <h3>Recovery drill</h3>
                    <p>
                      Operations executes a controlled failing adapter followed
                      by real stable inference. Review each recorded check. This
                      proves local adapter recovery behavior; it does not verify
                      cloud revision rollback.
                    </p>
                    <button
                      className="button primary"
                      onClick={() => navigate("Operations")}
                    >
                      Open Operations <ArrowRight size={14} />
                    </button>
                  </>
                ) : (
                  <>
                    <p className="doc-lead">
                      Typed requests. Inspectable responses. Correlated
                      execution.
                    </p>
                    <a
                      className="button primary"
                      href="/docs"
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open interactive OpenAPI docs <ExternalLink size={14} />
                    </a>
                    <h3>Run sample inference</h3>
                    <pre>
                      <code>{`curl -X POST http://127.0.0.1:8000/api/inference/sample \\\n  -H 'Content-Type: application/json' \\\n  -d '{"sample":"bracket","model":"surface-rf-v1","compare":true}'`}</code>
                    </pre>
                    <h3>Endpoints</h3>
                    {[
                      ["GET", "/api/health", "Runtime readiness"],
                      [
                        "GET",
                        "/api/registry",
                        "Actual trained estimator records",
                      ],
                      [
                        "POST",
                        "/api/inference/sample",
                        "Sample solid inference",
                      ],
                      [
                        "POST",
                        "/api/inference/upload",
                        "Multipart STEP upload",
                      ],
                      [
                        "GET",
                        "/api/telemetry",
                        "Retained runtime request metrics",
                      ],
                      [
                        "POST",
                        "/api/operations/drill",
                        "Isolated failure and recovery checks",
                      ],
                      ["GET", "/metrics", "Prometheus-compatible exposition"],
                    ].map(([method, path, text]) => (
                      <div className="endpoint" key={path}>
                        <span>{method}</span>
                        <code>{path}</code>
                        <p>{text}</p>
                      </div>
                    ))}
                  </>
                )}
                <div className="doc-footer">
                  <ShieldCheck size={14} /> Documentation reflects the local
                  implementation. Production capabilities require deployment
                  validation.
                </div>
              </article>
            </div>
          )}
          <footer className="app-footer">
            <span>
              <span className="brand-mini">
                <Hexagon size={12} />
              </span>
              ShapeOps <span className="muted">/</span> Engineering intelligence
            </span>
            <span>
              Local-first platform <span className="tiny-dot" /> v0.1.0
            </span>
          </footer>
        </main>
      </div>
      {modal && (
        <div className="modal-backdrop" onClick={() => setModal(null)}>
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label={
              modal === "search" ? "Search workspace" : "Workspace details"
            }
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="modal-close icon-button"
              aria-label="Close dialog"
              onClick={() => setModal(null)}
            >
              <X size={18} />
            </button>
            {modal === "search" ? (
              <>
                <div className="modal-search">
                  <Search size={20} />
                  <input
                    autoFocus
                    aria-label="Search workspace"
                    placeholder="Search screens and documentation…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                  <kbd>ESC</kbd>
                </div>
                <div className="search-results">
                  {NAV.filter((n) =>
                    n.name.toLowerCase().includes(search.toLowerCase()),
                  ).map((n) => (
                    <button
                      key={n.name}
                      onClick={() => {
                        navigate(n.name);
                        setModal(null);
                      }}
                    >
                      <n.icon size={18} />
                      {n.name}
                      <ArrowRight size={15} />
                    </button>
                  ))}
                  {!NAV.some((n) =>
                    n.name.toLowerCase().includes(search.toLowerCase()),
                  ) && (
                    <p>
                      No screens match “{search}”. Try Studio, Registry, or
                      Operations.
                    </p>
                  )}
                </div>
              </>
            ) : modal.startsWith("model:") ? (
              (() => {
                const r = registry.find((r) => r.id === modal.slice(6));
                return r ? (
                  <>
                    <div className="eyebrow">MODEL CARD</div>
                    <h2>{r.id}</h2>
                    <Badge tone={r.stage === "stable" ? "green" : "purple"}>
                      {r.stage}
                    </Badge>
                    <p>{r.limitations}</p>
                    <h3>Provenance</h3>
                    <dl className="hash-list">
                      <dt>Artifact SHA-256</dt>
                      <dd>{r.checksum}</dd>
                      <dt>Packaged estimator SHA-256</dt>
                      <dd>{r.package_checksum}</dd>
                      <dt>Dataset SHA-256</dt>
                      <dd>{r.dataset_hash}</dd>
                      <dt>Source Git commit</dt>
                      <dd>{r.git_commit}</dd>
                      <dt>License</dt>
                      <dd>{r.license}</dd>
                    </dl>
                    <h3>Measured evaluation</h3>
                    <p>
                      {r.evaluation_rows} held-out faces · macro F1{" "}
                      {pct(r.macro_f1)} · accuracy {pct(r.accuracy)}.
                      Parameter-group split, seed 42.
                    </p>
                    <div className="gates">
                      {Object.entries(r.gates).map(([k, v]) => (
                        <div key={k}>
                          {v ? (
                            <CheckCircle2 size={15} className="green" />
                          ) : (
                            <Clock3 size={15} className="amber" />
                          )}
                          <span>{k}</span>
                          <Badge tone={v ? "green" : "amber"}>
                            {v ? "Passed" : "Pending"}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </>
                ) : null;
              })()
            ) : modal.startsWith("trace:") ? (
              (() => {
                const r = telemetry.requests.find(
                  (r) => r.id === modal.slice(6),
                );
                return r ? (
                  <>
                    <div className="eyebrow">ACTUAL REQUEST TRACE</div>
                    <h2>Inference execution</h2>
                    <Badge tone={r.success ? "green" : "red"}>
                      {r.success ? "Success" : "Failed"}
                    </Badge>
                    <pre className="trace-json">
                      {JSON.stringify(
                        { ...r, at: new Date(r.at * 1000).toISOString() },
                        null,
                        2,
                      )}
                    </pre>
                    <p>
                      Raw CAD and uploaded filenames are never stored in this
                      trace.
                    </p>
                  </>
                ) : null;
              })()
            ) : (
              <>
                <div className="model-symbol">
                  <Hexagon size={28} />
                </div>
                <div className="eyebrow">SHAPEOPS · LOCAL WORKSPACE</div>
                <h2>
                  Engineering intelligence,
                  <br />
                  with evidence.
                </h2>
                <p>
                  An original CAD inference platform combining OpenCascade
                  geometry processing, trained analytic-surface models,
                  immutable artifact identities and actual runtime telemetry.
                </p>
                <div className="doc-callout">
                  <Info size={18} />
                  <p>
                    This is a local development environment. Azure is not
                    provisioned. Production promotion is disabled. Sample
                    geometry is labeled; metrics come from executed requests.
                  </p>
                </div>
                <button
                  className="button primary"
                  onClick={() => {
                    setDoc("5-minute walkthrough");
                    navigate("Documentation");
                    setModal(null);
                  }}
                >
                  Take the five-minute walkthrough <ArrowRight size={15} />
                </button>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
function LayersIcon() {
  return <Boxes size={16} />;
}
createRoot(document.getElementById("root")!).render(<App />);
