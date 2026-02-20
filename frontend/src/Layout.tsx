import { Link, Outlet } from "react-router-dom";
import { useAuth } from "./auth";

export function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>Propel Swim Evaluation</h1>
        {user && (
          <div className="topbar-right">
            <span>
              {user.name} ({user.role})
            </span>
            <button onClick={logout}>Logout</button>
          </div>
        )}
      </header>
      <nav className="nav">
        {user?.role === "MANAGER" && <Link to="/manager">Manager</Link>}
        {user?.role === "SUPERVISOR" && <Link to="/supervisor">Supervisor</Link>}
        {user?.role === "INSTRUCTOR" && <Link to="/instructor">Instructor</Link>}
      </nav>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
