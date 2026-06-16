import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { Spinner } from "./ui";

export function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}
