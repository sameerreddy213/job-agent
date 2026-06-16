import { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { cn } from "../lib/format";

interface NavItem {
  to: string;
  label: string;
  icon: string; // emoji keeps the bundle dependency-free
}

const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: "📊" },
  { to: "/queue", label: "Queue", icon: "🗂️" },
  { to: "/applications", label: "Applications", icon: "📮" },
  { to: "/readiness", label: "Readiness", icon: "✅" },
  { to: "/analytics", label: "Analytics", icon: "📈" },
  { to: "/sources", label: "Sources", icon: "🔌" },
  { to: "/resumes", label: "Resumes", icon: "📄" },
  { to: "/settings", label: "Settings", icon: "⚙️" },
  { to: "/audit", label: "Audit", icon: "📝" },
];

// Mobile bottom-nav shows the most-used destinations.
const MOBILE_NAV = NAV.filter((n) => ["/", "/queue", "/analytics", "/sources", "/settings"].includes(n.to));

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
      isActive
        ? "bg-indigo-600 text-white"
        : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
    );

  return (
    <div className="flex min-h-screen">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 md:flex">
        <div className="mb-6 px-2 text-lg font-bold">job-agent</div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === "/"} className={linkClass}>
              <span aria-hidden>{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-4 space-y-2 border-t border-slate-200 pt-4 dark:border-slate-800">
          <button onClick={toggle} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
            {theme === "dark" ? "🌞 Light mode" : "🌙 Dark mode"}
          </button>
          <div className="px-3 text-xs text-slate-400">Signed in as {user?.username}</div>
          <button onClick={onLogout} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20">
            ⎋ Logout
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900 md:hidden">
          <span className="text-base font-bold">job-agent</span>
          <div className="flex items-center gap-1">
            <button onClick={toggle} className="rounded-lg p-2 text-lg hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Toggle theme">
              {theme === "dark" ? "🌞" : "🌙"}
            </button>
            <button onClick={onLogout} className="rounded-lg p-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20" aria-label="Logout">
              ⎋
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 pb-24 md:p-6 md:pb-6">{children}</main>

        {/* Mobile bottom nav */}
        <nav className="fixed bottom-0 left-0 right-0 z-40 flex items-stretch justify-around border-t border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 md:hidden">
          {MOBILE_NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px]",
                  isActive ? "text-indigo-600 dark:text-indigo-400" : "text-slate-500 dark:text-slate-400",
                )
              }
            >
              <span className="text-lg" aria-hidden>{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
