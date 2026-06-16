import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { WorkflowApi } from "../lib/api";
import { fmtDuration, workflowTone } from "../lib/format";
import type { WorkflowAnalytics } from "../lib/types";
import { Badge, Card, Spinner, Stat } from "./ui";

/**
 * Workflow health for the Dashboard: approval/rejection rates, average review
 * time, jobs-by-state distribution, and the pending-review trend.
 */
export function WorkflowMetricsCard({ days = 30 }: { days?: number }) {
  const [data, setData] = useState<WorkflowAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    WorkflowApi.analytics(days)
      .then((d) => active && setData(d))
      .catch(() => undefined)
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [days]);

  if (loading) return <Spinner />;
  if (!data) return null;

  const nonZeroStates = data.jobs_by_state.filter((s) => s.count > 0);

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold">Workflow metrics (last {data.days}d)</h2>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Approval rate" value={`${data.approval_pct}%`} tone="green" />
        <Stat label="Rejection rate" value={`${data.rejection_pct}%`} tone="red" />
        <Stat label="Snooze rate" value={`${data.snooze_pct}%`} tone="amber" />
        <Stat label="Avg review time" value={fmtDuration(data.avg_review_seconds)} tone="indigo" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Jobs by workflow state</h3>
          {nonZeroStates.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">No jobs yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {nonZeroStates.map((s) => (
                <Badge key={s.state} tone={workflowTone(s.state)}>
                  {s.state}: {s.count}
                </Badge>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <h3 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Pending review trend</h3>
          {data.pending_review_trend.length === 0 ? (
            <div className="flex h-[180px] items-center justify-center text-sm text-slate-500 dark:text-slate-400">
              No data yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={data.pending_review_trend} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip
                  cursor={{ fill: "rgba(99,102,241,0.1)" }}
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid rgb(203 213 225)" }}
                />
                <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>
    </div>
  );
}
