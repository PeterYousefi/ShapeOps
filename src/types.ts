export type Face = {
  id: number;
  surface: string;
  prediction: string;
  confidence: number;
  probabilities?: Record<string, number>;
  comparison_confidence?: number | null;
  area: number;
  edges: number;
  positions: number[];
  candidate: string | null;
  disagreement: boolean;
};
export type Result = {
  faces: Face[];
  name: string;
  source: string;
  face_count: number;
  edge_count: number;
  volume: number;
  bounds: number[];
  model: string;
  checksum: string;
  trace_id: string;
  latency_ms: number;
  parse_ms: number;
  execution_ms: number;
  confidence: number;
  ood: boolean;
  ood_score: number;
  ood_contributions: { feature: string; deviation: number }[];
  disagreements: number;
  comparison_model: string | null;
};
export type Registry = {
  id: string;
  stage: string;
  framework: string;
  runtime: string;
  algorithm: string;
  checksum: string;
  dataset_hash: string;
  license: string;
  training_rows: number;
  evaluation_rows: number;
  accuracy: number;
  macro_f1: number;
  heldout_log_loss: number;
  package_checksum: string;
  git_commit: string;
  classes: string[];
  limitations: string;
  gates: Record<string, boolean>;
  parameters: Record<string, unknown>;
};
export type RequestRow = {
  id: string;
  at: number;
  source: string;
  model: string;
  success: number;
  latency: number;
  parse: number;
  execution: number;
  faces: number;
  confidence: number;
  ood: number;
  error: string;
};
export type Telemetry = {
  total: number;
  successful: number;
  failed: number;
  p50: number | null;
  p95: number | null;
  ood_rate: number | null;
  origin: string;
  requests: RequestRow[];
  throughput_per_minute: number;
};
export type Drill = {
  id: string;
  at: number;
  passed: boolean;
  duration_ms: number;
  scope: string;
  checks: { name: string; passed: boolean }[];
};
export type Operations = {
  active: string;
  candidate: string;
  environment: string;
  production: string;
  release_history: unknown[];
  drills: Drill[];
  promotion: string;
};
export const COLORS: Record<string, string> = {
  Planar: "#7b9fc5",
  Cylindrical: "#6db8a7",
  Conical: "#99bdb4",
  Spherical: "#e7a85f",
  Toroidal: "#c28d76",
  Other: "#93a7a0",
};

export type DriftFeature = {
  name: string;
  value: number;
  reference_mean: number;
  reference_scale: number;
  deviation: number;
};
export type DriftObservation = {
  id: string;
  at: number;
  source: "sample" | "upload";
  model: string;
  reference_id: string;
  reference_scope: string;
  reference_parts: number;
  threshold: number;
  warning: boolean;
  ood_score: number;
  ood: boolean;
  features: DriftFeature[];
};
export type DriftHistory = { origin: string; observations: DriftObservation[] };
export type CandidateJob = {
  id: string;
  started_at: number;
  finished_at: number | null;
  status: "running" | "succeeded" | "failed" | "timed_out" | "interrupted";
  scope: string;
  candidate: (Registry & { package_id: string; run_id: string }) | null;
};
export type CandidateHistory = { origin: string; jobs: CandidateJob[] };
export type TrainingRun = {
  id: string;
  started_at: number;
  completed_at: number;
  models: { model_id: string; package_id: string }[];
};
export type TrainingHistory = { origin: string; runs: TrainingRun[] };
export type TrainingFailure = {
  id: string;
  started_at: number;
  failed_at: number;
  category: "validation" | "storage" | "execution";
};
export type FailureHistory = { origin: string; failures: TrainingFailure[] };

export type ReleaseRecord = {
  id: string;
  at: number;
  operator: string;
  candidate_id: string;
  package_id: string;
  gates: Record<string, boolean>;
  status: "approved" | "rejected";
  rationale: string;
};
export type ReleasesHistory = { origin: string; releases: ReleaseRecord[] };
