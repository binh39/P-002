import { LogOut, Settings } from "lucide-react";

import { Brand } from "@/components/Brand";
import { IC } from "@/components/Icons";

export type NavigationId =
  | "dashboard"
  | "projects"
  | "experiments"
  | "coverage"
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
  { id: "coverage" as NavigationId, label: "Coverage Guide", Icon: IC.Code },
  { id: "registry" as NavigationId, label: "Prompt Registry", Icon: IC.CheckSquare },
];

export default function Sidebar({
  currentPage,
  onNavigate,
  user,
  onSignOut,
  isOpen = false,
}: SidebarProps) {
  const initials = user.name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <aside className={`sidebar ${isOpen ? "sidebar-open" : ""}`} aria-label="Main navigation">
      <div className="sidebar-brand">
        <Brand />
      </div>

      <nav className="sidebar-navigation">
        <p className="sidebar-label">Workspace</p>
        {navItems.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            className={currentPage === id ? "is-active" : ""}
            onClick={() => onNavigate(id)}
            aria-current={currentPage === id ? "page" : undefined}
          >
            <Icon />
            <span>{label}</span>
          </button>
        ))}

        <p className="sidebar-label sidebar-system-label">System</p>
        <button
          type="button"
          className={currentPage === "settings" ? "is-active" : ""}
          onClick={() => onNavigate("settings")}
          aria-current={currentPage === "settings" ? "page" : undefined}
        >
          <Settings size={17} strokeWidth={1.8} />
          <span>Settings</span>
        </button>
      </nav>

      <div className="sidebar-user">
        <span className="sidebar-avatar">
          {user.photoUrl ? (
            <img src={user.photoUrl} alt="" referrerPolicy="no-referrer" />
          ) : (
            initials
          )}
        </span>
        <span className="sidebar-user-copy">
          <strong>{user.name}</strong>
          <small>{user.role}</small>
        </span>
        <button type="button" onClick={onSignOut} aria-label="Sign out" title="Sign out">
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
