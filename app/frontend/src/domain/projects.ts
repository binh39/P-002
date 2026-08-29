export type ProjectStatus = "ready" | "warning" | "analyzing" | "failed";
export type RuntimeStatus =
  | "not_requested"
  | "runtime_queued"
  | "runtime_preparing"
  | "runtime_ready"
  | "runtime_failed";

export interface RuntimeReport {
  dependencyFiles: string[];
  installStrategy: string;
  collectedTests: number;
  statementCoverage: number | null;
  branchCoverage: number | null;
  error: string | null;
  dependencyFingerprint?: string | null;
  executionMode?: string | null;
}

export interface PythonProject {
  id: string;
  name: string;
  description: string;
  python: string;
  commit: string;
  branch: string;
  files: number;
  functions: number;
  statements: number;
  branches: number;
  status: ProjectStatus;
  analyzedAt: string;
  analysisError?: string | null;
  testCommand: string;
  sourceDir: string;
  testDir: string;
  runtimeStatus?: RuntimeStatus;
  runtimeReport?: RuntimeReport | null;
  runtimeEnvironmentId?: string | null;
  runtimeEnvironmentName?: string | null;
  runtimeBundleObject?: string | null;
  runtimeDependencyFingerprint?: string | null;
}

export interface ProjectFunction {
  id: string;
  project: string;
  file: string;
  className: string;
  name: string;
  lines: string;
  loc: number;
  statements: number;
  branches: number;
  status: "Valid" | "Warning";
}

export interface CreateProjectInput {
  name: string;
  description: string;
  branch: string;
  commit?: string;
  file: File;
}
