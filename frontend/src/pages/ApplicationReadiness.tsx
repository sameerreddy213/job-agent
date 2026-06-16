import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Badge, Card, EmptyState, PageHeader, Spinner, Stat } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { ApplicationsApi } from "../lib/api";
import { appStateTone, scoreTone } from "../lib/format";
import type { AtsBreakdown, ReadinessItem } from "../lib/types";

export function ApplicationReadiness() {
  const navigate = useNavigate();
  const toast = useToast();
  const [breakdown, setBreakdown] = useState<AtsBreakdown | null>(null);
  const [items, setItems] = useState<ReadinessItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [b, list] = await Promise.all([
          ApplicationsApi.atsBreakdown(),
          ApplicationsApi.readiness(false),
        ]);
        setBreakdown(b);
        setItems(list);
      } catch {
        toast.error("Failed to load readiness");
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <Spinner />;

  const open = (id: string) => navigate(`/applications/${id}`);
  const readyQueue = items.filter((i) => i.ready);

  const Flag = ({ on, label }: { on: boolean; label: string }) =>
    on ? <Badge tone="red">{label}</Badge> : null;

  return (
    <div>
      <PageHeader title="Application Readiness" subtitle="ATS targets and material completeness — no auto-submit" />

      {breakdown && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <Stat label="Total" value={breakdown.total} />
            <Stat label="ATS detected" value={breakdown.detected} tone="indigo" />
            <Stat label="ATS unknown" value={breakdown.unknown} tone="amber" />
            <Stat label="Ready to apply" value={breakdown.ready_to_apply} tone="green" />
            <Stat label="Manual review" value={breakdown.manual_review_required} tone="red" />
          </div>

          <Card className="mb-5">
            <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">ATS breakdown</h2>
            {breakdown.by_ats.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">No applications yet.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {breakdown.by_ats.map((a) => (
                  <Badge key={a.ats_type} tone={a.ats_type === "UNKNOWN" ? "amber" : "indigo"}>
                    {a.ats_type}: {a.count}
                  </Badge>
                ))}
              </div>
            )}
          </Card>
        </>
      )}

      <h2 className="mb-3 text-lg font-semibold">Ready queue ({readyQueue.length})</h2>
      {readyQueue.length === 0 ? (
        <EmptyState title="Nothing ready yet" hint="Applications appear here once materials are complete and no manual fields are required." />
      ) : (
        <div className="mb-6 grid gap-3">
          {readyQueue.map((i) => (
            <Card key={i.id}>
              <div className="flex cursor-pointer items-start justify-between gap-3" onClick={() => open(i.id)}>
                <div className="min-w-0">
                  <p className="truncate font-medium">{i.title ?? "—"}</p>
                  <p className="truncate text-sm text-slate-500 dark:text-slate-400">{i.company ?? "—"}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <Badge tone="indigo">{i.ats_type}</Badge>
                  {i.ready_confirmed ? <Badge tone="green">confirmed</Badge> : <Badge tone="amber">unconfirmed</Badge>}
                  <Badge tone={i.packet_generated_at ? "green" : "slate"}>
                    {i.packet_generated_at ? "packet ready" : "no packet"}
                  </Badge>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <h2 className="mb-3 text-lg font-semibold">All applications</h2>
      {items.length === 0 ? (
        <EmptyState title="No applications" hint="Approve a job to create its application." />
      ) : (
        <div className="grid gap-3">
          {items.map((i) => (
            <Card key={i.id}>
              <div className="flex cursor-pointer items-start justify-between gap-3" onClick={() => open(i.id)}>
                <div className="min-w-0">
                  <p className="truncate font-medium">{i.title ?? "—"}</p>
                  <p className="truncate text-sm text-slate-500 dark:text-slate-400">
                    {i.company ?? "—"} · {i.ats_type}
                    {i.ats_version ? ` (${i.ats_version})` : ""}
                  </p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    <Flag on={i.manual_review_required} label="manual review" />
                    {i.supports_easy_apply && <Badge tone="green">easy apply</Badge>}
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <Badge tone={scoreTone(i.ready_score)}>{i.ready_score}/100</Badge>
                  {i.ready && <Badge tone="green">ready</Badge>}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
