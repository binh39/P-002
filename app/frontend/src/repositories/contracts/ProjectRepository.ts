import type { CreateProjectInput, ProjectFunction, PythonProject } from "@/domain/projects";

export interface ProjectRepository {
  list(signal?: AbortSignal): Promise<PythonProject[]>;
  listSamples(signal?: AbortSignal): Promise<PythonProject[]>;
  get(projectId: string, signal?: AbortSignal): Promise<PythonProject>;
  listFunctions(projectId: string, signal?: AbortSignal): Promise<ProjectFunction[]>;
  getFunctionSource(projectId: string, functionId: string, signal?: AbortSignal): Promise<string>;
  analyze(projectId: string): Promise<PythonProject>;
  prepareRuntime(projectId: string): Promise<PythonProject>;
  create(input: CreateProjectInput): Promise<PythonProject>;
  delete(projectId: string): Promise<void>;
}
