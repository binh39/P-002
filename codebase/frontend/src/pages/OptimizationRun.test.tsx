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
      candidatePrompt: { instructions: "Generate focused tests for the selected function." },
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
      baselineRunId: "baseline-1",
      comparisonRunId: "comparison-1",
    });
  });

  it("renders the candidate and real optimization metrics", async () => {
    render(<OptimizationRun />, { wrapper: Wrapper });

    expect(await screen.findByText("isort optimization")).toBeInTheDocument();
    expect(
      screen.getByText("Generate focused tests for the selected function."),
    ).toBeInTheDocument();
    expect(screen.getByText("+0.500")).toBeInTheDocument();
    expect(screen.getByText("Locked baseline vs optimized result")).toBeInTheDocument();
    expect(screen.getByText("Optimized prompt promoted")).toBeInTheDocument();
    expect(screen.getByText("candidate_prompt.json")).toBeInTheDocument();
  });
});
