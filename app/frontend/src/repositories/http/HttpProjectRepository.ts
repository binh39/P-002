import { apiRequest } from "@/api/client";
import { getAccessToken } from "@/auth/tokenProvider";
import type {
  CreateProjectInput,
  ProjectFunction,
  PythonProject,
  ProjectStatus,
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
        }
      : null,
  };
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
      }),
    });
    const token = upload.upload_url.startsWith("/") ? await getAccessToken() : null;
    const uploadResponse = await fetch(upload.upload_url, {
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
        }),
      }),
    );
    return this.analyze(project.id);
  }

  async delete(projectId: string) {
    await apiRequest<void>(`/projects/${projectId}`, { method: "DELETE" });
  }
}
