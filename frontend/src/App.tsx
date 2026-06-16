import { type ComponentType, lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Spinner } from "./components/ui";
import { Login } from "./pages/Login"; // eager: unauthenticated entry point

// Lazy-load authenticated pages so per-page code (and recharts) split out of the
// main bundle and load on demand.
const named = <T extends Record<string, unknown>, K extends keyof T>(p: Promise<T>, k: K) =>
  p.then((m) => ({ default: m[k] as ComponentType }));

const Dashboard = lazy(() => named(import("./pages/Dashboard"), "Dashboard"));
const Queue = lazy(() => named(import("./pages/Queue"), "Queue"));
const Applications = lazy(() => named(import("./pages/Applications"), "Applications"));
const ApplicationReadiness = lazy(() => named(import("./pages/ApplicationReadiness"), "ApplicationReadiness"));
const ApplicationDetail = lazy(() => named(import("./pages/ApplicationDetail"), "ApplicationDetail"));
const JobDetail = lazy(() => named(import("./pages/JobDetail"), "JobDetail"));
const Analytics = lazy(() => named(import("./pages/Analytics"), "Analytics"));
const Sources = lazy(() => named(import("./pages/Sources"), "Sources"));
const Settings = lazy(() => named(import("./pages/Settings"), "Settings"));
const ResumeManagement = lazy(() => named(import("./pages/ResumeManagement"), "ResumeManagement"));
const AuditLogs = lazy(() => named(import("./pages/AuditLogs"), "AuditLogs"));

function Shell({ children }: { children: JSX.Element }) {
  return (
    <ProtectedRoute>
      <Layout>{children}</Layout>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Spinner />
        </div>
      }
    >
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Shell><Dashboard /></Shell>} />
        <Route path="/queue" element={<Shell><Queue /></Shell>} />
        <Route path="/applications" element={<Shell><Applications /></Shell>} />
        <Route path="/readiness" element={<Shell><ApplicationReadiness /></Shell>} />
        <Route path="/applications/:id" element={<Shell><ApplicationDetail /></Shell>} />
        <Route path="/jobs/:id" element={<Shell><JobDetail /></Shell>} />
        <Route path="/analytics" element={<Shell><Analytics /></Shell>} />
        <Route path="/sources" element={<Shell><Sources /></Shell>} />
        <Route path="/settings" element={<Shell><Settings /></Shell>} />
        <Route path="/resumes" element={<Shell><ResumeManagement /></Shell>} />
        <Route path="/audit" element={<Shell><AuditLogs /></Shell>} />
        <Route path="*" element={<Shell><Dashboard /></Shell>} />
      </Routes>
    </Suspense>
  );
}
