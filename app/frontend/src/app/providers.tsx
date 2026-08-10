/* eslint-disable react-refresh/only-export-components */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, type PropsWithChildren, useContext, useState } from "react";

import { env } from "@/config/env";
import type { DashboardRepository } from "@/repositories/contracts/DashboardRepository";
import type { ExperimentRepository } from "@/repositories/contracts/ExperimentRepository";
import type { ProjectRepository } from "@/repositories/contracts/ProjectRepository";
import type { PromptVersionRepository } from "@/repositories/contracts/PromptVersionRepository";
import { HttpDashboardRepository } from "@/repositories/http/HttpDashboardRepository";
import { HttpExperimentRepository } from "@/repositories/http/HttpExperimentRepository";
import { HttpProjectRepository } from "@/repositories/http/HttpProjectRepository";
import { HttpPromptVersionRepository } from "@/repositories/http/HttpPromptVersionRepository";
import { MockDashboardRepository } from "@/repositories/mock/MockDashboardRepository";

interface Repositories {
  dashboard: DashboardRepository;
  projects: ProjectRepository;
  experiments: ExperimentRepository;
  promptVersions: PromptVersionRepository;
}
const RepositoryContext = createContext<Repositories | null>(null);

function createRepositories(): Repositories {
  return {
    dashboard:
      env.dataMode === "demo" ? new MockDashboardRepository() : new HttpDashboardRepository(),
    projects: new HttpProjectRepository(),
    experiments: new HttpExperimentRepository(),
    promptVersions: new HttpPromptVersionRepository(),
  };
}

// Repository classes are stateless. Keeping this object at module scope lets Vite
// replace it together with an updated repository module during Fast Refresh.
// Storing it in React state would retain an instance of the old class and make
// newly added methods (for example cancelOptimization) unavailable until reload.
const repositories = createRepositories();

export function useRepositories() {
  const repositories = useContext(RepositoryContext);
  if (!repositories) throw new Error("useRepositories must be used inside AppProviders");
  return repositories;
}

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <RepositoryContext.Provider value={repositories}>{children}</RepositoryContext.Provider>
    </QueryClientProvider>
  );
}
