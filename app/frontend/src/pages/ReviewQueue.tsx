import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useLocation } from "wouter";

import { useRepositories } from "@/app/providers";
import { PageHeader, StatusBadge } from "@/components/PlatformUI";
import type { PromptVersionStatus } from "@/domain/experiments";

export default function ReviewQueue() {
  const [, navigate] = useLocation();
  const { promptVersions } = useRepositories();
  const [status, setStatus] = useState<PromptVersionStatus>("in_review");
  const query = useQuery({
    queryKey: ["reviews", status],
    queryFn: ({ signal }) => promptVersions.list(status, signal),
  });

  if (query.isPending)
    return (
      <div className="page-state" role="status">
        Loading review queue...
      </div>
    );
  if (query.isError) {
    return (
      <div className="page-state page-state-error" role="alert">
        {query.error.message}
      </div>
    );
  }
  return (
    <div className="platform-page registry-page">
      <PageHeader
        eyebrow="Independent prompt governance"
        title="Review Queue"
        description="Review locked-holdout evidence before a prompt enters the approved registry."
      />
      <section className="platform-card registry-filters">
        <label className="registry-model-filter">
          <span>Status</span>
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value as PromptVersionStatus)}
          >
            <option value="in_review">Awaiting review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </label>
        <span className="registry-result-count">{query.data.total} results</span>
      </section>
      <section className="platform-card table-card">
        {query.data.items.length === 0 ? (
          <div className="empty-state">No prompt candidates match this status.</div>
        ) : (
          <div className="table-scroll">
            <table className="platform-table registry-table">
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Experiment</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((item) => (
                  <tr
                    key={item.id}
                    className="registry-row"
                    onClick={() => navigate(`/reviews/${item.id}`)}
                  >
                    <td>
                      <strong>{item.id}</strong>
                      <small>{item.promptDigest.slice(0, 12)}</small>
                    </td>
                    <td>{item.experimentId}</td>
                    <td>
                      <StatusBadge tone={item.status === "rejected" ? "danger" : "info"}>
                        {item.status.replace("_", " ")}
                      </StatusBadge>
                    </td>
                    <td>{new Date(item.createdAt).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
