import type { NavigationId } from "@/components/Sidebar";

export const pathByNavigationId: Record<NavigationId, string> = {
  dashboard: "/dashboard",
  projects: "/projects",
  experiments: "/experiments",
  datasets: "/datasets",
  coverage: "/docs/coverage",
  playground: "/playground",
  registry: "/prompts",
  settings: "/settings",
};

export function currentNavigationId(pathname: string): NavigationId {
  if (pathname.startsWith("/projects")) return "projects";
  if (
    pathname.startsWith("/experiments") ||
    pathname.startsWith("/runs") ||
    pathname.startsWith("/optimization-runs") ||
    pathname.startsWith("/comparison-runs")
  ) {
    return "experiments";
  }
  if (pathname.startsWith("/datasets")) return "datasets";
  if (pathname.startsWith("/docs/coverage")) return "coverage";
  if (pathname.startsWith("/playground")) return "playground";
  if (pathname.startsWith("/prompts")) return "registry";
  if (pathname.startsWith("/settings")) return "settings";
  return "dashboard";
}
