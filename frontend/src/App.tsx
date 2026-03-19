import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth";
import { Layout } from "./Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { LoginPage } from "./pages/LoginPage";
import { ManagerPage } from "./pages/ManagerPage";
import { SupervisorPage } from "./pages/SupervisorPage";
import { SupervisorEvaluationsPage } from "./pages/SupervisorEvaluationsPage";
import { InstructorPage } from "./pages/InstructorPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<Layout />}>
            <Route
              path="/manager"
              element={
                <ProtectedRoute allowedRoles={["MANAGER"]}>
                  <ManagerPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/supervisor"
              element={
                <ProtectedRoute allowedRoles={["SUPERVISOR"]}>
                  <Navigate to="/supervisor/evaluations" replace />
                </ProtectedRoute>
              }
            />
            <Route
              path="/supervisor/manage"
              element={
                <ProtectedRoute allowedRoles={["SUPERVISOR"]}>
                  <SupervisorPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/supervisor/evaluations"
              element={
                <ProtectedRoute allowedRoles={["SUPERVISOR"]}>
                  <SupervisorEvaluationsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/instructor"
              element={
                <ProtectedRoute allowedRoles={["INSTRUCTOR"]}>
                  <InstructorPage />
                </ProtectedRoute>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
