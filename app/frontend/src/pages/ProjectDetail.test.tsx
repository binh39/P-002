import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PythonProject } from "@/domain/projects";
import ProjectDetail from "@/pages/ProjectDetail";

const state = vi.hoisted(() => ({
  get: vi.fn(),
  listFunctions: vi.fn(),
  getFunctionSource: vi.fn(),
  analyze: vi.fn(),
  prepareRuntime: vi.fn(),
  retryBuild: vi.fn(),
  retryExecution: vi.fn(),
  runtimeCapabilities: vi.fn(),
  validateSettings: vi.fn(),
  updateSettings: vi.fn(),
  delete: vi.fn(),
  navigate: vi.fn(),
}));

vi.mock("@/app/providers", () => ({ useRepositories: () => ({ projects: state }) }));
vi.mock("wouter", () => ({
  useParams: () => ({ projectId: "project-1" }),
  useLocation: () => ["/projects/project-1", state.navigate],
}));

const project: PythonProject = {
  id: "project-1",
  name: "isort",
  description: "Import sorter",
  python: "3.12",
  requestedPython: "3.12",
  commit: "abc123",
  branch: "main",
  files: 10,
  functions: 20,
  statements: 100,
  branches: 20,
  status: "ready",
  analyzedAt: "Today",
  testCommand: "pytest -q",
  sourceDir: "src",
  testDir: "tests",
  runtimeStatus: "runtime_failed",
  runtimeBuildStatus: "failed",
  runtimeExecutionStatus: "not_started",
  runtimeReport: {
    dependencyFiles: ["requirements.txt"],
    installStrategy: "uv",
    collectedTests: 0,
    statementCoverage: null,
    branchCoverage: null,
    error: "coverage versions conflict",
    retryable: false,
    failureStage: "resolve",
    errorCode: "DEPENDENCY_CONFLICT",
    conflicts: [
      {
        package: "coverage",
        requestedVersions: ["7.15.2", "7.10.7"],
        sources: ["tool", "requirements.txt"],
      },
    ],
  },
};

function renderPage() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <ProjectDetail />
    </QueryClientProvider>,
  );
}

describe("ProjectDetail runtime admission", () => {
  beforeEach(() => {
    for (const mock of Object.values(state)) mock.mockReset();
    state.get.mockResolvedValue(project);
    state.listFunctions.mockResolvedValue([]);
    state.runtimeCapabilities.mockResolvedValue([
      { pythonVersion: "3.12", image: "promptopt-sandbox:py3.12", job: "runtime", healthy: true },
      { pythonVersion: "3.13", image: "promptopt-sandbox:py3.13", job: "runtime", healthy: false },
    ]);
    state.validateSettings.mockResolvedValue(undefined);
    state.updateSettings.mockResolvedValue({ ...project, runtimeStatus: "runtime_queued" });
  });

  it("shows deterministic conflict details without a retry action", async () => {
    renderPage();

    expect(await screen.findByText("DEPENDENCY_CONFLICT", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("7.15.2 versus 7.10.7", { exact: false })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /retry transient/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Fix configuration" })).toBeInTheDocument();
  });

  it("validates and saves only healthy sandbox settings", async () => {
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Python settings" }));

    expect(await screen.findByRole("option", { name: "Python 3.12" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Python 3.13" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Runtime image")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Install command")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Source directory"), { target: { value: "package" } });
    fireEvent.click(screen.getByRole("button", { name: "Validate configuration" }));
    await waitFor(() =>
      expect(state.validateSettings).toHaveBeenCalledWith(
        "project-1",
        expect.objectContaining({
          runtime: expect.objectContaining({ source_directory: "package" }),
        }),
      ),
    );

    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
    await waitFor(() => expect(state.updateSettings).toHaveBeenCalledTimes(1));
  });
});
