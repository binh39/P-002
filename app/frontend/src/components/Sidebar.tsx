import { LogOut, Settings } from "lucide-react";

import { Brand } from "@/components/Brand";
import { IC } from "@/components/Icons";
import type { UserRole } from "@/auth/AuthService";
import WorkspaceSwitcher from "@/components/WorkspaceSwitcher";

export type NavigationId =
  | "dashboard"
  | "reviews"
  | "projects"
  | "experiments"
  | "coverage"
  | "registry"
  | "testCases"
  | "workspaceSettings"
  | "settings";

interface SidebarProps {
  currentPage: NavigationId;
  onNavigate: (page: NavigationId) => void;
  user: { name: string; role: UserRole; photoUrl: string | null; workspaceId?: string };
  onSignOut: () => void;
  isOpen?: boolean;
}

const engineerNavItems = [
  { id: "dashboard" as NavigationId, label: "Dashboard", Icon: IC.Dashboard },
  { id: "projects" as NavigationId, label: "Projects", Icon: IC.Code },
  { id: "experiments" as NavigationId, label: "Experiments", Icon: IC.Flask },
  { id: "registry" as NavigationId, label: "Prompt Registry", Icon: IC.CheckSquare },
  { id: "testCases" as NavigationId, label: "Test Suites", Icon: IC.Database },
  { id: "workspaceSettings" as NavigationId, label: "Workspace Settings", Icon: Settings },
];

const reviewerNavItems = [
  { id: "reviews" as NavigationId, label: "Review Queue", Icon: IC.CheckSquare },
  { id: "registry" as NavigationId, label: "Prompt Registry", Icon: IC.CheckSquare },
  { id: "testCases" as NavigationId, label: "Test Suites", Icon: IC.Database },
  { id: "workspaceSettings" as NavigationId, label: "Workspace Settings", Icon: Settings },
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
  const navItems = user.role === "prompt_reviewer" ? reviewerNavItems : engineerNavItems;

  return (
    <aside className={`sidebar ${isOpen ? "sidebar-open" : ""}`} aria-label="Main navigation">
      <div className="sidebar-brand">
        <Brand />
      </div>

      <nav className="sidebar-navigation" aria-label="Workspace navigation">
        <p className="sidebar-label">Workspace</p>
        <WorkspaceSwitcher activeId={user.workspaceId ?? ""} />
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
      </nav>

      <nav className="sidebar-system-navigation" aria-label="System navigation">
        <p className="sidebar-label">System</p>
        <button
          type="button"
          className={currentPage === "coverage" ? "is-active" : ""}
          onClick={() => onNavigate("coverage")}
          aria-current={currentPage === "coverage" ? "page" : undefined}
        >
          <IC.Code />
          <span>Docs</span>
        </button>
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
          <small>{user.role === "prompt_reviewer" ? "Prompt Reviewer" : "Prompt Engineer"}</small>
        </span>
        <button type="button" onClick={onSignOut} aria-label="Sign out" title="Sign out">
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
