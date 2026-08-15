import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AppLayout from "@/app/AppLayout";

const routerState = vi.hoisted(() => ({ location: "/projects" }));

vi.mock("wouter", () => ({
  useLocation: () => [routerState.location, vi.fn()],
}));

vi.mock("@/auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { displayName: "Test User", email: "test@example.com" },
    signOut: vi.fn(),
  }),
}));

vi.mock("@/components/Sidebar", () => ({ default: () => <aside>Sidebar</aside> }));
vi.mock("@/components/TopNav", () => ({ default: () => <header>Top navigation</header> }));
vi.mock("@/components/AppFooter", () => ({ default: () => <footer>Footer</footer> }));

describe("AppLayout", () => {
  it("returns the content area to the top after route navigation", () => {
    const queryClient = new QueryClient();
    const view = render(
      <QueryClientProvider client={queryClient}>
        <AppLayout>
          <div>Projects page</div>
        </AppLayout>
      </QueryClientProvider>,
    );

    const projectsContent = screen.getByRole("main");
    projectsContent.scrollTop = 640;
    projectsContent.scrollLeft = 20;
    routerState.location = "/experiments";

    view.rerender(
      <QueryClientProvider client={queryClient}>
        <AppLayout>
          <div>Experiments page</div>
        </AppLayout>
      </QueryClientProvider>,
    );

    const experimentsContent = screen.getByRole("main");
    expect(experimentsContent).not.toBe(projectsContent);
    expect(experimentsContent.scrollTop).toBe(0);
    expect(experimentsContent.scrollLeft).toBe(0);
  });
});
