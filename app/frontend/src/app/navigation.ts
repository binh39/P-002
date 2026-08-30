import type { NavigationId } from "@/components/Sidebar";

export const pathByNavigationId: Record<NavigationId, string> = {
  dashboard: "/dashboard",
  reviews: "/reviews",
  projects: "/projects",
  experiments: "/experiments",
  coverage: "/docs/coverage",
  registry: "/prompts",
  testCases: "/test-cases",
  workspaceSettings: "/workspace-settings",
  settings: "/settings",
};

export function currentNavigationId(pathname: string): NavigationId {
  if (pathname.startsWith("/reviews")) return "reviews";
  if (pathname.startsWith("/projects")) return "projects";
  if (
    pathname.startsWith("/experiments") ||
    pathname.startsWith("/runs") ||
    pathname.startsWith("/optimization-runs")
  ) {
    return "experiments";
  }
  if (pathname.startsWith("/docs/coverage")) return "coverage";
  if (pathname.startsWith("/prompts")) return "registry";
  if (pathname.startsWith("/test-cases") || pathname.startsWith("/test-suites")) return "testCases";
  if (pathname.startsWith("/workspace-settings")) return "workspaceSettings";
  if (pathname.startsWith("/settings")) return "settings";
  return "dashboard";
}
