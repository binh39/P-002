import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import OptimizationRun from "@/pages/OptimizationRun";

const repositories = vi.hoisted(() => ({
  experiments: {
    getOptimizationRun: vi.fn(),
    cancelOptimization: vi.fn(),
    getOptimizationEvolution: vi.fn(),
    get: vi.fn(),
    downloadOptimizationArtifact: vi.fn(),
  },
}));

vi.mock("@/app/providers", () => ({ useRepositories: () => repositories }));
vi.mock("wouter", () => ({
  useParams: () => ({ runId: "optimization-1" }),
  useLocation: () => ["/optimization-runs/optimization-1", vi.fn()],
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

describe("optimization run", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    repositories.experiments.getOptimizationRun.mockResolvedValue({
      id: "optimization-1",
      experimentId: "experiment-1",
      status: "optimization_succeeded",
      parentPromptDigest: "parent",
      candidatePrompt: {
        initial: "Optimized initial prompt",
        error: "Optimized error prompt",
      },
      candidatePromptDigest: "candidate",
      baselineValidationScore: 0.2,
      candidateValidationScore: 0.7,
      candidateCount: 4,
      metricCalls: 8,
      finalComparison: {
        baselineMetrics: { score: 0.3 },
        candidateMetrics: { score: 0.6 },
        absoluteGain: 0.3,
        promoted: true,
        skipped: false,
        reason: null,
      },
      artifacts: ["candidate_prompt.json"],
      errorMessage: null,
      createdAt: "2026-08-06T00:00:00Z",
      startedAt: "2026-08-06T00:00:01Z",
      finishedAt: "2026-08-06T00:01:00Z",
    });
    repositories.experiments.get.mockResolvedValue({
      id: "experiment-1",
      name: "isort optimization",
      baselinePrompt: {
        initial: "Sparse baseline initial prompt",
        error: "Sparse baseline error prompt",
      },
      baselineRunId: "baseline-1",
      comparisonRunId: "comparison-1",
    });
    repositories.experiments.getOptimizationEvolution.mockResolvedValue({
      available: true,
      source: "cloud_run_stdout",
      message: "Parsed from Cloud Run stdout.",
      iterations: [
        {
          iteration: 0,
          strategy: "baseline",
          parentProgram: "Program 0",
          parentValidationScore: 0.2599,
          component: null,
          proposedPrompt: null,
          parentMinibatchSum: null,
          candidateMinibatchSum: null,
          decision: "Baseline evaluated",
          fullValidation: true,
          bestStatement: null,
          bestBranch: null,
          bestScore: 0.2599,
          bestCandidateChanged: true,
        },
        {
          iteration: 2,
          strategy: "reflective mutation",
          parentProgram: "Program 0",
          parentValidationScore: 0.2599,
          component: "error",
          proposedPrompt: "Repair the failing test.",
          parentMinibatchSum: 0.9625,
          candidateMinibatchSum: 0.9398,
          decision: "Rejected",
          fullValidation: false,
          bestStatement: 0.8198,
          bestBranch: 0.7707,
          bestScore: 0.8319,
          bestCandidateChanged: false,
        },
      ],
      metrics: [
        { iteration: 0, statement: null, branch: null, score: 0.2599 },
        { iteration: 2, statement: 0.8198, branch: 0.7707, score: 0.8319 },
      ],
    });
  });

  it("renders the candidate and real optimization metrics", async () => {
    render(<OptimizationRun />, { wrapper: Wrapper });

    expect(await screen.findByText("isort optimization")).toBeInTheDocument();
    expect(screen.getByText("Sparse baseline initial prompt")).toBeInTheDocument();
    expect(screen.getByText("Optimized initial prompt")).toBeInTheDocument();
    expect(screen.getByText("Baseline prompt")).toBeInTheDocument();
    expect(screen.getByText("Final selected prompt")).toBeInTheDocument();
    expect(screen.getByText("+0.500")).toBeInTheDocument();
    const resultsCard = screen.getByText("Evaluation results").closest("section");
    expect(resultsCard).not.toBeNull();
    expect(within(resultsCard!).getByText("Validation")).toBeInTheDocument();
    expect(within(resultsCard!).getByText("Final locked test")).toBeInTheDocument();
    expect(within(resultsCard!).getByText("Promoted")).toBeInTheDocument();
    expect(screen.getByText("candidate_prompt.json")).toBeInTheDocument();
    expect(screen.getByText("Live GEPA evolution")).toBeInTheDocument();
    expect(screen.getAllByText("Iteration 2")).toHaveLength(2);
    expect(screen.getByText("Repair the failing test.")).toBeInTheDocument();
    expect(screen.getByText("Parent minibatch sum")).toBeInTheDocument();
    expect(screen.getByText("Best validation candidate")).toBeInTheDocument();
    expect(
      screen.getByText(
        /micro-averaged over executable units for the same aggregate-best candidate/i,
      ),
    ).toBeInTheDocument();
  });

  it("shows the baseline as the final prompt when the proposal is not promoted", async () => {
    repositories.experiments.getOptimizationRun.mockResolvedValueOnce({
      ...(await repositories.experiments.getOptimizationRun()),
      finalComparison: {
        baselineMetrics: { score: 0.6 },
        candidateMetrics: { score: 0.5 },
        absoluteGain: -0.1,
        promoted: false,
        skipped: false,
        reason: null,
      },
    });

    render(<OptimizationRun />, { wrapper: Wrapper });

    expect(await screen.findByText("Baseline retained")).toBeInTheDocument();
    expect(await screen.findAllByText("Sparse baseline initial prompt")).toHaveLength(2);
    expect(screen.queryByText("Optimized initial prompt")).not.toBeInTheDocument();
  });

  it("cancels an active Cloud Run optimization from the running card", async () => {
    const activeRun = {
      ...(await repositories.experiments.getOptimizationRun()),
      status: "optimizing",
      finishedAt: null,
    };
    repositories.experiments.getOptimizationRun.mockResolvedValueOnce(activeRun);
    repositories.experiments.cancelOptimization.mockResolvedValue({
      ...activeRun,
      status: "cancelled",
      finishedAt: "2026-08-06T00:00:30Z",
    });
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<OptimizationRun />, { wrapper: Wrapper });
    fireEvent.click(await screen.findByRole("button", { name: "Stop optimization" }));

    expect(confirm).toHaveBeenCalledOnce();
    await waitFor(() => {
      expect(repositories.experiments.cancelOptimization).toHaveBeenCalledWith("optimization-1");
    });
    expect(await screen.findByText("Cancelled")).toBeInTheDocument();
    confirm.mockRestore();
  });
});
