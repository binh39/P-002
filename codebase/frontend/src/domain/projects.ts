export type ProjectStatus = "ready" | "warning" | "analyzing";

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
  testCommand: string;
  sourceDir: string;
  testDir: string;
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
