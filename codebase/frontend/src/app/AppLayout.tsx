import { type ReactNode, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";

import { useAuth } from "@/auth/AuthProvider";
import Sidebar, { type NavigationId } from "@/components/Sidebar";
import TopNav from "@/components/TopNav";

const pathByNavigationId: Record<NavigationId, string> = {
  dashboard: "/dashboard",
  projects: "/projects",
  experiments: "/experiments",
  datasets: "/datasets",
  playground: "/playground",
  registry: "/prompts",
  settings: "/settings",
};

function currentNavigationId(pathname: string): NavigationId {
  if (pathname.startsWith("/projects")) return "projects";
  if (pathname.startsWith("/experiments") || pathname.startsWith("/runs")) return "experiments";
  if (pathname.startsWith("/datasets")) return "datasets";
  if (pathname.startsWith("/playground")) return "playground";
  if (pathname.startsWith("/prompts")) return "registry";
  if (pathname.startsWith("/settings")) return "settings";
  return "dashboard";
}

export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth();
  const queryClient = useQueryClient();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [location, navigate] = useLocation();
  const onNavigate = (id: NavigationId) => {
    navigate(pathByNavigationId[id]);
    setSidebarOpen(false);
  };

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <button
          className="mobile-backdrop"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <Sidebar
        currentPage={currentNavigationId(location)}
        onNavigate={onNavigate}
        user={user!}
        onSignOut={() => void signOut().then(() => queryClient.clear())}
        isOpen={sidebarOpen}
      />
      <div className="app-main">
        <TopNav onMenu={() => setSidebarOpen(true)} />
        <main className="main-scroll" id="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
