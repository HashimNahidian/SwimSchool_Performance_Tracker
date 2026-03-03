import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "./auth";
import { ShieldLogo } from "./components/ShieldLogo";
import type { UserRole } from "./types";

const ROLE_PATH: Record<UserRole, string> = {
  MANAGER: "/manager",
  SUPERVISOR: "/supervisor",
  INSTRUCTOR: "/instructor",
};

function initials(name: string) {
  return name
    .split(" ")
    .map((w) => w[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <ShieldLogo size={34} color="rgba(255,255,255,0.18)" />
          <span className="topbar-title">DataShield 5</span>
        </div>

        <nav className="topbar-nav">
          {user?.role && (
            <NavLink
              to={ROLE_PATH[user.role]}
              className={({ isActive }) => `topnav-link${isActive ? " active" : ""}`}
            >
              Dashboard
            </NavLink>
          )}
        </nav>

        {user && (
          <div className="topbar-right">
            <div className="user-avatar">{initials(user.name)}</div>
            <span className="topbar-user">{user.name}</span>
            <button className="signout-btn" onClick={logout}>
              Sign Out
            </button>
          </div>
        )}
      </header>

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
