import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button, Card, Field, Input } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

export function Login() {
  const { user, login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err: any) {
      const status = err?.response?.status;
      toast.error(status === 429 ? "Too many attempts. Try again later." : "Invalid credentials");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4 dark:bg-slate-950">
      <Card className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-bold">job-agent</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Sign in to your dashboard</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <Field label="Username">
            <Input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus autoComplete="username" />
          </Field>
          <Field label="Password">
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </Field>
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
