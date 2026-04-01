import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProjectProvider } from "@/contexts/ProjectContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Login from "@/pages/auth/Login";
import Signup from "@/pages/auth/Signup";
import Dashboard from "@/pages/Dashboard";
import Systems from "@/pages/Systems";
import Projects from "@/pages/Projects";
import ProjectDetails from "@/pages/ProjectDetails";
import Monitoring from "@/pages/Monitoring";
import ProjectMonitoringDetails from "@/pages/ProjectMonitoringDetails";
import ModelComparison from "@/pages/ModelComparison";
import Docs from "@/pages/Docs";
import "./App.css";

const ErrorPage = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary">
      <div className="text-text-secondary">404 - Page Not Found</div>
    </div>
  );
};

function App() {
  return (
    <Router>
      <AuthProvider>
        <ProjectProvider>
          <Routes>
            {/* Redirect root to login */}
            <Route path="/" element={<Navigate to="/auth/login" replace />} />

            {/* Auth routes */}
            <Route path="/auth/login" element={<Login />} />
            <Route path="/auth/signup" element={<Signup />} />

            {/* Protected routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="systems"
              element={
                <ProtectedRoute>
                  <Systems />
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects"
              element={
                <ProtectedRoute>
                  <Projects />
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects/:projectId"
              element={
                <ProtectedRoute>
                  <ProjectDetails />
                </ProtectedRoute>
              }
            />
            <Route
              path="/monitoring"
              element={
                <ProtectedRoute>
                  <Monitoring />
                </ProtectedRoute>
              }
            />
            <Route
              path="/monitoring/:projectId"
              element={
                <ProtectedRoute>
                  <ProjectMonitoringDetails />
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects/:projectId/compare"
              element={
                <ProtectedRoute>
                  <ModelComparison />
                </ProtectedRoute>
              }
            />
            <Route
              path="/docs"
              element={
                <ProtectedRoute>
                  <Docs />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<ErrorPage />} />
          </Routes>
        </ProjectProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
