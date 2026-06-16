import { ReactNode, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { AuditHistoryCard } from "../components/AuditHistoryCard";
import { MaterialsCard } from "../components/MaterialsCard";
import { WorkflowHistoryCard } from "../components/WorkflowHistoryCard";
import { Badge, Button, Card, EmptyState, PageHeader, Select, Spinner } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { JobsApi } from "../lib/api";
import { classificationTone, cn, fmtDate, scoreTone, Tone, workflowTone } from "../lib/format";
import { RESUME_CATEGORIES, type JobDetailOut } from "../lib/types";

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="text-sm text-slate-900 dark:text-slate-100">{children}</dd>
    </div>
  );
}

const BAR_BG: Record<Tone, string> = {
  green: "bg-emerald-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
  slate: "bg-slate-400",
  indigo: "bg-indigo-500",
};

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  const tone = scoreTone(value);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium text-slate-700 dark:text-slate-300">{label}</span>
        <span className="tabular-nums text-slate-500 dark:text-slate-400">{value}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div className={cn("h-full rounded-full transition-all", BAR_BG[tone])} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const [job, setJob] = useState<JobDetailOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [override, setOverride] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    const load = async () => {
      if (!id) {
        setError(true);
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const data = await JobsApi.get(id);
        if (!active) return;
        setJob(data);
        setOverride(data.score?.matched_resume_category ?? "");
        setError(false);
      } catch {
        if (!active) return;
        setError(true);
        toast.error("Failed to load job");
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [id]);

  const applyOverride = async () => {
    if (!id || !override) return;
    setBusy(true);
    try {
      const updated = await JobsApi.setResume(id, override);
      setJob(updated);
      toast.success(`Resume set to ${override}`);
    } catch {
      toast.error("Failed to set resume");
    } finally {
      setBusy(false);
    }
  };

  const rematch = async () => {
    if (!id) return;
    setBusy(true);
    try {
      const updated = await JobsApi.rematch(id);
      setJob(updated);
      setOverride(updated.score?.matched_resume_category ?? "");
      toast.success("Re-matched against current resumes");
    } catch {
      toast.error("Re-match failed");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Spinner />;
  if (error || !job) return <EmptyState title="Job not found" hint="This job may have been removed or the link is invalid." />;

  const score = job.score;

  return (
    <div>
      <div className="mb-4">
        <Button variant="secondary" onClick={() => navigate(-1)}>
          ← Back
        </Button>
      </div>

      <PageHeader title={job.title} subtitle={`${job.company} · ${job.location || "—"}`} />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-lg font-semibold">Overview</h2>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
            <Detail label="Company">{job.company}</Detail>
            <Detail label="Location">{job.location || "—"}</Detail>
            <Detail label="Source">{job.source}</Detail>
            <Detail label="Employment Type">{job.employment_type || "—"}</Detail>
            <Detail label="Remote Status">{job.remote_status || "—"}</Detail>
            <Detail label="Posted Date">{fmtDate(job.posted_date)}</Detail>
            <Detail label="Status">
              <Badge tone={workflowTone(job.status)}>{job.status}</Badge>
            </Detail>
          </dl>
        </Card>

        <Card>
          <h2 className="mb-3 text-lg font-semibold">Score breakdown</h2>
          {score ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-3 dark:bg-slate-800/60">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Total score
                  </p>
                  <p
                    className={cn(
                      "text-3xl font-bold",
                      {
                        green: "text-emerald-600 dark:text-emerald-400",
                        amber: "text-amber-600 dark:text-amber-400",
                        red: "text-red-600 dark:text-red-400",
                        slate: "text-slate-900 dark:text-slate-100",
                        indigo: "text-indigo-600 dark:text-indigo-400",
                      }[scoreTone(score.total_score)],
                    )}
                  >
                    {score.total_score}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-1.5">
                  <Badge tone={scoreTone(score.total_score)}>Score</Badge>
                  <Badge tone={classificationTone(score.classification)}>{score.classification}</Badge>
                </div>
              </div>
              <div className="space-y-3">
                <ScoreBar label="Freshers" value={score.freshers_score} />
                <ScoreBar label="Skills" value={score.skills_score} />
                <ScoreBar label="Location" value={score.location_score} />
                <ScoreBar label="Role" value={score.role_score} />
              </div>
            </div>
          ) : (
            <EmptyState title="No score" hint="This job has not been scored yet." />
          )}
        </Card>

        <Card className="lg:col-span-2">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold">Resume match</h2>
            <div className="flex items-center gap-2">
              {score?.resume_override && <Badge tone="indigo">manual override</Badge>}
              <Badge tone={scoreTone(score?.resume_match_score)}>Match {score?.resume_match_score ?? 0}%</Badge>
              <Badge tone={scoreTone(score?.resume_confidence)}>Confidence {score?.resume_confidence ?? 0}%</Badge>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Selected resume
              </p>
              <p className="mt-1 text-lg font-semibold">{score?.matched_resume_category || "—"}</p>
            </div>
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Override resume
              </p>
              <div className="flex gap-2">
                <Select value={override} onChange={(e) => setOverride(e.target.value)} className="w-auto flex-1">
                  <option value="">Select…</option>
                  {RESUME_CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </Select>
                <Button onClick={applyOverride} disabled={busy || !override}>
                  Save
                </Button>
                <Button variant="secondary" onClick={rematch} disabled={busy}>
                  Re-match
                </Button>
              </div>
            </div>
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Matched skills
              </p>
              {score && score.matched_skills.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {score.matched_skills.map((s) => (
                    <Badge key={s} tone="green">{s}</Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">None</p>
              )}
            </div>
            <div>
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Missing skills
              </p>
              {score && score.missing_skills.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {score.missing_skills.map((s) => (
                    <Badge key={s} tone="red">{s}</Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">None</p>
              )}
            </div>
          </div>

          <div className="mt-4">
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Selection reasoning
            </p>
            <p className="text-sm text-slate-700 dark:text-slate-300">{score?.resume_reasoning || "—"}</p>
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold">Description</h2>
          {job.description ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700 dark:text-slate-300">
              {job.description}
            </p>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">No description available.</p>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold">Apply</h2>
          {job.apply_url ? (
            <Button onClick={() => window.open(job.apply_url as string, "_blank")}>Apply now</Button>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">No apply URL</p>
          )}
        </Card>

        <MaterialsCard jobId={job.id} />

        <WorkflowHistoryCard jobId={job.id} currentState={job.status} />

        <AuditHistoryCard jobId={job.id} />
      </div>
    </div>
  );
}
