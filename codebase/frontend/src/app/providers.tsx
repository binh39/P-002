/* eslint-disable react-refresh/only-export-components */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, type PropsWithChildren, useContext, useState } from "react";

import { env } from "@/config/env";
import type { DashboardRepository } from "@/repositories/contracts/DashboardRepository";
import type { ProjectRepository } from "@/repositories/contracts/ProjectRepository";
import { HttpDashboardRepository } from "@/repositories/http/HttpDashboardRepository";
import { HttpProjectRepository } from "@/repositories/http/HttpProjectRepository";
import { MockDashboardRepository } from "@/repositories/mock/MockDashboardRepository";
import { MockProjectRepository } from "@/repositories/mock/MockProjectRepository";

interface Repositories {
  dashboard: DashboardRepository;
  projects: ProjectRepository;
}
const RepositoryContext = createContext<Repositories | null>(null);

function createRepositories(): Repositories {
  return {
    dashboard:
      env.dataMode === "demo" ? new MockDashboardRepository() : new HttpDashboardRepository(),
    projects: env.dataMode === "demo" ? new MockProjectRepository() : new HttpProjectRepository(),
  };
}

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
  const [repositories] = useState(createRepositories);

  return (
    <QueryClientProvider client={queryClient}>
      <RepositoryContext.Provider value={repositories}>{children}</RepositoryContext.Provider>
    </QueryClientProvider>
  );
}
