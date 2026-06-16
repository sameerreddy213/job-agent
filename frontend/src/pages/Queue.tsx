import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { TransitionHistoryModal } from "../components/TransitionHistoryModal";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Select,
  Spinner,
  Stat,
} from "../components/ui";
import { useToast } from "../context/ToastContext";
import { JobsApi, QueueApi, WorkflowApi } from "../lib/api";
import { classificationTone, fmtDuration, scoreTone, workflowTone } from "../lib/format";
import type { BulkResult, JobOut, QueueCounts, WorkflowAnalytics } from "../lib/types";

type PendingBulk = {
  verb: string; // imperative, e.g. "Approve"
  pastLabel: string; // past tense for the toast, e.g. "Approved"
  count: number;
  variant: "primary" | "danger" | "secondary";
  fn: (ids: string[]) => Promise<BulkResult>;
};

const STATUS_OPTIONS = [
  { value: "", label: "All" },
  { value: "AUTO_APPROVE_ELIGIBLE", label: "Auto-approve eligible" },
  { value: "REVIEW_QUEUE", label: "Review" },
];

export function Queue() {
  const toast = useToast();
  const navigate = useNavigate();

  const [jobs, setJobs] = useState<JobOut[]>([]);
  const [counts, setCounts] = useState<QueueCounts | null>(null);
  const [stats, setStats] = useState<WorkflowAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [historyJob, setHistoryJob] = useState<JobOut | null>(null);
  const [pending, setPending] = useState<PendingBulk | null>(null);

  const [classification, setClassification] = useState("");
  const [source, setSource] = useState("");
  const [minScore, setMinScore] = useState("");
  const [location, setLocation] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {};
      if (classification) params.classification = classification;
      if (source.trim()) params.source = source.trim();
      if (minScore.trim() !== "") params.min_score = Number(minScore);
      const [list, c, s] = await Promise.all([
        QueueApi.list(params),
        QueueApi.counts(),
        WorkflowApi.analytics(30).catch(() => null),
      ]);
      setJobs(list);
      setCounts(c);
      setStats(s);
      setSelected(new Set());
    } catch {
      toast.error("Failed to load queue");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [classification, source, minScore]);

  const visible = jobs.filter((j) =>
    location.trim() === "" ? true : (j.location ?? "").toLowerCase().includes(location.trim().toLowerCase()),
  );

  const openJob = (id: string) => navigate(`/jobs/${id}`);

  const removeJobs = (ids: string[]) => {
    const idset = new Set(ids);
    setJobs((prev) => prev.filter((j) => !idset.has(j.id)));
    setSelected((prev) => {
      const next = new Set(prev);
      ids.forEach((id) => next.delete(id));
      return next;
    });
  };

  const act = async (id: string, fn: () => Promise<unknown>, msg: string) => {
    setBusy(true);
    try {
      await fn();
      removeJobs([id]);
      toast.success(msg);
      QueueApi.counts().then(setCounts).catch(() => undefined);
    } catch (err: any) {
      toast.error(err?.response?.status === 409 ? "Invalid action for this job's state" : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const allSelected = visible.length > 0 && visible.every((j) => selected.has(j.id));
  const toggleAll = () =>
    setSelected(allSelected ? new Set() : new Set(visible.map((j) => j.id)));

  const requestBulk = (p: Omit<PendingBulk, "count">) => {
    if (!selected.size) return;
    setPending({ ...p, count: selected.size });
  };

  const runBulk = async () => {
    if (!pending) return;
    const ids = [...selected];
    setBusy(true);
    try {
      const res = await pending.fn(ids);
      removeJobs(ids);
      toast.success(`${pending.pastLabel}: ${res.succeeded} ok, ${res.failed} failed`);
      QueueApi.counts().then(setCounts).catch(() => undefined);
      WorkflowApi.analytics(30).then(setStats).catch(() => undefined);
    } catch {
      toast.error("Bulk action failed");
    } finally {
      setBusy(false);
      setPending(null);
    }
  };

  return (
    <div>
      <PageHeader title="Queue" subtitle="Jobs awaiting review or auto-approval" />

      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Auto eligible" value={counts?.auto_eligible ?? "—"} tone="green" />
        <Stat label="Review queue" value={counts?.review_queue ?? "—"} tone="amber" />
        <Stat label="Approval rate" value={stats ? `${stats.approval_pct}%` : "—"} tone="green" />
        <Stat label="Rejection rate" value={stats ? `${stats.rejection_pct}%` : "—"} tone="red" />
        <Stat label="Snooze rate" value={stats ? `${stats.snooze_pct}%` : "—"} tone="amber" />
        <Stat label="Avg review" value={stats ? fmtDuration(stats.avg_review_seconds) : "—"} tone="indigo" />
      </div>

      <Card className="mb-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Classification">
            <Select value={classification} onChange={(e) => setClassification(e.target.value)}>
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </Select>
          </Field>
          <Field label="Source"><Input value={source} onChange={(e) => setSource(e.target.value)} placeholder="e.g. greenhouse" /></Field>
          <Field label="Min score"><Input type="number" value={minScore} onChange={(e) => setMinScore(e.target.value)} placeholder="0–100" /></Field>
          <Field label="Location"><Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Remote" /></Field>
        </div>
      </Card>

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <Card className="mb-4 flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium">{selected.size} selected</span>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => requestBulk({ verb: "Approve", pastLabel: "Approved", variant: "primary", fn: JobsApi.bulkApprove })} disabled={busy}>Approve</Button>
            <Button variant="danger" onClick={() => requestBulk({ verb: "Reject", pastLabel: "Rejected", variant: "danger", fn: JobsApi.bulkReject })} disabled={busy}>Reject</Button>
            <Button variant="secondary" onClick={() => requestBulk({ verb: "Archive", pastLabel: "Archived", variant: "secondary", fn: JobsApi.bulkArchive })} disabled={busy}>Archive</Button>
            <Button variant="ghost" onClick={() => setSelected(new Set())}>Clear</Button>
          </div>
        </Card>
      )}

      {loading ? (
        <Spinner />
      ) : visible.length === 0 ? (
        <EmptyState title="Queue is empty" hint="Run the pipeline to populate jobs." />
      ) : (
        <>
          <div className="mb-2 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={allSelected} onChange={toggleAll} className="h-4 w-4 rounded" />
            <span className="text-slate-500 dark:text-slate-400">Select all ({visible.length})</span>
          </div>

          <div className="grid gap-3">
            {visible.map((job) => (
              <Card key={job.id} className="card-hover">
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={selected.has(job.id)}
                    onChange={() => toggle(job.id)}
                    className="mt-1 h-4 w-4 shrink-0 rounded"
                  />
                  <div className="min-w-0 flex-1 cursor-pointer" onClick={() => openJob(job.id)}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{job.title}</p>
                        <p className="truncate text-sm text-slate-500 dark:text-slate-400">
                          {job.company} · {job.location ?? "—"} · {job.source}
                        </p>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-1">
                        <Badge tone={scoreTone(job.score?.total_score)}>{job.score?.total_score ?? "—"}</Badge>
                        <Badge tone={classificationTone(job.score?.classification)}>
                          {job.score?.classification === "AUTO_APPROVE_ELIGIBLE" ? "auto" : "review"}
                        </Badge>
                        <Badge tone={workflowTone(job.status)}>{job.status}</Badge>
                      </div>
                    </div>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      Resume: {job.score?.matched_resume_category ?? "—"}
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button onClick={() => act(job.id, () => JobsApi.approve(job.id), "Approved")} disabled={busy}>Approve</Button>
                  <Button variant="danger" onClick={() => act(job.id, () => JobsApi.reject(job.id), "Rejected")} disabled={busy}>Reject</Button>
                  <Button variant="secondary" onClick={() => act(job.id, () => JobsApi.snooze(job.id, 24), "Snoozed 24h")} disabled={busy}>Snooze</Button>
                  <Button variant="ghost" onClick={() => act(job.id, () => JobsApi.archive(job.id), "Archived")} disabled={busy}>Archive</Button>
                  <Button variant="ghost" onClick={() => setHistoryJob(job)}>History</Button>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {historyJob && (
        <TransitionHistoryModal
          jobId={historyJob.id}
          title={historyJob.title}
          onClose={() => setHistoryJob(null)}
        />
      )}

      <ConfirmDialog
        open={pending !== null}
        title={`${pending?.verb ?? "Confirm"} ${pending?.count ?? 0} job(s)?`}
        message={`This will ${pending?.verb.toLowerCase() ?? "update"} ${pending?.count ?? 0} selected job(s). The action is recorded in the workflow audit log.`}
        confirmLabel={pending?.verb ?? "Confirm"}
        confirmVariant={pending?.variant ?? "primary"}
        busy={busy}
        onConfirm={runBulk}
        onCancel={() => setPending(null)}
      />
    </div>
  );
}
