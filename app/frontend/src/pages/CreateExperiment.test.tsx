import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CreateExperiment from "@/pages/CreateExperiment";

const navigate = vi.fn();
const auth = vi.hoisted(() => ({
  user: { email: "member@example.com" },
}));
const repositories = vi.hoisted(() => ({
  projects: {
    list: vi.fn(),
    listSamples: vi.fn(),
    listFunctions: vi.fn(),
  },
  experiments: {
    list: vi.fn(),
    create: vi.fn(),
    requestOptimization: vi.fn(),
  },
}));

vi.mock("@/app/providers", () => ({ useRepositories: () => repositories }));
vi.mock("@/auth/AuthProvider", () => ({ useAuth: () => auth }));
vi.mock("wouter", () => ({ useLocation: () => ["/experiments/new", navigate] }));

const project = {
  id: "project-1",
  name: "isort",
  description: "Import sorter",
  python: "3.11",
  commit: "9262aa8",
  branch: "main",
  files: 10,
  functions: 3,
  statements: 50,
  branches: 12,
  status: "ready" as const,
  analyzedAt: "Now",
  testCommand: "pytest",
  sourceDir: "isort",
  testDir: "tests",
  runtimeStatus: "runtime_ready" as const,
  runtimeEnvironmentId: "sample-runtime",
  runtimeEnvironmentName: "Bundled sample environment",
};
const uploadedProject = {
  ...project,
  id: "project-2",
  name: "uploaded-project",
  runtimeEnvironmentId: "uploaded-runtime",
  runtimeEnvironmentName: "Uploaded Python 3.12 runtime",
};
const functions = Array.from({ length: 3 }, (_, index) => ({
  id: `fn-${index + 1}`,
  project: "project-1",
  file: "isort/api.py",
  className: "",
  name: `sort_code_string_${index + 1}`,
  lines: "10-20",
  loc: 11,
  statements: 8 + index,
  branches: 2 + index,
  status: "Valid" as const,
}));

function Wrapper({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      {children}
    </QueryClientProvider>
  );
}

describe("create experiment wizard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.user.email = "member@example.com";
    repositories.projects.list.mockResolvedValue([]);
    repositories.projects.listSamples.mockResolvedValue([project]);
    repositories.projects.listFunctions.mockResolvedValue(functions);
    repositories.experiments.list.mockResolvedValue([]);
    repositories.experiments.create.mockResolvedValue({ id: "experiment-1" });
    repositories.experiments.requestOptimization.mockResolvedValue({ id: "optimization-1" });
  });

  it("creates an experiment and queues optimization with baseline as candidate zero", async () => {
    render(<CreateExperiment />, { wrapper: Wrapper });

    fireEvent.click(await screen.findByRole("button", { name: /isort/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    await screen.findByText(/3 valid functions available/i);
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /create and optimize/i }));

    await waitFor(() =>
      expect(repositories.experiments.create).toHaveBeenCalledWith(
        expect.objectContaining({
          projectIds: ["project-1"],
          name: "isort prompt optimization",
          samplingMethod: "random",
          maxTargets: 3,
          randomSeed: 115,
          settings: expect.objectContaining({
            maxAttempts: 3,
            maxMetricCalls: 10,
            reflectionMinibatchSize: 3,
          }),
        }),
      ),
    );
    expect(repositories.experiments.requestOptimization).toHaveBeenCalledWith("experiment-1");
    expect(navigate).toHaveBeenCalledWith("/optimization-runs/optimization-1");
  });

  it("requires an analyzed project before continuing", async () => {
    render(<CreateExperiment />, { wrapper: Wrapper });

    await screen.findByRole("button", { name: /isort/i });
    expect(screen.getByRole("button", { name: /continue/i })).toBeDisabled();
  });

  it("allows projects with independent runtime environments in one experiment", async () => {
    repositories.projects.list.mockResolvedValue([uploadedProject]);

    render(<CreateExperiment />, { wrapper: Wrapper });

    fireEvent.click(await screen.findByRole("button", { name: /isort/i }));
    fireEvent.click(screen.getByRole("button", { name: /uploaded-project/i }));

    expect(screen.getByText("2 project(s) selected")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /continue/i })).toBeEnabled();
  });

  it("limits a standard account to twenty functions", async () => {
    repositories.projects.listFunctions.mockResolvedValue(
      Array.from({ length: 25 }, (_, index) => ({
        ...functions[index % functions.length],
        id: `fn-${index + 1}`,
        name: `function_${index + 1}`,
      })),
    );
    render(<CreateExperiment />, { wrapper: Wrapper });

    fireEvent.click(await screen.findByRole("button", { name: /isort/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    await screen.findByText(/25 valid functions available/i);
    expect(screen.getByLabelText(/Candidate functions/i)).toHaveAttribute("max", "20");
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /create and optimize/i }));

    await waitFor(() =>
      expect(repositories.experiments.create).toHaveBeenCalledWith(
        expect.objectContaining({ maxTargets: 20 }),
      ),
    );
  });

  it("shows the limits for a standard account", async () => {
    render(<CreateExperiment />, { wrapper: Wrapper });

    expect(await screen.findByText("Standard account limits")).toBeInTheDocument();
    expect(screen.getByText(/2,200 metric calls/i)).toBeInTheDocument();
    expect(screen.getByText(/one active experiment at a time/i)).toBeInTheDocument();
  });

  it("blocks a standard account while another experiment is active", async () => {
    repositories.experiments.list.mockResolvedValue([
      { id: "active-experiment", name: "Current optimization", status: "optimizing" },
    ]);
    render(<CreateExperiment />, { wrapper: Wrapper });

    expect(
      await screen.findByText(/Standard accounts can run only one experiment at a time/i),
    ).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: /isort/i }));
    expect(screen.getByRole("button", { name: /continue/i })).toBeDisabled();
  });

  it("removes the metric budget ceiling for the full-access account", async () => {
    auth.user.email = "admintest@gmail.com";
    render(<CreateExperiment />, { wrapper: Wrapper });

    expect(screen.queryByText("Standard account limits")).not.toBeInTheDocument();

    fireEvent.change(await screen.findByLabelText(/Runtime environment/i), {
      target: { value: "sample-runtime" },
    });
    fireEvent.click(await screen.findByRole("button", { name: /isort/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    await screen.findByText(/3 valid functions available/i);
    expect(screen.getByLabelText(/Candidate functions/i)).not.toHaveAttribute("max");
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    expect(screen.getByLabelText(/Max metric calls · Full access/i)).not.toHaveAttribute("max");
  });
});
