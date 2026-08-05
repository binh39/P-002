const card = {
  background: "#fff",
  borderRadius: 14,
  border: "1px solid #E8EBF5",
  boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
} as const;

export default function Settings() {
  return (
    <div style={{ padding: "28px 32px", maxWidth: 800 }}>
      <h1
        style={{
          fontSize: 22,
          fontWeight: 700,
          color: "#0F1117",
          margin: "0 0 6px",
          letterSpacing: "-0.02em",
        }}
      >
        Settings
      </h1>
      <p style={{ color: "#9CA3AF", fontSize: 13, margin: "0 0 28px" }}>
        Manage your workspace preferences and API keys
      </p>

      {[
        {
          title: "API Keys",
          items: [
            {
              label: "OpenAI API Key",
              value: "sk-proj-••••••••••••••••••••••xxK3",
              hint: "Used for GPT-4o, GPT-4o-mini",
            },

            {
              label: "Anthropic API Key",
              value: "sk-ant-••••••••••••••••••••••••••xR8",
              hint: "Used for Claude models",
            },
          ],
        },

        {
          title: "Default Model Settings",
          items: [
            {
              label: "Default Model",
              value: "gpt-4o",
              hint: "Model used for new experiments",
            },

            {
              label: "Default Temperature",
              value: "0.7",
              hint: "Sampling temperature (0–2)",
            },

            {
              label: "Default Max Tokens",
              value: "2048",
              hint: "Maximum token output per call",
            },
          ],
        },

        {
          title: "Optimization Defaults",
          items: [
            {
              label: "Default Generations",
              value: "5",
              hint: "Number of optimization generations",
            },

            {
              label: "Candidates per Gen",
              value: "3",
              hint: "Candidates evaluated per generation",
            },

            {
              label: "Coverage Target",
              value: "85%",
              hint: "Minimum branch coverage target",
            },
          ],
        },
      ].map(({ title, items }) => (
        <div key={title} style={{ ...card, padding: "22px 24px", marginBottom: 16 }}>
          <h3
            style={{
              margin: "0 0 16px",
              fontSize: 14,
              fontWeight: 600,
              color: "#0F1117",
            }}
          >
            {title}
          </h3>
          {items.map(({ label, value, hint }) => (
            <div
              key={label}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                paddingBlock: 12,
                borderBottom: "1px solid #F0F1F5",
              }}
            >
              <div>
                <div style={{ fontSize: 13.5, fontWeight: 500, color: "#374151" }}>{label}</div>
                <div style={{ fontSize: 12, color: "#9CA3AF", marginTop: 2 }}>{hint}</div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span
                  style={{
                    fontSize: 13,
                    fontFamily: "JetBrains Mono, monospace",
                    color: "#6B7280",
                    background: "#F0F1F5",
                    padding: "4px 10px",
                    borderRadius: 6,
                  }}
                >
                  {value}
                </span>
                <button
                  style={{
                    background: "none",
                    border: "1px solid #E8EBF5",
                    borderRadius: 6,
                    padding: "5px 10px",
                    cursor: "pointer",
                    color: "#6B7280",
                    fontSize: 12,
                    fontFamily: "inherit",
                  }}
                >
                  Edit
                </button>
              </div>
            </div>
          ))}
        </div>
      ))}

      <div style={{ ...card, padding: "22px 24px" }}>
        <h3
          style={{
            margin: "0 0 16px",
            fontSize: 14,
            fontWeight: 600,
            color: "#0F1117",
          }}
        >
          Danger Zone
        </h3>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "14px 16px",
            background: "#FEF2F2",
            borderRadius: 10,
            border: "1px solid #FECACA",
          }}
        >
          <div>
            <div style={{ fontSize: 13.5, fontWeight: 500, color: "#991B1B" }}>
              Delete all experiment data
            </div>
            <div style={{ fontSize: 12, color: "#EF4444", marginTop: 2 }}>
              This action cannot be undone
            </div>
          </div>
          <button
            style={{
              padding: "7px 14px",
              background: "#EF4444",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
