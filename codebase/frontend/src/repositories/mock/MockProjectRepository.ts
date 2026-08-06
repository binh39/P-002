import { projectFunctions, pythonProjects, sourcePreview } from "@/mocks/fixtures/platform";
import type { CreateProjectInput } from "@/domain/projects";
import type { ProjectRepository } from "@/repositories/contracts/ProjectRepository";

async function delay(signal?: AbortSignal) {
  await new Promise<void>((resolve, reject) => {
    const timer = window.setTimeout(resolve, 180);
    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timer);
        reject(new DOMException("Request aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

export class MockProjectRepository implements ProjectRepository {
  private items = structuredClone(pythonProjects);

  async list(signal?: AbortSignal) {
    await delay(signal);
    return structuredClone(this.items);
  }

  async get(projectId: string, signal?: AbortSignal) {
    await delay(signal);
    const project = this.items.find((item) => item.id === projectId);
    if (!project) throw new Error("Project was not found");
    return structuredClone(project);
  }

  async listFunctions(projectId: string, signal?: AbortSignal) {
    await delay(signal);
    return structuredClone(projectFunctions.filter((item) => item.project === projectId));
  }

  async getFunctionSource(projectId: string, functionId: string, signal?: AbortSignal) {
    await delay(signal);
    const exists = projectFunctions.some(
      (item) => item.project === projectId && item.id === functionId,
    );
    if (!exists) throw new Error("Function source was not found");
    return sourcePreview;
  }

  async create(input: CreateProjectInput) {
    await delay();
    const project = {
      id: crypto.randomUUID(),
      name: input.name,
      description: input.description,
      python: "3.11",
      commit: input.commit || "Not recorded",
      branch: input.branch,
      files: 0,
      functions: 0,
      statements: 0,
      branches: 0,
      status: "analyzing" as const,
      analyzedAt: "Analysis pending",
      testCommand: "pytest -q",
      sourceDir: "src",
      testDir: "tests",
    };
    this.items.unshift(project);
    return structuredClone(project);
  }
}
