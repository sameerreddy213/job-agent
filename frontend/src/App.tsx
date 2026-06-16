import { Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Analytics } from "./pages/Analytics";
import { ApplicationDetail } from "./pages/ApplicationDetail";
import { Applications } from "./pages/Applications";
import { AuditLogs } from "./pages/AuditLogs";
import { Dashboard } from "./pages/Dashboard";
import { JobDetail } from "./pages/JobDetail";
import { Login } from "./pages/Login";
import { Queue } from "./pages/Queue";
import { ResumeManagement } from "./pages/ResumeManagement";
import { Settings } from "./pages/Settings";
import { Sources } from "./pages/Sources";

function Shell({ children }: { children: JSX.Element }) {
  return (
    <ProtectedRoute>
      <Layout>{children}</Layout>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Shell><Dashboard /></Shell>} />
      <Route path="/queue" element={<Shell><Queue /></Shell>} />
      <Route path="/applications" element={<Shell><Applications /></Shell>} />
      <Route path="/applications/:id" element={<Shell><ApplicationDetail /></Shell>} />
      <Route path="/jobs/:id" element={<Shell><JobDetail /></Shell>} />
      <Route path="/analytics" element={<Shell><Analytics /></Shell>} />
      <Route path="/sources" element={<Shell><Sources /></Shell>} />
      <Route path="/settings" element={<Shell><Settings /></Shell>} />
      <Route path="/resumes" element={<Shell><ResumeManagement /></Shell>} />
      <Route path="/audit" element={<Shell><AuditLogs /></Shell>} />
      <Route path="*" element={<Shell><Dashboard /></Shell>} />
    </Routes>
  );
}
