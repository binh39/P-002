import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PromptRegistryList } from "@/domain/experiments";

const registry: PromptRegistryList = {
  items: [
    {
      experimentId: "experiment-1",
      experimentName: "isort prompt optimization",
      projectIds: ["sample:isort"],
      projectNames: ["isort"],
      status: "approved",
      baseline: {
        id: "experiment-1:baseline",
        experimentId: "experiment-1",
        role: "baseline",
        origin: "initial_baseline",
        promptDigest: "baseline-digest",
        prompt: { initial: "baseline", error: "error {error}" },
        sourceSnapshotDigest: "source",
        datasetDigest: "dataset",
        splitSeed: 7,
        runnerProtocolVersion: 3,
        coverupModel: "gemini/gemini-2.5-flash",
        optimizeModel: "gemini/gemini-2.5-pro",
        metrics: { score: null, statementCoverage: null, branchCoverage: null, passRate: null },
        estimatedCostUsd: null,
        createdAt: "2026-08-18T00:00:00Z",
      },
      optimized: null,
      baselineMetrics: { score: 0.7, statementCoverage: 0.75, branchCoverage: 0.65, passRate: 1 },
      optimizedMetrics: {
        score: null,
        statementCoverage: null,
        branchCoverage: null,
        passRate: null,
      },
      absoluteGain: null,
      createdAt: "2026-08-18T00:00:00Z",
      updatedAt: "2026-08-18T00:00:00Z",
    },
  ],
  total: 1,
  offset: 0,
  limit: 50,
};

vi.mock("@/app/providers", () => ({
  useRepositories: () => ({ promptRegistry: { list: async () => registry } }),
}));

import Registry from "@/pages/Registry";

describe("Registry", () => {
  it("renders one real registry row per experiment instead of prompt fixture rows", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <Registry />
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Prompt Registry" })).toBeInTheDocument();
    expect(container.firstElementChild).toHaveClass("platform-page", "registry-page");
    expect(screen.getByRole("table")).toHaveClass("registry-table");
    expect(screen.getByText("isort prompt optimization")).toBeInTheDocument();
    expect(screen.queryByText("PRG-031")).not.toBeInTheDocument();
  });
});
