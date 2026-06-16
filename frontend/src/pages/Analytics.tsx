import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

import { Card, EmptyState, PageHeader, Select, Spinner, Stat } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { AnalyticsApi, WorkflowApi } from "../lib/api";
import { fmtDuration } from "../lib/format";
import type { AnalyticsOverview, CountPoint, DayPoint, WorkflowAnalytics } from "../lib/types";

const BAR_FILL = "#6366f1";
const DAY_OPTIONS = [7, 30, 90];

function ChartCard({
  title,
  data,
  xKey,
}: {
  title: string;
  data: Array<DayPoint | CountPoint>;
  xKey: "day" | "label";
}) {
  return (
    <Card>
      <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</h2>
      {data.length === 0 ? (
        <div className="flex h-[260px] items-center justify-center text-center text-sm text-slate-500 dark:text-slate-400">
          No data yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
            <XAxis
              dataKey={xKey}
              tick={{ fontSize: 11 }}
              interval="preserveStartEnd"
              className="fill-slate-500 dark:fill-slate-400"
            />
            <YAxis allowDecimals={false} tick={{ fontSize: 11 }} className="fill-slate-500 dark:fill-slate-400" />
            <Tooltip
              cursor={{ fill: "rgba(99,102,241,0.1)" }}
              contentStyle={{
                fontSize: 12,
                borderRadius: 8,
                border: "1px solid rgb(203 213 225)",
              }}
            />
            <Bar dataKey="count" fill={BAR_FILL} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}

export function Analytics() {
  const toast = useToast();
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [wf, setWf] = useState<WorkflowAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const [overview, workflow] = await Promise.all([
          AnalyticsApi.overview(days),
          WorkflowApi.analytics(days).catch(() => null),
        ]);
        if (!cancelled) {
          setData(overview);
          setWf(workflow);
        }
      } catch {
        if (!cancelled) toast.error("Failed to load analytics");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [days]);

  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle="Job discovery and pipeline trends"
        actions={
          <Select
            className="w-auto"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            aria-label="Time range in days"
          >
            {DAY_OPTIONS.map((d) => (
              <option key={d} value={d}>
                Last {d} days
              </option>
            ))}
          </Select>
        }
      />

      {loading ? (
        <Spinner />
      ) : !data ? (
        <EmptyState title="No data" hint="Analytics could not be loaded." />
      ) : (
        <div>
          {data.note && (
            <p className="mb-4 text-sm italic text-slate-500 dark:text-slate-400">{data.note}</p>
          )}

          {wf && (
            <div className="mb-6">
              <h2 className="mb-3 text-lg font-semibold">Workflow</h2>
              <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Stat label="Approval %" value={`${wf.approval_pct}%`} tone="green" />
                <Stat label="Rejection %" value={`${wf.rejection_pct}%`} tone="red" />
                <Stat label="Snooze %" value={`${wf.snooze_pct}%`} tone="amber" />
                <Stat label="Avg review time" value={fmtDuration(wf.avg_review_seconds)} tone="indigo" />
              </div>
              <ChartCard
                title="Jobs by Workflow State"
                data={wf.jobs_by_state
                  .filter((s) => s.count > 0)
                  .map((s) => ({ label: s.state, count: s.count }))}
                xKey="label"
              />
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartCard title="Jobs Per Day" data={data.jobs_per_day} xKey="day" />
            <ChartCard title="Applications Per Day" data={data.applications_per_day} xKey="day" />
            <ChartCard title="Top Companies" data={data.top_companies} xKey="label" />
            <ChartCard title="Top Locations" data={data.top_locations} xKey="label" />
            <ChartCard title="Top Skills" data={data.top_skills} xKey="label" />
          </div>
        </div>
      )}
    </div>
  );
}
