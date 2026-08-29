import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PythonProject } from "@/domain/projects";
import Projects from "@/pages/Projects";

const state = vi.hoisted(() => ({
  navigate: vi.fn(),
  list: vi.fn(),
  listSamples: vi.fn(),
  create: vi.fn(),
}));

vi.mock("@/app/providers", () => ({
  useRepositories: () => ({
    projects: {
      list: state.list,
      listSamples: state.listSamples,
      create: state.create,
    },
  }),
}));
vi.mock("wouter", () => ({ useLocation: () => ["/projects", state.navigate] }));

const importedProject: PythonProject = {
  id: "project-1",
  name: "payments",
  description: "Payment service",
  python: "3.11",
  commit: "Not recorded",
  branch: "main",
  files: 0,
  functions: 0,
  statements: 0,
  branches: 0,
  status: "analyzing",
  analyzedAt: "Analysis pending",
  testCommand: "pytest -q",
  sourceDir: "src",
  testDir: "tests",
};

function renderPage() {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <Projects />
    </QueryClientProvider>,
  );
}

describe("Projects", () => {
  beforeEach(() => {
    state.navigate.mockReset();
    state.list.mockReset().mockResolvedValue([]);
    state.listSamples.mockReset().mockResolvedValue([]);
    state.create.mockReset().mockResolvedValue(importedProject);
  });

  it("keeps samples separate and opens the private ZIP import flow", async () => {
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: "+ Create project" }));

    expect(screen.getByRole("dialog", { name: "Create project" })).toBeInTheDocument();
    expect(screen.getByText("My projects")).toBeInTheDocument();
    expect(screen.getByText("Sample projects")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /create experiment/i })).not.toBeInTheDocument();
  });

  it("validates the archive before calling the repository", async () => {
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "+ Create project" }));
    fireEvent.change(screen.getByLabelText("Project name"), { target: { value: "payments" } });
    fireEvent.click(screen.getByRole("button", { name: "Upload and prepare" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Choose a ZIP archive.");
    expect(state.create).not.toHaveBeenCalled();
  });

  it("keeps optional metadata collapsed and does not ask for a shared runtime label", async () => {
    state.list.mockResolvedValue([
      {
        ...importedProject,
        status: "ready",
        runtimeStatus: "runtime_ready",
        runtimeEnvironmentId: "environment-1",
        runtimeEnvironmentName: "Shared Python 3.12",
      },
    ]);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "+ Create project" }));

    const advanced = screen.getByText("Advanced details").closest("details");
    expect(advanced).not.toHaveAttribute("open");
    expect(screen.queryByLabelText("Environment name")).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: /Runtime label/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("Advanced details"));
    expect(advanced).toHaveAttribute("open");
    expect(screen.getByLabelText("Branch or source label")).toHaveValue("main");
    expect(screen.getByLabelText("Commit or version")).toBeInTheDocument();
    expect(screen.getByLabelText("Description")).toBeInTheDocument();
  });

  it("keeps admission details off the project card", async () => {
    state.list.mockResolvedValue([
      {
        ...importedProject,
        status: "ready",
        runtimeStatus: "runtime_failed",
        runtimeReport: {
          dependencyFiles: ["pyproject.toml"],
          installStrategy: "",
          collectedTests: 0,
          statementCoverage: null,
          branchCoverage: null,
          error: "Project requires Python >=3.14, but no compatible runtime is deployed.",
        },
      },
    ]);

    renderPage();

    expect(await screen.findByText("Environment rejected")).toBeInTheDocument();
    expect(
      screen.queryByText("Project requires Python >=3.14, but no compatible runtime is deployed."),
    ).not.toBeInTheDocument();
  });

  it("uploads a ZIP and opens the queued project", async () => {
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "+ Create project" }));
    fireEvent.change(screen.getByLabelText("Project name"), { target: { value: " payments " } });
    fireEvent.change(screen.getByLabelText("Python source ZIP"), {
      target: { files: [new File(["PK"], "payments.zip", { type: "application/zip" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Upload and prepare" }));

    await waitFor(() =>
      expect(state.create).toHaveBeenCalledWith(
        expect.objectContaining({ name: "payments", branch: "main" }),
      ),
    );
    await waitFor(() => expect(state.navigate).toHaveBeenCalledWith("/projects/project-1"));
  });
});
