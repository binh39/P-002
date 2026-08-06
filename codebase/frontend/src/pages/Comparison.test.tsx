import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Comparison from "@/pages/Comparison";

const repositories = vi.hoisted(() => ({
  experiments: {
    getComparisonRun: vi.fn(),
    get: vi.fn(),
    downloadComparisonArtifact: vi.fn(),
  },
}));

vi.mock("@/app/providers", () => ({ useRepositories: () => repositories }));
vi.mock("wouter", () => ({
  useParams: () => ({ runId: "comparison-1" }),
  useLocation: () => ["/comparison-runs/comparison-1", vi.fn()],
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

describe("comparison run", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    repositories.experiments.getComparisonRun.mockResolvedValue({
      id: "comparison-1",
      experimentId: "experiment-1",
      optimizationRunId: "optimization-1",
      status: "in_review",
      baselinePromptDigest: "parent-digest",
      candidatePromptDigest: "candidate-digest",
      testTargetIds: ["fn-1"],
      replicateCount: 2,
      baselineMetrics: {
        score: 0.2,
        statementCoverage: 0.3,
        branchCoverage: 0.1,
        passRate: 1,
        latencySeconds: 4,
        sampleCount: 2,
        timeoutCount: 0,
        flakyTargets: [],
      },
      candidateMetrics: {
        score: 0.7,
        statementCoverage: 0.8,
        branchCoverage: 0.6,
        passRate: 1,
        latencySeconds: 5,
        sampleCount: 2,
        timeoutCount: 0,
        flakyTargets: [],
      },
      absoluteGain: 0.5,
      relativeGain: 2.5,
      promotionEligible: true,
      decisionReason: "Candidate improved locked-test coverage and passed all hard gates",
      artifacts: ["final_validation.json"],
      promptVersionId: "version-1",
      errorMessage: null,
      createdAt: "2026-08-06T00:00:00Z",
      startedAt: "2026-08-06T00:00:01Z",
      finishedAt: "2026-08-06T00:01:00Z",
    });
    repositories.experiments.get.mockResolvedValue({
      id: "experiment-1",
      name: "isort comparison",
    });
  });

  it("renders production comparison metrics, decision, and artifact", async () => {
    render(<Comparison />, { wrapper: Wrapper });

    expect(await screen.findByText("isort comparison")).toBeInTheDocument();
    expect(screen.getAllByText("+0.500")).toHaveLength(2);
    expect(screen.getByText("Candidate passed the promotion gates")).toBeInTheDocument();
    expect(
      screen.getByText("Candidate improved locked-test coverage and passed all hard gates"),
    ).toBeInTheDocument();
    expect(screen.getByText("final_validation.json")).toBeInTheDocument();
    expect(screen.getByText("version-1")).toBeInTheDocument();
  });
});
