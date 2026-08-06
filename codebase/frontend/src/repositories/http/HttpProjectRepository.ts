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
  status: "uploaded" | "ready" | "warning" | "failed";
  settings: {
    runtime: { python_version: string; source_directory: string };
    tests: { test_directory: string; test_command: string };
  };
  python_file_count: number;
  function_count: number;
  statement_count: number;
  branch_count: number;
  analyzed_at: string | null;
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

function mapStatus(status: ApiProject["status"]): ProjectStatus {
  if (status === "ready") return "ready";
  if (status === "uploaded") return "analyzing";
  return "warning";
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
    testCommand: project.settings.tests.test_command,
    sourceDir: project.settings.runtime.source_directory,
    testDir: project.settings.tests.test_directory,
  };
}

export class HttpProjectRepository implements ProjectRepository {
  async list(signal?: AbortSignal) {
    const response = await apiRequest<ApiProjectList>("/projects", { signal });
    return response.items.map(mapProject);
  }

  async get(projectId: string, signal?: AbortSignal) {
    return mapProject(await apiRequest<ApiProject>(`/projects/${projectId}`, { signal }));
  }

  listFunctions(projectId: string, signal?: AbortSignal) {
    return apiRequest<ProjectFunction[]>(`/projects/${projectId}/functions`, { signal });
  }

  getFunctionSource(projectId: string, functionId: string, signal?: AbortSignal) {
    return apiRequest<{ source: string }>(`/projects/${projectId}/functions/${functionId}/source`, {
      signal,
    }).then((response) => response.source);
  }

  async create(input: CreateProjectInput) {
    const upload = await apiRequest<ApiUpload>("/uploads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: input.file.name,
        content_type: input.file.type || "application/zip",
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
    return mapProject(
      await apiRequest<ApiProject>("/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: input.name,
          description: input.description,
          upload_id: upload.id,
          branch: input.branch,
          commit: input.commit || null,
        }),
      }),
    );
  }
}
