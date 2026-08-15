import { type ReactNode, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";

import { useAuth } from "@/auth/AuthProvider";
import { currentNavigationId, pathByNavigationId } from "@/app/navigation";
import AppFooter from "@/components/AppFooter";
import Sidebar, { type NavigationId } from "@/components/Sidebar";
import TopNav from "@/components/TopNav";

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
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <div className="ambient-orb ambient-orb-one" aria-hidden="true" />
      <div className="ambient-orb ambient-orb-two" aria-hidden="true" />
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
        <main className="main-scroll" id="main-content" key={location}>
          <div className="page-stage">{children}</div>
          <AppFooter />
        </main>
      </div>
    </div>
  );
}
