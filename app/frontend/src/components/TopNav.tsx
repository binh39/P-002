import { Bell, Command, Menu, Moon, Search, Sun, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useLocation } from "wouter";

import { env } from "@/config/env";
import { useTheme } from "@/theme/ThemeProvider";

const destinations = [
  { label: "Dashboard", detail: "Workspace overview", path: "/dashboard" },
  { label: "Projects", detail: "Source repositories", path: "/projects" },
  { label: "Experiments", detail: "Optimization runs", path: "/experiments" },
  { label: "Prompt registry", detail: "Versioned prompt bundles", path: "/prompts" },
  { label: "Playground", detail: "Try a prompt against a target", path: "/playground" },
];

export default function TopNav({ onMenu }: { onMenu: () => void }) {
  const { theme, toggleTheme } = useTheme();
  const [, navigate] = useLocation();
  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dataStatus = env.dataMode === "demo" ? "hybrid data" : "API connected";
  const results = destinations.filter((item) =>
    `${item.label} ${item.detail}`.toLowerCase().includes(query.trim().toLowerCase()),
  );

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen(true);
        window.setTimeout(() => inputRef.current?.focus(), 0);
      }
      if (event.key === "Escape") {
        setSearchOpen(false);
        setNotificationsOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const openResult = (path: string) => {
    navigate(path);
    setQuery("");
    setSearchOpen(false);
  };

  return (
    <header className="top-nav">
      <button className="mobile-menu-button" onClick={onMenu} aria-label="Open navigation">
        <Menu size={19} />
      </button>

      <div className={`top-search ${searchOpen ? "is-open" : ""}`}>
        <Search size={16} />
        <input
          ref={inputRef}
          value={query}
          onFocus={() => setSearchOpen(true)}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && results[0]) openResult(results[0].path);
          }}
          placeholder="Search workspace"
          aria-label="Search workspace"
        />
        {searchOpen ? (
          <button type="button" onClick={() => setSearchOpen(false)} aria-label="Close search">
            <X size={15} />
          </button>
        ) : (
          <kbd>
            <Command size={11} />K
          </kbd>
        )}
        {searchOpen && (
          <div className="top-search-results">
            <p>{query ? `${results.length} matching destinations` : "Jump to"}</p>
            {results.map((item) => (
              <button key={item.path} type="button" onClick={() => openResult(item.path)}>
                <span>{item.label}</span>
                <small>{item.detail}</small>
              </button>
            ))}
            {results.length === 0 && <div className="top-search-empty">No matching page</div>}
          </div>
        )}
      </div>

      <div className="top-nav-spacer" />
      <span className="connection-status">
        <i /> {dataStatus}
      </span>
      <button
        type="button"
        className="icon-button theme-toggle"
        aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        title={theme === "dark" ? "Light mode" : "Dark mode"}
        onClick={toggleTheme}
      >
        {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
      </button>
      <div className="notification-wrap">
        <button
          type="button"
          className="icon-button"
          aria-label="Notifications"
          aria-expanded={notificationsOpen}
          onClick={() => setNotificationsOpen((open) => !open)}
        >
          <Bell size={17} />
          <i />
        </button>
        {notificationsOpen && (
          <div className="notification-panel" role="status">
            <strong>Workspace ready</strong>
            <p>Run status and review decisions will appear here.</p>
          </div>
        )}
      </div>
    </header>
  );
}
