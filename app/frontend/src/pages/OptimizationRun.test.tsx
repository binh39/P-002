import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import OptimizationRun from "@/pages/OptimizationRun";

const repositories = vi.hoisted(() => ({
  experiments: {
    getOptimizationRun: vi.fn(),
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
  });

  it("renders the candidate and real optimization metrics", async () => {
    render(<OptimizationRun />, { wrapper: Wrapper });

    expect(await screen.findByText("isort optimization")).toBeInTheDocument();
    expect(screen.getByText("Sparse baseline initial prompt")).toBeInTheDocument();
    expect(screen.getByText("Optimized initial prompt")).toBeInTheDocument();
    expect(screen.getByText("Baseline prompt")).toBeInTheDocument();
    expect(screen.getByText("Final selected prompt")).toBeInTheDocument();
    expect(screen.getByText("+0.500")).toBeInTheDocument();
    expect(screen.getByText("Locked baseline vs optimized result")).toBeInTheDocument();
    expect(screen.getByText("Optimized prompt promoted")).toBeInTheDocument();
    expect(screen.getByText("candidate_prompt.json")).toBeInTheDocument();
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
});
