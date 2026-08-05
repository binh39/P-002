import { apiRequest } from "@/api/client";
import type { DashboardSnapshot } from "@/domain/dashboard";
import type { DashboardRepository } from "@/repositories/contracts/DashboardRepository";

export class HttpDashboardRepository implements DashboardRepository {
  getSnapshot(signal?: AbortSignal) {
    return apiRequest<DashboardSnapshot>("/dashboard", { signal });
  }
}
