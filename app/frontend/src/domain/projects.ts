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
  environmentFingerprint?: string | null;
  failureStage?:
    | "metadata"
    | "resolve"
    | "build"
    | "collect"
    | "test"
    | "coverage"
    | "internal"
    | null;
  errorCode?: string | null;
  retryable: boolean;
  runnerProfile?: {
    name: string;
    pytestVersion: string | null;
    coverageVersion: string | null;
  } | null;
  conflicts: Array<{ package: string; requestedVersions: string[]; sources: string[] }>;
}

export type BuildStatus = "not_started" | "queued" | "building" | "ready" | "failed";
export type ExecutionStatus = "not_started" | "queued" | "running" | "succeeded" | "failed";

export interface ProjectSettingsInput {
  runtime?: {
    python_version?: string;
    working_directory?: string;
    source_directory?: string;
    cpu?: number;
    memory_mb?: number;
    run_timeout_seconds?: number;
    maximum_workers?: number;
  };
  tests?: {
    framework?: "pytest" | "unittest";
    test_directory?: string;
    test_pattern?: string;
    per_test_timeout_seconds?: number;
    retry_count?: number;
  };
  coverage?: {
    statement_enabled?: boolean;
    branch_enabled?: boolean;
    config_file?: string | null;
    include_pattern?: string;
    omit_pattern?: string;
    source_package?: string;
  };
  security?: {
    network_access?: boolean;
    read_only_source?: boolean;
    allowed_environment_variables?: string[];
    maximum_output_bytes?: number;
  };
}

export interface PythonProject {
  id: string;
  name: string;
  description: string;
  python: string;
  requestedPython?: string;
  detectedPython?: string | null;
  resolvedPython?: string | null;
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
  runtimeBuildStatus?: BuildStatus;
  runtimeExecutionStatus?: ExecutionStatus;
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
  runtimeEnvironmentId?: string;
  runtimeEnvironmentName?: string;
  pythonVersion: string;
}

export interface RuntimeCapability {
  pythonVersion: string;
  image: string;
  job: string;
  healthy: boolean;
}
