import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import { IC } from "../components/Icons";

const card = {
  background: "#fff",
  borderRadius: 14,
  border: "1px solid #E8EBF5",
  boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
} as const;

const progressData = [
  { gen: "Gen 1", branch: 62.1, statement: 70.3, cost: 0.052 },

  { gen: "Gen 2", branch: 68.5, statement: 75.8, cost: 0.047 },

  { gen: "Gen 3", branch: 74.2, statement: 81.1, cost: 0.045 },

  { gen: "Gen 4", branch: 79.8, statement: 85.6, cost: 0.044 },

  { gen: "Gen 5", branch: 87.3, statement: 93.1, cost: 0.043 },
];

const generations = [
  {
    id: 1,
    label: "Generation 1",
    status: "completed",

    candidates: [
      {
        id: "A",
        branch: 62.1,
        statement: 70.3,
        tokens: 1842,
        cost: 0.052,
        latency: 2.1,
        best: false,
      },

      {
        id: "B",
        branch: 58.4,
        statement: 67.9,
        tokens: 1920,
        cost: 0.055,
        latency: 2.3,
        best: false,
      },

      {
        id: "C",
        branch: 65.3,
        statement: 72.1,
        tokens: 1780,
        cost: 0.051,
        latency: 1.9,
        best: false,
      },
    ],

    bestId: "C",
  },

  {
    id: 2,
    label: "Generation 2",
    status: "completed",

    candidates: [
      {
        id: "A",
        branch: 68.5,
        statement: 75.8,
        tokens: 2041,
        cost: 0.047,
        latency: 1.8,
        best: false,
      },

      {
        id: "B",
        branch: 71.2,
        statement: 77.4,
        tokens: 2180,
        cost: 0.048,
        latency: 2.0,
        best: true,
      },

      {
        id: "C",
        branch: 66.9,
        statement: 74.2,
        tokens: 1950,
        cost: 0.046,
        latency: 1.7,
        best: false,
      },
    ],

    bestId: "B",
  },

  {
    id: 3,
    label: "Generation 3",
    status: "completed",

    candidates: [
      {
        id: "A",
        branch: 74.2,
        statement: 81.1,
        tokens: 2340,
        cost: 0.045,
        latency: 1.9,
        best: false,
      },

      {
        id: "B",
        branch: 76.8,
        statement: 83.2,
        tokens: 2410,
        cost: 0.046,
        latency: 2.0,
        best: true,
      },

      {
        id: "C",
        branch: 73.5,
        statement: 80.7,
        tokens: 2290,
        cost: 0.044,
        latency: 1.8,
        best: false,
      },
    ],

    bestId: "B",
  },

  {
    id: 4,
    label: "Generation 4",
    status: "completed",

    candidates: [
      {
        id: "A",
        branch: 79.8,
        statement: 85.6,
        tokens: 2680,
        cost: 0.044,
        latency: 1.9,
        best: true,
      },

      {
        id: "B",
        branch: 78.1,
        statement: 84.3,
        tokens: 2590,
        cost: 0.043,
        latency: 1.8,
        best: false,
      },

      {
        id: "C",
        branch: 81.4,
        statement: 87.2,
        tokens: 2720,
        cost: 0.045,
        latency: 2.0,
        best: false,
      },
    ],

    bestId: "C",
  },

  {
    id: 5,
    label: "Generation 5",
    status: "completed",

    candidates: [
      {
        id: "A",
        branch: 87.3,
        statement: 93.1,
        tokens: 2847,
        cost: 0.043,
        latency: 1.84,
        best: true,
      },

      {
        id: "B",
        branch: 84.9,
        statement: 91.2,
        tokens: 2710,
        cost: 0.041,
        latency: 1.72,
        best: false,
      },

      {
        id: "C",
        branch: 85.7,
        statement: 92.0,
        tokens: 2780,
        cost: 0.042,
        latency: 1.78,
        best: false,
      },
    ],

    bestId: "A",
  },
];

export default function OptimizationProgress() {
  return (
    <div style={{ padding: "28px 32px", maxWidth: 1200 }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 24,
        }}
      >
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 4,
            }}
          >
            <h1
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: "#0F1117",
                margin: 0,
                letterSpacing: "-0.02em",
              }}
            >
              Optimization Progress
            </h1>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                background: "#F0FDF4",
                color: "#059669",
                padding: "3px 10px",
                borderRadius: 20,
                fontSize: 12,
                fontWeight: 600,
                border: "1px solid #BBF7D0",
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "#10B981",
                  display: "inline-block",
                }}
              />
              Completed
            </span>
          </div>
          <p style={{ color: "#9CA3AF", fontSize: 13, margin: 0 }}>
            EXP-047 · GPT-4o Unit Test Generator v3 · 5 generations · 15 candidates
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 16px",

              background: "#fff",
              border: "1px solid #E8EBF5",
              borderRadius: 8,

              fontSize: 13,
              fontWeight: 500,
              color: "#6B7280",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            <IC.ExternalLink /> Export Report
          </button>
          <button
            style={{
              display: "flex",
              alignItems: "center",
              gap: 7,
              padding: "8px 18px",

              background: "linear-gradient(135deg, #4F6EF7, #7C3AED)",
              color: "#fff",

              border: "none",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,

              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            <IC.CheckSquare /> Review Best
          </button>
        </div>
      </div>

      {/* Summary KPIs */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 14,
          marginBottom: 20,
        }}
      >
        {[
          {
            label: "Best Branch Coverage",
            value: "87.3%",
            gain: "+25.2% from baseline",
            color: "#4F6EF7",
          },

          {
            label: "Best Stmt Coverage",
            value: "93.1%",
            gain: "+22.8% from baseline",
            color: "#8B5CF6",
          },

          {
            label: "Avg. Cost / Run",
            value: "$0.043",
            gain: "↓17% vs initial",
            color: "#10B981",
          },

          {
            label: "Total Generations",
            value: "5",
            gain: "15 candidates evaluated",
            color: "#F59E0B",
          },
        ].map(({ label, value, gain, color }) => (
          <div key={label} style={{ ...card, padding: "18px 20px" }}>
            <div style={{ fontSize: 12.5, color: "#9CA3AF", marginBottom: 8 }}>{label}</div>
            <div
              style={{
                fontSize: 26,
                fontWeight: 700,
                color,
                letterSpacing: "-0.03em",
              }}
            >
              {value}
            </div>
            <div style={{ fontSize: 11.5, color: "#9CA3AF", marginTop: 6 }}>{gain}</div>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div style={{ ...card, padding: "22px 24px", marginBottom: 20 }}>
        <h3
          style={{
            margin: "0 0 18px",
            fontSize: 14,
            fontWeight: 600,
            color: "#0F1117",
          }}
        >
          Coverage Progress by Generation
        </h3>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={progressData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F0F1F5" vertical={false} />
            <XAxis
              dataKey="gen"
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
              formatter={(v) => [`${v}%`]}
            />
            <Line
              type="monotone"
              dataKey="branch"
              stroke="#4F6EF7"
              strokeWidth={2.5}
              dot={{ r: 4, fill: "#4F6EF7" }}
            />
            <Line
              type="monotone"
              dataKey="statement"
              stroke="#8B5CF6"
              strokeWidth={2.5}
              dot={{ r: 4, fill: "#8B5CF6" }}
            />
          </LineChart>
        </ResponsiveContainer>
        <div
          style={{
            display: "flex",
            gap: 20,
            justifyContent: "center",
            marginTop: 8,
          }}
        >
          {[
            ["Branch Coverage", "#4F6EF7"],
            ["Statement Coverage", "#8B5CF6"],
          ].map(([label, color]) => (
            <span
              key={label}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 12,
                color: "#6B7280",
              }}
            >
              <span
                style={{
                  width: 12,
                  height: 3,
                  background: color,
                  borderRadius: 2,
                  display: "inline-block",
                }}
              />
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* Generations timeline */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {generations.map((gen) => {
          const best = gen.candidates.find((c) => c.id === gen.bestId)!;

          return (
            <div key={gen.id}>
              {/* Generation header */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  marginBottom: 10,
                }}
              >
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",

                    background: "linear-gradient(135deg, #4F6EF7, #7C3AED)",

                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",

                    color: "#fff",
                    fontSize: 12,
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {gen.id}
                </div>
                <span style={{ fontSize: 14, fontWeight: 600, color: "#0F1117" }}>{gen.label}</span>
                <div style={{ flex: 1, height: 1, background: "#E8EBF5" }} />
                <span style={{ fontSize: 12, color: "#9CA3AF" }}>
                  Best: {best.branch}% branch, {best.statement}% stmt
                </span>
              </div>

              {/* Candidates */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: 12,
                  paddingLeft: 40,
                }}
              >
                {gen.candidates.map((cand) => {
                  const isBest = cand.id === gen.bestId;

                  return (
                    <div
                      key={cand.id}
                      style={{
                        ...card,

                        padding: "16px 18px",

                        border: isBest ? "2px solid #4F6EF7" : "1px solid #E8EBF5",

                        background: isBest ? "#FAFBFF" : "#fff",

                        position: "relative",
                      }}
                    >
                      {isBest && (
                        <div
                          style={{
                            position: "absolute",
                            top: -10,
                            right: 12,

                            background: "linear-gradient(135deg, #4F6EF7, #7C3AED)",

                            color: "#fff",
                            fontSize: 10,
                            fontWeight: 700,
                            padding: "2px 8px",

                            borderRadius: 10,
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                          }}
                        >
                          <IC.Award /> BEST
                        </div>
                      )}
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          marginBottom: 12,
                        }}
                      >
                        <span
                          style={{
                            fontSize: 13,
                            fontWeight: 600,
                            color: "#0F1117",
                          }}
                        >
                          Candidate {cand.id}
                        </span>
                        <span
                          style={{
                            fontSize: 11.5,
                            color: "#9CA3AF",
                            fontFamily: "JetBrains Mono, monospace",
                          }}
                        >
                          {gen.id}-{cand.id}
                        </span>
                      </div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: 8,
                        }}
                      >
                        {[
                          {
                            label: "Branch",
                            value: `${cand.branch}%`,
                            color: "#4F6EF7",
                          },

                          {
                            label: "Statement",
                            value: `${cand.statement}%`,
                            color: "#8B5CF6",
                          },

                          {
                            label: "Cost",
                            value: `$${cand.cost}`,
                            color: "#10B981",
                          },

                          {
                            label: "Latency",
                            value: `${cand.latency}s`,
                            color: "#6B7280",
                          },
                        ].map(({ label, value, color }) => (
                          <div
                            key={label}
                            style={{
                              background: "#F8F9FC",
                              borderRadius: 8,
                              padding: "8px 10px",
                            }}
                          >
                            <div
                              style={{
                                fontSize: 10,
                                color: "#9CA3AF",
                                marginBottom: 3,
                              }}
                            >
                              {label}
                            </div>
                            <div style={{ fontSize: 14, fontWeight: 700, color }}>{value}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
