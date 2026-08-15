import { apiRequest } from "@/api/client";
import type { DashboardSnapshot } from "@/domain/dashboard";
import type { DashboardRepository } from "@/repositories/contracts/DashboardRepository";

export class HttpDashboardRepository implements DashboardRepository {
  async getSnapshot(signal?: AbortSignal): Promise<DashboardSnapshot> {
    const item = await apiRequest<ApiDashboardSnapshot>("/dashboard", { signal });
    return {
      projectName: item.project_name,
      asOf: item.as_of,
      coverage: item.coverage,
      kpis: item.kpis,
      quickStats: item.quick_stats,
      experiments: item.experiments.map((experiment) => ({
        id: experiment.id,
        name: experiment.name,
        model: experiment.model,
        branchCoverage: experiment.branch_coverage,
        statementCoverage: experiment.statement_coverage,
        status: experiment.status,
        updatedAt: experiment.updated_at,
      })),
    };
  }
}

interface ApiDashboardSnapshot {
  project_name: string;
  as_of: string;
  coverage: DashboardSnapshot["coverage"];
  kpis: DashboardSnapshot["kpis"];
  quick_stats: DashboardSnapshot["quickStats"];
  experiments: Array<{
    id: string;
    name: string;
    model: string;
    branch_coverage: number;
    statement_coverage: number;
    status: DashboardSnapshot["experiments"][number]["status"];
    updated_at: string;
  }>;
}
