import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { EvaluationDetailPage } from "./EvaluationDetailPage";
import { InstructorPage } from "./InstructorPage";
import { Layout } from "./Layout";
import { LoginPage } from "./LoginPage";
import { ManagerPage } from "./ManagerPage";
import { ProtectedRoute } from "./ProtectedRoute";
import { SupervisorPage } from "./SupervisorPage";

function RoleHomeRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={`/${user.role.toLowerCase()}`} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Layout />}>
        <Route index element={<RoleHomeRedirect />} />
        <Route
          path="manager"
          element={
            <ProtectedRoute allowedRoles={["MANAGER"]}>
              <ManagerPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="supervisor"
          element={
            <ProtectedRoute allowedRoles={["SUPERVISOR"]}>
              <SupervisorPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="instructor"
          element={
            <ProtectedRoute allowedRoles={["INSTRUCTOR"]}>
              <InstructorPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="evaluations/:evaluationId"
          element={
            <ProtectedRoute allowedRoles={["MANAGER", "SUPERVISOR", "INSTRUCTOR"]}>
              <EvaluationDetailPage />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
