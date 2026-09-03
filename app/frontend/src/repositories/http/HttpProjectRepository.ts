import { apiRequest } from "@/api/client";
import { getAccessToken } from "@/auth/tokenProvider";
import { env } from "@/config/env";
import type {
  CreateProjectInput,
  ProjectFunction,
  PythonProject,
  ProjectStatus,
  ProjectSettingsInput,
} from "@/domain/projects";
import type { ProjectRepository } from "@/repositories/contracts/ProjectRepository";

interface ApiProject {
  id: string;
  name: string;
  description: string;
  branch: string;
  commit: string | null;
  status: "uploaded" | "analyzing" | "ready" | "warning" | "failed";
  settings: {
    runtime: { python_version: string; source_directory: string };
    tests: { test_directory: string; test_command: string };
  };
  python_file_count: number;
  function_count: number;
  statement_count: number;
  branch_count: number;
  analyzed_at: string | null;
  analysis_error: string | null;
  runtime_environment_id: string | null;
  runtime_environment_name: string | null;
  runtime_bundle_object: string | null;
  runtime_dependency_fingerprint: string | null;
  requested_python_version?: string;
  detected_python_version?: string | null;
  resolved_python_version?: string | null;
  runtime_build_status?: "not_started" | "queued" | "building" | "ready" | "failed";
  runtime_execution_status?: "not_started" | "queued" | "running" | "succeeded" | "failed";
  runtime_status:
    | "not_requested"
    | "runtime_queued"
    | "runtime_preparing"
    | "runtime_ready"
    | "runtime_failed";
  runtime_report: {
    dependency_files: string[];
    install_strategy: string;
    collected_tests: number;
    statement_coverage: number | null;
    branch_coverage: number | null;
    error: string | null;
    dependency_fingerprint: string | null;
    environment_fingerprint?: string | null;
    failure_stage?:
      | "metadata"
      | "resolve"
      | "build"
      | "collect"
      | "test"
      | "coverage"
      | "internal"
      | null;
    error_code?: string | null;
    retryable?: boolean;
    runner_profile?: string | null;
    pytest_version?: string | null;
    coverage_version?: string | null;
    conflicts?: Array<{ package: string; requested_versions: string[]; sources: string[] }>;
  } | null;
}

interface ApiProjectList {
  items: ApiProject[];
  total: number;
}

interface ApiUpload {
  id: string;
  upload_url: string;
  method: string;
  headers: Record<string, string>;
}

interface ApiProjectFunction {
  id: string;
  project_id: string;
  file: string;
  class_name: string;
  name: string;
  start_line: number;
  end_line: number;
  loc: number;
  statements: number;
  branches: number;
  status: string;
}

interface ApiProjectFunctionList {
  items: ApiProjectFunction[];
  total: number;
}

interface ApiRuntimeCapabilities {
  items: Array<{ python_version: string; image: string; job: string; healthy: boolean }>;
}

function mapStatus(status: ApiProject["status"]): ProjectStatus {
  if (status === "ready") return "ready";
  if (status === "uploaded" || status === "analyzing") return "analyzing";
  if (status === "failed") return "failed";
  return "warning";
}

function mapFunction(item: ApiProjectFunction): ProjectFunction {
  return {
    id: item.id,
    project: item.project_id,
    file: item.file,
    className: item.class_name,
    name: item.name,
    lines: `${item.start_line}-${item.end_line}`,
    loc: item.loc,
    statements: item.statements,
    branches: item.branches,
    status: item.status === "Valid" ? "Valid" : "Warning",
  };
}

function mapProject(project: ApiProject): PythonProject {
  return {
    id: project.id,
    name: project.name,
    description: project.description,
    python: project.settings.runtime.python_version,
    requestedPython: project.requested_python_version ?? project.settings.runtime.python_version,
    detectedPython: project.detected_python_version,
    resolvedPython: project.resolved_python_version,
    commit: project.commit ?? "Not recorded",
    branch: project.branch,
    files: project.python_file_count,
    functions: project.function_count,
    statements: project.statement_count,
    branches: project.branch_count,
    status: mapStatus(project.status),
    analyzedAt: project.analyzed_at
      ? new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
          new Date(project.analyzed_at),
        )
      : "Analysis pending",
    analysisError: project.analysis_error,
    testCommand: project.settings.tests.test_command,
    sourceDir: project.settings.runtime.source_directory,
    testDir: project.settings.tests.test_directory,
    runtimeStatus: project.runtime_status,
    runtimeBuildStatus: project.runtime_build_status,
    runtimeExecutionStatus: project.runtime_execution_status,
    runtimeEnvironmentId: project.runtime_environment_id,
    runtimeEnvironmentName: project.runtime_environment_name,
    runtimeBundleObject: project.runtime_bundle_object,
    runtimeDependencyFingerprint: project.runtime_dependency_fingerprint,
    runtimeReport: project.runtime_report
      ? {
          dependencyFiles: project.runtime_report.dependency_files,
          installStrategy: project.runtime_report.install_strategy,
          collectedTests: project.runtime_report.collected_tests,
          statementCoverage: project.runtime_report.statement_coverage,
          branchCoverage: project.runtime_report.branch_coverage,
          error: project.runtime_report.error,
          dependencyFingerprint: project.runtime_report.dependency_fingerprint,
          environmentFingerprint: project.runtime_report.environment_fingerprint,
          failureStage: project.runtime_report.failure_stage,
          errorCode: project.runtime_report.error_code,
          retryable: project.runtime_report.retryable ?? false,
          runnerProfile: project.runtime_report.runner_profile
            ? {
                name: project.runtime_report.runner_profile,
                pytestVersion: project.runtime_report.pytest_version ?? null,
                coverageVersion: project.runtime_report.coverage_version ?? null,
              }
            : null,
          conflicts: (project.runtime_report.conflicts ?? []).map((conflict) => ({
            package: conflict.package,
            requestedVersions: conflict.requested_versions,
            sources: conflict.sources,
          })),
        }
      : null,
  };
}

export function resolveUploadUrl(
  uploadUrl: string,
  apiBaseUrl = env.apiBaseUrl,
  browserOrigin = globalThis.location?.origin ?? "http://localhost",
) {
  if (/^https?:\/\//i.test(uploadUrl)) return uploadUrl;
  const apiUrl = new URL(apiBaseUrl, `${browserOrigin.replace(/\/$/, "")}/`);
  return new URL(uploadUrl, apiUrl.origin).toString();
}

export class HttpProjectRepository implements ProjectRepository {
  async list(signal?: AbortSignal) {
    const response = await apiRequest<ApiProjectList>("/projects", { signal });
    return response.items.map(mapProject);
  }

  async listSamples(signal?: AbortSignal) {
    const response = await apiRequest<ApiProjectList>("/projects/samples", { signal });
    return response.items.map(mapProject);
  }

  async get(projectId: string, signal?: AbortSignal) {
    return mapProject(await apiRequest<ApiProject>(`/projects/${projectId}`, { signal }));
  }

  async listFunctions(projectId: string, signal?: AbortSignal) {
    const response = await apiRequest<ApiProjectFunctionList>(`/projects/${projectId}/functions`, {
      signal,
    });
    return response.items.map(mapFunction);
  }

  getFunctionSource(projectId: string, functionId: string, signal?: AbortSignal) {
    return apiRequest<{ source: string }>(`/projects/${projectId}/functions/${functionId}/source`, {
      signal,
    }).then((response) => response.source);
  }

  async analyze(projectId: string) {
    return mapProject(
      await apiRequest<ApiProject>(`/projects/${projectId}/analyze`, { method: "POST" }),
    );
  }

  async prepareRuntime(projectId: string) {
    return mapProject(
      await apiRequest<ApiProject>(`/projects/${projectId}/prepare-runtime`, { method: "POST" }),
    );
  }

  async retryBuild(projectId: string) {
    return mapProject(
      await apiRequest<ApiProject>(`/projects/${projectId}/retry-build`, { method: "POST" }),
    );
  }

  async retryExecution(projectId: string) {
    return mapProject(
      await apiRequest<ApiProject>(`/projects/${projectId}/retry-execution`, { method: "POST" }),
    );
  }

  async runtimeCapabilities(signal?: AbortSignal) {
    const response = await apiRequest<ApiRuntimeCapabilities>("/projects/runtime-capabilities", {
      signal,
    });
    return response.items.map((item) => ({
      pythonVersion: item.python_version,
      image: item.image,
      job: item.job,
      healthy: item.healthy,
    }));
  }

  async validateSettings(projectId: string, settings: ProjectSettingsInput) {
    await apiRequest(`/projects/${projectId}/settings/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
  }

  async updateSettings(projectId: string, settings: ProjectSettingsInput) {
    return mapProject(
      await apiRequest<ApiProject>(`/projects/${projectId}/settings`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      }),
    );
  }

  async create(input: CreateProjectInput) {
    const contentType = ["application/zip", "application/x-zip-compressed"].includes(
      input.file.type.toLowerCase(),
    )
      ? input.file.type.toLowerCase()
      : "application/zip";
    const upload = await apiRequest<ApiUpload>("/uploads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: input.file.name,
        content_type: contentType,
        size_bytes: input.file.size,
        settings: { runtime: { python_version: input.pythonVersion } },
      }),
    });
    const localUpload = !/^https?:\/\//i.test(upload.upload_url);
    const token = localUpload ? await getAccessToken() : null;
    const uploadResponse = await fetch(resolveUploadUrl(upload.upload_url), {
      method: upload.method,
      headers: {
        ...upload.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: input.file,
    });
    if (!uploadResponse.ok)
      throw new Error(`ZIP upload failed with status ${uploadResponse.status}`);

    await apiRequest(`/uploads/${upload.id}/complete`, { method: "POST" });
    const project = mapProject(
      await apiRequest<ApiProject>("/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: input.name,
          description: input.description,
          upload_id: upload.id,
          branch: input.branch,
          commit: input.commit || null,
          runtime_environment_id: input.runtimeEnvironmentId || null,
          runtime_environment_name: input.runtimeEnvironmentName || null,
          settings: { runtime: { python_version: input.pythonVersion } },
        }),
      }),
    );
    return this.analyze(project.id);
  }

  async delete(projectId: string) {
    await apiRequest<void>(`/projects/${projectId}`, { method: "DELETE" });
  }
}
