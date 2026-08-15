import { useState } from "react";

import { IC } from "../components/Icons";
import { PageHeader } from "../components/PlatformUI";

const card = {
  background: "#fff",
  borderRadius: 14,
  border: "1px solid #E8EBF5",
  boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
} as const;

const prompts = [
  {
    id: "PRG-031",
    name: "GPT-4o Unit Test Generator v3",
    model: "gpt-4o",
    version: "v3.0",
    branch: 87.3,
    statement: 93.1,
    status: "active",
    cost: "$0.043",
    latency: "1.84s",
    createdBy: "Auto-optimizer",
    createdAt: "Aug 4, 2026",
    experiment: "EXP-047",
  },

  {
    id: "PRG-030",
    name: "Database Layer Coverage Run",
    model: "gpt-4o",
    version: "v2.1",
    branch: 91.2,
    statement: 95.6,
    status: "active",
    cost: "$0.038",
    latency: "1.62s",
    createdBy: "Auto-optimizer",
    createdAt: "Aug 2, 2026",
    experiment: "EXP-043",
  },

  {
    id: "PRG-029",
    name: "Claude Haiku Coverage v2",
    model: "claude-haiku-4-5",
    version: "v2.0",
    branch: 84.5,
    statement: 90.2,
    status: "archived",
    cost: "$0.021",
    latency: "1.21s",
    createdBy: "Auto-optimizer",
    createdAt: "Jul 30, 2026",
    experiment: "EXP-041",
  },

  {
    id: "PRG-028",
    name: "Auth Module Test Suite",
    model: "claude-sonnet-4-6",
    version: "v1.2",
    branch: 79.8,
    statement: 87.4,
    status: "active",
    cost: "$0.055",
    latency: "2.10s",
    createdBy: "Auto-optimizer",
    createdAt: "Jul 28, 2026",
    experiment: "EXP-039",
  },

  {
    id: "PRG-027",
    name: "API Gateway Integration v1",
    model: "gpt-4o-mini",
    version: "v1.0",
    branch: 71.3,
    statement: 79.6,
    status: "deprecated",
    cost: "$0.018",
    latency: "0.94s",
    createdBy: "Alex Morgan",
    createdAt: "Jul 25, 2026",
    experiment: "EXP-036",
  },

  {
    id: "PRG-026",
    name: "Stripe Payment Tests v1",
    model: "gpt-4o",
    version: "v1.4",
    branch: 88.1,
    statement: 94.3,
    status: "active",
    cost: "$0.041",
    latency: "1.78s",
    createdBy: "Auto-optimizer",
    createdAt: "Jul 22, 2026",
    experiment: "EXP-034",
  },

  {
    id: "PRG-025",
    name: "User Auth Regression v2",
    model: "claude-sonnet-4-6",
    version: "v2.3",
    branch: 76.4,
    statement: 83.7,
    status: "archived",
    cost: "$0.048",
    latency: "1.95s",
    createdBy: "Sarah Chen",
    createdAt: "Jul 19, 2026",
    experiment: "EXP-031",
  },
];

type Status = "all" | "active" | "archived" | "deprecated";

function StatusBadge({ status }: { status: string }) {
  const s: Record<string, { bg: string; color: string }> = {
    active: { bg: "#F0FDF4", color: "#059669" },

    archived: { bg: "#F0F1F5", color: "#6B7280" },

    deprecated: { bg: "#FEF2F2", color: "#DC2626" },
  };

  const { bg, color } = s[status] || s.archived;

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        background: bg,
        color,
        padding: "3px 10px",
        borderRadius: 20,
        fontSize: 12,
        fontWeight: 500,
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          background: color,
          display: "inline-block",
        }}
      />
      {status}
    </span>
  );
}

function CoverageBar({ value, max = 100 }: { value: number; max?: number }) {
  const pct = (value / max) * 100;

  const color = value >= 80 ? "#10B981" : value >= 65 ? "#F59E0B" : "#EF4444";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ width: 52, height: 4, background: "#F0F1F5", borderRadius: 2 }}>
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            borderRadius: 2,
          }}
        />
      </div>
      <span style={{ fontSize: 13, fontWeight: 500, color: "#374151" }}>{value}%</span>
    </div>
  );
}

export default function Registry() {
  const [search, setSearch] = useState("");

  const [statusFilter, setStatusFilter] = useState<Status>("all");

  const [modelFilter, setModelFilter] = useState("all");

  const filtered = prompts.filter((p) => {
    const matchSearch =
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.id.toLowerCase().includes(search.toLowerCase());

    const matchStatus = statusFilter === "all" || p.status === statusFilter;

    const matchModel = modelFilter === "all" || p.model === modelFilter;

    return matchSearch && matchStatus && matchModel;
  });

  return (
    <div className="platform-page registry-page">
      <PageHeader
        eyebrow="Prompt library"
        title="Prompt Registry"
        description={`${prompts.length} registered prompts · payment-service project`}
        actions={
          <button className="primary-button" type="button">
            <IC.Plus /> Import Prompt
          </button>
        }
      />

      {/* Filters */}
      <div
        className="registry-filters"
        style={{
          ...card,
          padding: "16px 20px",
          marginBottom: 16,
          display: "flex",
          gap: 12,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        {/* Search */}
        <div style={{ position: "relative", flex: 1, minWidth: 220 }}>
          <span
            style={{
              position: "absolute",
              left: 11,
              top: "50%",
              transform: "translateY(-50%)",
              color: "#9CA3AF",
            }}
          >
            <IC.Search />
          </span>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or ID..."
            style={{
              width: "100%",
              paddingLeft: 34,
              paddingRight: 14,
              paddingBlock: 8,

              border: "1px solid #E8EBF5",
              borderRadius: 8,
              fontSize: 13.5,

              background: "#F8F9FC",
              color: "#374151",
              outline: "none",

              fontFamily: "inherit",
              boxSizing: "border-box" as const,
            }}
          />
        </div>

        {/* Status filter */}
        <div style={{ display: "flex", gap: 6 }}>
          {(["all", "active", "archived", "deprecated"] as Status[]).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              style={{
                padding: "6px 14px",
                borderRadius: 8,
                fontSize: 12.5,
                fontWeight: 500,

                background: statusFilter === s ? "#EEF2FF" : "#fff",

                color: statusFilter === s ? "#4F6EF7" : "#6B7280",

                border: statusFilter === s ? "1px solid #C7D2FE" : "1px solid #E8EBF5",

                cursor: "pointer",
                fontFamily: "inherit",
                textTransform: "capitalize" as const,
              }}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Model filter */}
        <select
          value={modelFilter}
          onChange={(e) => setModelFilter(e.target.value)}
          style={{
            padding: "7px 12px",
            border: "1px solid #E8EBF5",
            borderRadius: 8,

            fontSize: 12.5,
            fontFamily: "inherit",
            background: "#fff",
            color: "#374151",

            cursor: "pointer",
          }}
        >
          <option value="all">All Models</option>
          <option value="gpt-4o">GPT-4o</option>
          <option value="gpt-4o-mini">GPT-4o Mini</option>
          <option value="claude-sonnet-4-6">Claude Sonnet 4.6</option>
          <option value="claude-haiku-4-5">Claude Haiku 4.5</option>
        </select>

        <span style={{ fontSize: 12.5, color: "#9CA3AF", marginLeft: "auto" }}>
          {filtered.length} results
        </span>
      </div>

      {/* Table */}
      <div className="registry-table-card" style={card}>
        <table className="registry-table">
          <colgroup>
            <col className="registry-col-id" />
            <col className="registry-col-name" />
            <col className="registry-col-model" />
            <col className="registry-col-version" />
            <col className="registry-col-coverage" />
            <col className="registry-col-coverage" />
            <col className="registry-col-cost" />
            <col className="registry-col-latency" />
            <col className="registry-col-status" />
            <col className="registry-col-created" />
            <col className="registry-col-actions" />
          </colgroup>
          <thead>
            <tr style={{ background: "#FAFBFF" }}>
              {[
                "ID",
                "Name",
                "Model",
                "Version",
                "Branch Cov.",
                "Stmt Cov.",
                "Cost",
                "Latency",
                "Status",
                "Created",
                "",
              ].map((h) => (
                <th
                  key={h}
                  style={{
                    padding: "11px 18px",
                    textAlign: "left",
                    fontSize: 11,
                    fontWeight: 600,
                    color: "#9CA3AF",
                    letterSpacing: "0.05em",
                    textTransform: "uppercase",
                    whiteSpace: "nowrap",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((p, i) => (
              <tr
                key={p.id}
                style={{
                  borderTop: "1px solid #F0F1F5",
                  background: i % 2 === 0 ? "#fff" : "#FAFBFF",
                }}
              >
                <td
                  className="registry-id-cell"
                  style={{
                    padding: "13px 18px",
                    fontSize: 12,
                    color: "#6B7280",
                    fontFamily: "JetBrains Mono, monospace",
                    fontWeight: 500,
                  }}
                >
                  {p.id}
                </td>
                <td className="registry-name-cell" style={{ padding: "13px 18px" }}>
                  <div
                    style={{
                      fontSize: 13.5,
                      fontWeight: 500,
                      color: "#0F1117",
                    }}
                  >
                    {p.name}
                  </div>
                  <div style={{ fontSize: 11.5, color: "#9CA3AF", marginTop: 2 }}>
                    {p.experiment}
                  </div>
                </td>
                <td style={{ padding: "13px 18px" }}>
                  <span
                    className="registry-model-chip"
                    style={{
                      fontSize: 11.5,
                      background: "#F0F1F5",
                      color: "#6B7280",
                      padding: "3px 7px",
                      borderRadius: 5,
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    {p.model}
                  </span>
                </td>
                <td style={{ padding: "13px 18px" }}>
                  <span
                    style={{
                      fontSize: 12,
                      background: "#EEF2FF",
                      color: "#4F6EF7",
                      padding: "3px 8px",
                      borderRadius: 5,
                      fontWeight: 600,
                    }}
                  >
                    {p.version}
                  </span>
                </td>
                <td style={{ padding: "13px 18px" }}>
                  <CoverageBar value={p.branch} />
                </td>
                <td style={{ padding: "13px 18px" }}>
                  <CoverageBar value={p.statement} />
                </td>
                <td
                  style={{
                    padding: "13px 18px",
                    fontSize: 12.5,
                    color: "#374151",
                    fontFamily: "JetBrains Mono, monospace",
                  }}
                >
                  {p.cost}
                </td>
                <td
                  style={{
                    padding: "13px 18px",
                    fontSize: 12.5,
                    color: "#374151",
                    fontFamily: "JetBrains Mono, monospace",
                  }}
                >
                  {p.latency}
                </td>
                <td style={{ padding: "13px 18px" }}>
                  <StatusBadge status={p.status} />
                </td>
                <td
                  style={{
                    padding: "13px 18px",
                    fontSize: 12.5,
                    color: "#9CA3AF",
                    whiteSpace: "nowrap",
                  }}
                >
                  {p.createdAt}
                </td>
                <td style={{ padding: "13px 18px" }}>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      aria-label={`Copy ${p.id}`}
                      onClick={() => void navigator.clipboard.writeText(p.id)}
                      style={{
                        background: "none",
                        border: "1px solid #E8EBF5",
                        borderRadius: 6,
                        padding: "4px 8px",
                        cursor: "pointer",
                        color: "#6B7280",
                        display: "flex",
                        alignItems: "center",
                      }}
                    >
                      <IC.Copy />
                    </button>
                    <button
                      aria-label={`Open ${p.id}`}
                      onClick={() => window.alert(`${p.name} details opened.`)}
                      style={{
                        background: "none",
                        border: "1px solid #E8EBF5",
                        borderRadius: 6,
                        padding: "4px 8px",
                        cursor: "pointer",
                        color: "#6B7280",
                        display: "flex",
                        alignItems: "center",
                      }}
                    >
                      <IC.ExternalLink />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div
            style={{
              padding: "48px 24px",
              textAlign: "center",
              color: "#9CA3AF",
            }}
          >
            <div style={{ marginBottom: 8 }}>
              <IC.Search />
            </div>
            <div style={{ fontSize: 14 }}>No prompts found matching your filters</div>
          </div>
        )}
      </div>
    </div>
  );
}
