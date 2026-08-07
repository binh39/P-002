import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CreateExperiment from "@/pages/CreateExperiment";

const navigate = vi.fn();
const repositories = vi.hoisted(() => ({
  projects: {
    list: vi.fn(),
    listSamples: vi.fn(),
    listFunctions: vi.fn(),
  },
  experiments: {
    create: vi.fn(),
    requestBaseline: vi.fn(),
  },
}));

vi.mock("@/app/providers", () => ({ useRepositories: () => repositories }));
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
    repositories.projects.listSamples.mockResolvedValue([project]);
    repositories.projects.listFunctions.mockResolvedValue(functions);
    repositories.experiments.create.mockResolvedValue({ id: "experiment-1" });
    repositories.experiments.requestBaseline.mockResolvedValue({ id: "run-1" });
  });

  it("creates a real experiment and queues its baseline", async () => {
    render(<CreateExperiment />, { wrapper: Wrapper });

    fireEvent.click(await screen.findByRole("button", { name: /isort/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    await screen.findByText(/3 valid functions available/i);
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    fireEvent.click(screen.getByRole("button", { name: /create and run baseline/i }));

    await waitFor(() =>
      expect(repositories.experiments.create).toHaveBeenCalledWith(
        expect.objectContaining({
          projectId: "project-1",
          name: "isort prompt optimization",
          targetFunctionIds: expect.arrayContaining(["fn-1", "fn-2", "fn-3"]),
        }),
      ),
    );
    expect(repositories.experiments.requestBaseline).toHaveBeenCalledWith("experiment-1");
    expect(navigate).toHaveBeenCalledWith("/runs/run-1");
  });

  it("requires an analyzed project before continuing", async () => {
    render(<CreateExperiment />, { wrapper: Wrapper });

    await screen.findByRole("button", { name: /isort/i });
    expect(screen.getByRole("button", { name: /continue/i })).toBeDisabled();
  });
});
