import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import type { UserRole } from "../types";

export function ProtectedRoute({
  children,
  allowedRoles
}: {
  children: JSX.Element;
  allowedRoles: UserRole[];
}) {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (!allowedRoles.includes(user.role)) {
    return <Navigate to={`/${user.role.toLowerCase()}`} replace />;
  }
  return children;
}
