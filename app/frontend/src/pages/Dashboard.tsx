import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useRepositories } from "@/app/providers";
import { IC } from "@/components/Icons";
import type { ExperimentStatus, Kpi } from "@/domain/dashboard";

type Page =
  | "dashboard"
  | "experiments"
  | "playground"
  | "optimization"
  | "comparison"
  | "review"
  | "registry"
  | "settings";
interface Props {
  onNavigate: (page: Page) => void;
}

const card = {
  background: "#fff",
  borderRadius: 14,
  border: "1px solid #E8EBF5",
  boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
} as const;

const kpiPresentation: Record<
  Kpi["icon"],
  {
    icon: typeof IC.Flask;
    color: string;
    bg: string;
  }
> = {
  experiments: { icon: IC.Flask, color: "#4F6EF7", bg: "#EEF2FF" },
  running: { icon: IC.Play, color: "#F59E0B", bg: "#FFFBEB" },
  branch: { icon: IC.BarChart, color: "#10B981", bg: "#F0FDF4" },
  statement: { icon: IC.Code, color: "#8B5CF6", bg: "#F5F3FF" },
};

function StatusBadge({ status }: { status: ExperimentStatus }) {
  const styles = {
    completed: { bg: "#F0FDF4", color: "#059669", dot: "#10B981" },
    running: { bg: "#EFF6FF", color: "#2563EB", dot: "#3B82F6" },
    pending: { bg: "#FFFBEB", color: "#D97706", dot: "#F59E0B" },
    failed: { bg: "#FEF2F2", color: "#DC2626", dot: "#EF4444" },
  };
  const style = styles[status];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        background: style.bg,
        color: style.color,
        padding: "3px 10px",
        borderRadius: 20,
        fontSize: 12,
        fontWeight: 500,
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: style.dot,
        }}
      />
      {status}
    </span>
  );
}

function CoverageBar({ value }: { value: number }) {
  const color = value >= 80 ? "#10B981" : value >= 65 ? "#F59E0B" : "#EF4444";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div
        style={{
          flex: 1,
          height: 4,
          background: "#F0F1F5",
          borderRadius: 2,
          maxWidth: 60,
        }}
      >
        <div
          style={{
            width: `${value}%`,
            height: "100%",
            background: color,
            borderRadius: 2,
          }}
        />
      </div>
      <span style={{ fontSize: 13, fontWeight: 500, color: "#374151" }}>{value.toFixed(1)}%</span>
    </div>
  );
}

export default function Dashboard({ onNavigate }: Props) {
  const { dashboard } = useRepositories();
  const snapshot = useQuery({
    queryKey: ["dashboard"],
    queryFn: ({ signal }) => dashboard.getSnapshot(signal),
  });

  if (snapshot.isPending)
    return (
      <div className="page-state" role="status">
        Loading dashboard…
      </div>
    );
  if (snapshot.isError)
    return (
      <div className="page-state page-state-error" role="alert">
        <h2>Dashboard is unavailable</h2>
        <p>
          {snapshot.error instanceof Error
            ? snapshot.error.message
            : "An unexpected error occurred."}
        </p>
        <button onClick={() => snapshot.refetch()}>Try again</button>
      </div>
    );

  const data = snapshot.data;
  return (
    <div style={{ padding: "28px 32px", maxWidth: 1280 }}>
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: 28,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: "#0F1117",
              margin: 0,
            }}
          >
            Dashboard
          </h1>
          <p style={{ color: "#9CA3AF", fontSize: 13.5, margin: "4px 0 0" }}>
            {data.asOf} — {data.projectName} project
          </p>
        </div>
        <button className="primary-button" onClick={() => onNavigate("experiments")}>
          <IC.Plus /> New Experiment
        </button>
      </div>

      <div className="dashboard-kpis">
        {data.kpis.map(({ label, value, delta, trend, icon }) => {
          const presentation = kpiPresentation[icon];
          const Icon = presentation.icon;
          return (
            <div key={label} style={{ ...card, padding: "20px 22px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  marginBottom: 14,
                }}
              >
                <span style={{ fontSize: 13, color: "#6B7280", fontWeight: 500 }}>{label}</span>
                <div
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 9,
                    background: presentation.bg,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: presentation.color,
                  }}
                >
                  <Icon />
                </div>
              </div>
              <div style={{ fontSize: 28, fontWeight: 700, color: "#0F1117" }}>{value}</div>
              <div
                style={{
                  marginTop: 8,
                  fontSize: 12,
                  color: trend === "up" ? "#10B981" : trend === "down" ? "#EF4444" : "#9CA3AF",
                  fontWeight: 500,
                }}
              >
                {trend === "up" ? "↑ " : trend === "down" ? "↓ " : ""}
                {delta}
              </div>
            </div>
          );
        })}
      </div>

      <div className="dashboard-main-grid">
        <section style={{ ...card, padding: "22px 24px" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: 20,
            }}
          >
            <div>
              <h2 className="card-title">Coverage Trend</h2>
              <p className="card-subtitle">Last 8 days</p>
            </div>
            <div className="chart-legend">
              <span>
                <i style={{ background: "#4F6EF7" }} />
                Branch
              </span>
              <span>
                <i style={{ background: "#8B5CF6" }} />
                Statement
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={data.coverage} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="gradBlue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4F6EF7" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#4F6EF7" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradPurple" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#F0F1F5" vertical={false} />
              <XAxis
                dataKey="day"
                tick={{ fontSize: 11, fill: "#9CA3AF" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#9CA3AF" }}
                axisLine={false}
                tickLine={false}
                domain={[50, 100]}
              />
              <Tooltip
                contentStyle={{
                  border: "1px solid #E8EBF5",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(value) => [`${value}%`]}
              />
              <Area
                type="monotone"
                dataKey="branch"
                stroke="#4F6EF7"
                strokeWidth={2}
                fill="url(#gradBlue)"
              />
              <Area
                type="monotone"
                dataKey="statement"
                stroke="#8B5CF6"
                strokeWidth={2}
                fill="url(#gradPurple)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </section>

        <section style={{ ...card, padding: "22px 24px" }}>
          <h2 className="card-title" style={{ marginBottom: 18 }}>
            Quick Stats
          </h2>
          {data.quickStats.map(({ label, value }) => (
            <div key={label} className="quick-stat">
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </section>
      </div>

      <section style={{ ...card, overflow: "hidden" }}>
        <div className="table-heading">
          <h2 className="card-title">Recent Experiments</h2>
          <button onClick={() => onNavigate("registry")}>
            View all <IC.ArrowRight />
          </button>
        </div>
        {data.experiments.length === 0 ? (
          <div className="empty-state">
            No experiments yet. Create your first experiment to start optimizing.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                {["ID", "Name", "Model", "Branch Cov.", "Stmt Cov.", "Status", "Updated"].map(
                  (heading) => (
                    <th key={heading}>{heading}</th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {data.experiments.map((experiment) => (
                <tr key={experiment.id}>
                  <td className="mono-cell">{experiment.id}</td>
                  <td className="name-cell">{experiment.name}</td>
                  <td>
                    <span className="model-chip">{experiment.model}</span>
                  </td>
                  <td>
                    <CoverageBar value={experiment.branchCoverage} />
                  </td>
                  <td>
                    <CoverageBar value={experiment.statementCoverage} />
                  </td>
                  <td>
                    <StatusBadge status={experiment.status} />
                  </td>
                  <td className="muted-cell">{experiment.updatedAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
