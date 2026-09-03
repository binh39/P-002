import type {
  CreateProjectInput,
  ProjectFunction,
  ProjectSettingsInput,
  PythonProject,
  RuntimeCapability,
} from "@/domain/projects";

export interface ProjectRepository {
  list(signal?: AbortSignal): Promise<PythonProject[]>;
  listSamples(signal?: AbortSignal): Promise<PythonProject[]>;
  get(projectId: string, signal?: AbortSignal): Promise<PythonProject>;
  listFunctions(projectId: string, signal?: AbortSignal): Promise<ProjectFunction[]>;
  getFunctionSource(projectId: string, functionId: string, signal?: AbortSignal): Promise<string>;
  analyze(projectId: string): Promise<PythonProject>;
  prepareRuntime(projectId: string): Promise<PythonProject>;
  retryBuild(projectId: string): Promise<PythonProject>;
  retryExecution(projectId: string): Promise<PythonProject>;
  runtimeCapabilities(signal?: AbortSignal): Promise<RuntimeCapability[]>;
  validateSettings(projectId: string, settings: ProjectSettingsInput): Promise<void>;
  updateSettings(projectId: string, settings: ProjectSettingsInput): Promise<PythonProject>;
  create(input: CreateProjectInput): Promise<PythonProject>;
  delete(projectId: string): Promise<void>;
}
