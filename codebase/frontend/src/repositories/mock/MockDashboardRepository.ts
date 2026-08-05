import { dashboardFixture } from "@/mocks/fixtures/dashboard";
import type { DashboardRepository } from "@/repositories/contracts/DashboardRepository";

export class MockDashboardRepository implements DashboardRepository {
  async getSnapshot(signal?: AbortSignal) {
    await new Promise<void>((resolve, reject) => {
      const timer = window.setTimeout(resolve, 250);
      signal?.addEventListener(
        "abort",
        () => {
          window.clearTimeout(timer);
          reject(new DOMException("Request aborted", "AbortError"));
        },
        { once: true },
      );
    });
    return structuredClone(dashboardFixture);
  }
}
