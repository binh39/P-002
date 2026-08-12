import { IC } from "./Icons";

export type NavigationId =
  | "dashboard"
  | "projects"
  | "experiments"
  | "datasets"
  | "coverage"
  | "playground"
  | "registry"
  | "settings";

interface SidebarProps {
  currentPage: NavigationId;
  onNavigate: (page: NavigationId) => void;
  user: { name: string; role: string; photoUrl: string | null };
  onSignOut: () => void;
  isOpen?: boolean;
}

const navItems = [
  { id: "dashboard" as NavigationId, label: "Dashboard", Icon: IC.Dashboard },
  { id: "projects" as NavigationId, label: "Projects", Icon: IC.Code },
  { id: "experiments" as NavigationId, label: "Experiments", Icon: IC.Flask },
  { id: "datasets" as NavigationId, label: "Datasets", Icon: IC.Database },
  { id: "coverage" as NavigationId, label: "Coverage Guide", Icon: IC.Code },
  { id: "registry" as NavigationId, label: "Prompt Registry", Icon: IC.CheckSquare },
  { id: "playground" as NavigationId, label: "Playground", Icon: IC.Play },
];

export default function Sidebar({
  currentPage,
  onNavigate,
  user,
  onSignOut,
  isOpen = false,
}: SidebarProps) {
  return (
    <aside
      className={`sidebar ${isOpen ? "sidebar-open" : ""}`}
      style={{
        width: 224,
        minWidth: 224,
        background: "#131626",
        display: "flex",
        flexDirection: "column",
        height: "100vh",
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: "24px 20px 20px",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,

              background: "linear-gradient(135deg, #4F6EF7, #7C3AED)",

              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <IC.Zap />
          </div>
          <div>
            <div
              style={{
                color: "#fff",
                fontSize: 14,
                fontWeight: 600,
                letterSpacing: "-0.01em",
              }}
            >
              PromptOpt
            </div>
            <div style={{ color: "rgba(255,255,255,0.35)", fontSize: 11 }}>AI Platform</div>
          </div>
        </div>
      </div>

      {/* Project selector */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
        }}
      >
        <button
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",

            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.1)",

            borderRadius: 8,
            padding: "8px 12px",
            cursor: "pointer",
            color: "rgba(255,255,255,0.7)",

            fontSize: 12.5,
            fontWeight: 500,
          }}
        >
          <span>PromptOpt Research</span>
          <IC.ChevronDown />
        </button>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: "12px 12px", overflowY: "auto" }}>
        <div
          style={{
            fontSize: 10,
            fontWeight: 600,
            color: "rgba(255,255,255,0.25)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            padding: "4px 8px 8px",
          }}
        >
          Menu
        </div>
        {navItems.map(({ id, label, Icon }) => {
          const active = currentPage === id;

          return (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                gap: 10,

                padding: "9px 12px",
                borderRadius: 8,
                marginBottom: 2,

                background: active
                  ? "linear-gradient(90deg, rgba(79,110,247,0.25), rgba(124,58,237,0.15))"
                  : "transparent",

                border: active ? "1px solid rgba(79,110,247,0.3)" : "1px solid transparent",

                color: active ? "#fff" : "rgba(255,255,255,0.5)",

                cursor: "pointer",
                fontSize: 13.5,
                fontWeight: active ? 500 : 400,

                textAlign: "left",
                transition: "all 0.15s",
              }}
            >
              <span style={{ color: active ? "#6B8FFF" : "rgba(255,255,255,0.35)" }}>
                <Icon />
              </span>
              {label}
            </button>
          );
        })}

        <div
          style={{
            fontSize: 10,
            fontWeight: 600,
            color: "rgba(255,255,255,0.25)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            padding: "12px 8px 8px",
            marginTop: 8,
            borderTop: "1px solid rgba(255,255,255,0.06)",
          }}
        >
          System
        </div>
        <button
          onClick={() => onNavigate("settings")}
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            gap: 10,

            padding: "9px 12px",
            borderRadius: 8,

            background: currentPage === "settings" ? "rgba(79,110,247,0.2)" : "transparent",

            border: "1px solid transparent",

            color: currentPage === "settings" ? "#fff" : "rgba(255,255,255,0.5)",

            cursor: "pointer",
            fontSize: 13.5,
            fontWeight: 400,
            textAlign: "left",
          }}
        >
          <span style={{ color: "rgba(255,255,255,0.35)" }}>
            <IC.Settings />
          </span>
          Settings
        </button>
      </nav>

      {/* User */}
      <div
        style={{
          padding: "16px",
          borderTop: "1px solid rgba(255,255,255,0.07)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,

              background: "linear-gradient(135deg, #4F6EF7, #7C3AED)",

              display: "flex",
              alignItems: "center",
              justifyContent: "center",

              color: "#fff",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {user.photoUrl ? (
              <img
                src={user.photoUrl}
                alt=""
                referrerPolicy="no-referrer"
                style={{ width: "100%", height: "100%", borderRadius: 8 }}
              />
            ) : (
              user.name.slice(0, 1).toUpperCase()
            )}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                color: "rgba(255,255,255,0.85)",
                fontSize: 13,
                fontWeight: 500,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {user.name}
            </div>
            <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 11 }}>{user.role}</div>
          </div>
          <button className="sidebar-signout" onClick={onSignOut} aria-label="Sign out">
            Sign out
          </button>
        </div>
      </div>
    </aside>
  );
}
