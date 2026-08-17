import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Experiments from "@/pages/Experiments";

const mocks = vi.hoisted(() => ({
  navigate: vi.fn(),
  experiments: {
    list: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("@/app/providers", () => ({
  useRepositories: () => ({ experiments: mocks.experiments }),
}));
vi.mock("wouter", () => ({
  useLocation: () => ["/experiments", mocks.navigate],
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

describe("experiments list", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.experiments.list.mockResolvedValue([
      {
        id: "experiment-1",
        name: "Completed optimization",
        targetFunctionIds: ["target-1", "target-2"],
        datasetSplits: { train: ["target-1"], validation: ["target-2"] },
        status: "optimization_succeeded",
        optimizationEligible: true,
        optimizationRunId: "optimization-1",
        comparisonRunId: "comparison-1",
        updatedAt: "2026-08-10T17:00:00Z",
      },
    ]);
  });

  it("reopens a completed experiment at its evolution-rich optimization run", async () => {
    render(<Experiments />, { wrapper: Wrapper });

    fireEvent.click(await screen.findByRole("button", { name: "Open experiment" }));

    expect(mocks.navigate).toHaveBeenCalledWith("/optimization-runs/optimization-1");
  });

  it("does not link comparison-only experiments to the removed results page", async () => {
    mocks.experiments.list.mockResolvedValueOnce([
      {
        ...(await mocks.experiments.list())[0],
        optimizationRunId: null,
      },
    ]);

    render(<Experiments />, { wrapper: Wrapper });

    expect(await screen.findByText("Completed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open comparison" })).not.toBeInTheDocument();
  });
});
