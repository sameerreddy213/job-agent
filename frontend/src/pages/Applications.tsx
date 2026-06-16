import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Badge, Card, EmptyState, Field, PageHeader, Select, Spinner, Stat } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { ApplicationsApi } from "../lib/api";
import { appStateTone, fmtDate } from "../lib/format";
import { APPLICATION_STATES, type ApplicationAnalytics, type ApplicationOut } from "../lib/types";

function Tracker({
  title,
  apps,
  onOpen,
  emptyHint,
}: {
  title: string;
  apps: ApplicationOut[];
  onOpen: (id: string) => void;
  emptyHint: string;
}) {
  return (
    <Card>
      <h2 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">
        {title} ({apps.length})
      </h2>
      {apps.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">{emptyHint}</p>
      ) : (
        <ul className="space-y-2">
          {apps.map((a) => (
            <li
              key={a.id}
              className="cursor-pointer rounded-lg border border-slate-100 px-3 py-2 text-sm hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50"
              onClick={() => onOpen(a.id)}
            >
              <p className="truncate font-medium">{a.title ?? "—"}</p>
              <p className="truncate text-xs text-slate-500 dark:text-slate-400">{a.company ?? "—"}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function Applications() {
  const navigate = useNavigate();
  const toast = useToast();
  const [apps, setApps] = useState<ApplicationOut[]>([]);
  const [stats, setStats] = useState<ApplicationAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {};
      if (statusFilter) params.status = statusFilter;
      const [list, a] = await Promise.all([
        ApplicationsApi.list(params),
        ApplicationsApi.analytics().catch(() => null),
      ]);
      setApps(list);
      setStats(a);
    } catch {
      toast.error("Failed to load applications");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const open = (id: string) => navigate(`/applications/${id}`);

  // Trackers always reflect the full set, independent of the list filter.
  const [interviewApps, setInterviewApps] = useState<ApplicationOut[]>([]);
  const [assessmentApps, setAssessmentApps] = useState<ApplicationOut[]>([]);
  useEffect(() => {
    Promise.all([
      ApplicationsApi.list({ status: "INTERVIEW" }).catch(() => []),
      ApplicationsApi.list({ status: "ASSESSMENT" }).catch(() => []),
    ]).then(([iv, as]) => {
      setInterviewApps(iv);
      setAssessmentApps(as);
    });
  }, [apps]);

  return (
    <div>
      <PageHeader title="Applications" subtitle="Track applications from approval to outcome (manual submission only)" />

      {stats && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <Stat label="Total" value={stats.total} />
            <Stat label="Created" value={stats.created} tone="indigo" />
            <Stat label="Submitted" value={stats.submitted} tone="indigo" />
            <Stat label="Interviews" value={stats.interviews} tone="amber" />
            <Stat label="Offers" value={stats.offers} tone="green" />
            <Stat label="Rejections" value={stats.rejections} tone="red" />
          </div>
          <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Submit rate" value={`${stats.submit_rate}%`} tone="indigo" />
            <Stat label="Interview rate" value={`${stats.interview_rate}%`} tone="amber" />
            <Stat label="Offer rate" value={`${stats.offer_rate}%`} tone="green" />
            <Stat label="Acceptance rate" value={`${stats.acceptance_rate}%`} tone="green" />
          </div>
        </>
      )}

      <div className="mb-5 grid gap-4 lg:grid-cols-2">
        <Tracker title="Interview tracker" apps={interviewApps} onOpen={open} emptyHint="No applications in interviews." />
        <Tracker title="Assessment tracker" apps={assessmentApps} onOpen={open} emptyHint="No applications in assessments." />
      </div>

      <Card className="mb-4">
        <Field label="Status">
          <Select className="w-auto" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            {APPLICATION_STATES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </Select>
        </Field>
      </Card>

      {loading ? (
        <Spinner />
      ) : apps.length === 0 ? (
        <EmptyState title="No applications" hint="Approve a job to create its application." />
      ) : (
        <div className="grid gap-3">
          {apps.map((a) => (
            <Card key={a.id}>
              <div
                className="flex cursor-pointer items-start justify-between gap-3"
                onClick={() => open(a.id)}
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{a.title ?? "—"}</p>
                  <p className="truncate text-sm text-slate-500 dark:text-slate-400">
                    {a.company ?? "—"} · {a.resume_category ?? "no resume"}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">Updated {fmtDate(a.updated_at)}</p>
                </div>
                <Badge tone={appStateTone(a.status)}>{a.status}</Badge>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
