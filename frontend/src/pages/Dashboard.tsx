import { useEffect, useState } from "react";

import { SyncStatusCard } from "../components/SyncStatusCard";
import { WorkflowMetricsCard } from "../components/WorkflowMetricsCard";
import { Badge, Button, Card, EmptyState, PageHeader, Spinner, Stat } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { AdminApi, DashboardApi } from "../lib/api";
import { fmtDate, healthTone } from "../lib/format";
import type { DashboardSummary } from "../lib/types";

export function Dashboard() {
  const toast = useToast();
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setData(await DashboardApi.summary());
    } catch {
      toast.error("Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const runNow = async () => {
    setRunning(true);
    try {
      await AdminApi.runNow();
      toast.success("Pipeline run complete");
      await load();
    } catch {
      toast.error("Run failed");
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <Spinner />;
  if (!data) return <EmptyState title="No data" />;

  const healthy = data.sources.filter((s) => s.status === "HEALTHY").length;

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle={`Last run: ${fmtDate(data.last_run)}`}
        actions={
          <Button onClick={runNow} disabled={running}>
            {running ? "Running…" : "Run now"}
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Total Jobs" value={data.total_jobs} />
        <Stat label="New Jobs" value={data.new_today} tone="indigo" />
        <Stat label="Review Queue" value={data.review_queue} tone="amber" />
        <Stat label="Auto Approve" value={data.auto_eligible} tone="green" />
        <Stat label="Rejected" value={data.rejected} tone="red" />
        <Stat label="Sources Healthy" value={`${healthy}/${data.sources.length}`} tone={healthy === data.sources.length && data.sources.length > 0 ? "green" : "amber"} />
      </div>

      <div className="mt-6">
        <WorkflowMetricsCard />
      </div>

      <div className="mt-6">
        <SyncStatusCard />
      </div>

      <h2 className="mb-3 mt-6 text-lg font-semibold">Source health</h2>
      {data.sources.length === 0 ? (
        <EmptyState title="No runs yet" hint="Trigger a run to populate source health." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.sources.map((s) => (
            <Card key={s.source}>
              <div className="flex items-center justify-between">
                <span className="font-medium capitalize">{s.source}</span>
                <Badge tone={healthTone(s.status)}>{s.status}</Badge>
              </div>
              <dl className="mt-2 space-y-1 text-sm text-slate-500 dark:text-slate-400">
                <div className="flex justify-between"><dt>Jobs found</dt><dd>{s.jobs_found}</dd></div>
                <div className="flex justify-between"><dt>New</dt><dd>{s.new_jobs}</dd></div>
                <div className="flex justify-between"><dt>Errors</dt><dd>{s.errors}</dd></div>
                <div className="flex justify-between"><dt>Response</dt><dd>{s.response_time_ms} ms</dd></div>
                <div className="flex justify-between"><dt>Last run</dt><dd>{fmtDate(s.run_at)}</dd></div>
              </dl>
              {s.detail && <p className="mt-2 text-xs text-red-500">{s.detail}</p>}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
