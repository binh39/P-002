import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  Braces,
  ChartNoAxesCombined,
  FlaskConical,
  GitBranch,
  Play,
  Plus,
} from "lucide-react";
import { motion } from "motion/react";
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
import type { ExperimentStatus, Kpi } from "@/domain/dashboard";

type Page =
  | "dashboard"
  | "experiments"
  | "optimization"
  | "comparison"
  | "review"
  | "registry"
  | "settings";

interface Props {
  onNavigate: (page: Page) => void;
}

const kpiPresentation: Record<Kpi["icon"], { Icon: typeof FlaskConical; tone: string }> = {
  experiments: { Icon: FlaskConical, tone: "cyan" },
  running: { Icon: Play, tone: "amber" },
  branch: { Icon: GitBranch, tone: "green" },
  statement: { Icon: Braces, tone: "violet" },
};

function StatusBadge({ status }: { status: ExperimentStatus }) {
  return (
    <span className={`dashboard-status dashboard-status-${status}`}>
      <i />
      {status}
    </span>
  );
}

function CoverageBar({ value }: { value: number }) {
  const tone = value >= 80 ? "good" : value >= 65 ? "fair" : "low";
  return (
    <div className="coverage-meter">
      <span>
        <i className={tone} style={{ width: `${value}%` }} />
      </span>
      <strong>{value.toFixed(1)}%</strong>
    </div>
  );
}

export default function Dashboard({ onNavigate }: Props) {
  const { dashboard } = useRepositories();
  const snapshot = useQuery({
    queryKey: ["dashboard"],
    queryFn: ({ signal }) => dashboard.getSnapshot(signal),
  });

  if (snapshot.isPending) {
    return (
      <div className="page-state" role="status">
        Loading dashboard…
      </div>
    );
  }
  if (snapshot.isError) {
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
  }

  const data = snapshot.data;
  return (
    <div className="platform-page dashboard-page">
      <motion.header
        className="dashboard-hero"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <div>
          <span className="eyebrow">Optimization intelligence</span>
          <h1>Make every prompt earn its place.</h1>
          <p>
            {data.asOf} · Monitoring <strong>{data.projectName}</strong> with reproducible coverage
            evidence.
          </p>
        </div>
        <button className="primary-button" onClick={() => onNavigate("experiments")}>
          <Plus size={17} /> New experiment
        </button>
      </motion.header>

      <section className="dashboard-kpis" aria-label="Key metrics">
        {data.kpis.map(({ label, value, delta, trend, icon }, index) => {
          const { Icon, tone } = kpiPresentation[icon];
          return (
            <motion.article
              className={`dashboard-kpi tone-${tone}`}
              key={label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.06 * index, duration: 0.45 }}
            >
              <div className="dashboard-kpi-top">
                <span>{label}</span>
                <i>
                  <Icon size={18} strokeWidth={1.8} />
                </i>
              </div>
              <strong>{value}</strong>
              <small className={`trend-${trend}`}>
                {trend === "up" ? "↑ " : trend === "down" ? "↓ " : ""}
                {delta}
              </small>
            </motion.article>
          );
        })}
      </section>

      <div className="dashboard-main-grid">
        <section className="platform-card dashboard-chart-card">
          <div className="card-heading">
            <div>
              <span className="card-kicker">Coverage signal</span>
              <h2>Coverage trend</h2>
            </div>
            <div className="chart-legend">
              <span>
                <i className="branch" />
                Branch
              </span>
              <span>
                <i className="statement" />
                Statement
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={165}>
            <AreaChart data={data.coverage} margin={{ top: 16, right: 10, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="branchFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#31A8FF" stopOpacity={0.22} />
                  <stop offset="100%" stopColor="#31A8FF" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="statementFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#7C6CF2" stopOpacity={0.18} />
                  <stop offset="100%" stopColor="#7C6CF2" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 5" stroke="var(--po-chart-grid)" vertical={false} />
              <XAxis
                dataKey="day"
                tick={{ fontSize: 11, fill: "var(--po-chart-muted)" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "var(--po-chart-muted)" }}
                axisLine={false}
                tickLine={false}
                domain={[50, 100]}
              />
              <Tooltip
                contentStyle={{
                  border: "1px solid #E2E8F0",
                  borderRadius: 14,
                  fontSize: 12,
                  boxShadow: "0 16px 40px rgba(15,23,42,.1)",
                }}
                formatter={(value) => [`${value}%`]}
              />
              <Area
                type="monotone"
                dataKey="branch"
                stroke="#31A8FF"
                strokeWidth={2.5}
                fill="url(#branchFill)"
              />
              <Area
                type="monotone"
                dataKey="statement"
                stroke="#7C6CF2"
                strokeWidth={2.5}
                fill="url(#statementFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </section>

        <section className="platform-card dashboard-quick-card">
          <div className="quick-card-symbol">
            <ChartNoAxesCombined size={20} />
          </div>
          <span className="card-kicker">Current workspace</span>
          <h2>Quick stats</h2>
          <div className="quick-stat-list">
            {data.quickStats.map(({ label, value }) => (
              <div key={label} className="quick-stat">
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
          <button className="text-button" onClick={() => onNavigate("experiments")}>
            View experiments <ArrowUpRight size={15} />
          </button>
        </section>
      </div>

      <section className="platform-card dashboard-table-card">
        <div className="table-heading">
          <div>
            <span className="card-kicker">Latest activity</span>
            <h2>Recent experiments</h2>
          </div>
          <button onClick={() => onNavigate("experiments")}>
            View all <ArrowRight size={15} />
          </button>
        </div>
        {data.experiments.length === 0 ? (
          <div className="empty-state">No experiments yet. Create one to start optimizing.</div>
        ) : (
          <div className="data-table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  {["ID", "Experiment", "Model", "Branch", "Statement", "Status", "Updated"].map(
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
          </div>
        )}
      </section>
    </div>
  );
}
