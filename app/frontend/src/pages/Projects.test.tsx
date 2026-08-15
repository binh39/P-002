import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Projects from "@/pages/Projects";

const repositories = vi.hoisted(() => ({
  projects: {
    listSamples: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock("@/app/providers", () => ({ useRepositories: () => repositories }));
vi.mock("wouter", () => ({ useLocation: () => ["/projects", vi.fn()] }));

describe("Projects", () => {
  it("reserves project creation for the future import flow", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <Projects />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("button", { name: "Create project (coming soon)" }),
    ).toBeDisabled();
    expect(screen.queryByRole("button", { name: /create experiment/i })).not.toBeInTheDocument();
  });
});
