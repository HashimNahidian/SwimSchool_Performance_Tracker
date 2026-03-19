import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "./auth";
import { WaveLogo } from "./components/WaveLogo";
import type { UserRole } from "./types";

const ROLE_PATH: Record<UserRole, string> = {
  MANAGER: "/manager",
  SUPERVISOR: "/supervisor/manage",
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
          <WaveLogo size={38} light />
          <div>
            <div className="topbar-title">Propel Swim School</div>
            <div className="topbar-tagline">Instructor Evaluation Portal</div>
          </div>
        </div>

        <nav className="topbar-nav">
          {user?.role === "SUPERVISOR" ? (
            <>
              <NavLink
                to="/supervisor/evaluations"
                className={({ isActive }) => `topnav-link${isActive ? " active" : ""}`}
              >
                View Evaluations
              </NavLink>
              <NavLink
                to="/supervisor/manage"
                className={({ isActive }) => `topnav-link${isActive ? " active" : ""}`}
              >
                Create Eval
              </NavLink>
            </>
          ) : (
            user?.role && (
              <NavLink
                to={ROLE_PATH[user.role]}
                className={({ isActive }) => `topnav-link${isActive ? " active" : ""}`}
              >
                Dashboard
              </NavLink>
            )
          )}
        </nav>

        {user && (
          <div className="topbar-right">
            <div className="user-avatar">{initials(user.full_name)}</div>
            <span className="topbar-user">{user.full_name}</span>
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
