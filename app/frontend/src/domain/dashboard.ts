export type ExperimentStatus = "completed" | "running" | "pending" | "failed";

export interface CoveragePoint {
  day: string;
  branch: number;
  statement: number;
}

export interface Kpi {
  label: string;
  value: string;
  delta: string;
  trend: "up" | "down" | "neutral";
  icon: "experiments" | "running" | "branch" | "statement";
}

export interface ExperimentSummary {
  id: string;
  name: string;
  model: string;
  branchCoverage: number;
  statementCoverage: number;
  status: ExperimentStatus;
  updatedAt: string;
}

export interface QuickStat {
  label: string;
  value: string;
}

export interface DashboardSnapshot {
  projectName: string;
  asOf: string;
  coverage: CoveragePoint[];
  kpis: Kpi[];
  quickStats: QuickStat[];
  experiments: ExperimentSummary[];
}
