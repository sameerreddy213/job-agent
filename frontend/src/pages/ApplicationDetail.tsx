import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Badge, Button, Card, EmptyState, Input, PageHeader, Select, Spinner } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { ApplicationsApi } from "../lib/api";
import { appStateTone, fmtDate } from "../lib/format";
import { APP_TRANSITIONS, type ApplicationDetailOut, type ApplicationState } from "../lib/types";

export function ApplicationDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const [app, setApp] = useState<ApplicationDetailOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [target, setTarget] = useState("");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");

  const load = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await ApplicationsApi.get(id);
      setApp(data);
      setNotes(data.notes ?? "");
      setTarget("");
    } catch {
      toast.error("Failed to load application");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const doTransition = async () => {
    if (!id || !target) return;
    setBusy(true);
    try {
      const updated = await ApplicationsApi.transition(id, target, reason || undefined);
      setApp(updated);
      setReason("");
      setTarget("");
      toast.success(`Moved to ${updated.status}`);
    } catch (err: any) {
      toast.error(err?.response?.status === 409 ? "Invalid state transition" : "Transition failed");
    } finally {
      setBusy(false);
    }
  };

  const saveNotes = async () => {
    if (!id) return;
    setBusy(true);
    try {
      const updated = await ApplicationsApi.update(id, { notes });
      setApp(updated);
      toast.success("Notes saved");
    } catch {
      toast.error("Failed to save notes");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Spinner />;
  if (!app) return <EmptyState title="Application not found" />;

  const nextStates = APP_TRANSITIONS[app.status as ApplicationState] ?? [];

  return (
    <div>
      <div className="mb-4">
        <Button variant="secondary" onClick={() => navigate(-1)}>← Back</Button>
      </div>

      <PageHeader
        title={app.title ?? "Application"}
        subtitle={`${app.company ?? "—"} · ${app.resume_category ?? "no resume"}`}
        actions={<Badge tone={appStateTone(app.status)}>{app.status}</Badge>}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-lg font-semibold">State</h2>
          <dl className="grid grid-cols-2 gap-y-2 text-sm">
            <dt className="text-slate-500 dark:text-slate-400">Current</dt>
            <dd><Badge tone={appStateTone(app.status)}>{app.status}</Badge></dd>
            <dt className="text-slate-500 dark:text-slate-400">Submitted</dt>
            <dd>{fmtDate(app.submitted_at)}</dd>
            <dt className="text-slate-500 dark:text-slate-400">Created</dt>
            <dd>{fmtDate(app.created_at)}</dd>
          </dl>

          {nextStates.length > 0 ? (
            <div className="mt-4 space-y-2">
              <Select value={target} onChange={(e) => setTarget(e.target.value)}>
                <option value="">Move to…</option>
                {nextStates.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </Select>
              <Input placeholder="Reason (optional)" value={reason} onChange={(e) => setReason(e.target.value)} />
              <Button onClick={doTransition} disabled={busy || !target}>Apply transition</Button>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">Terminal state — no further transitions.</p>
          )}

          <p className="mt-3 text-xs text-slate-400">
            Submission is manual. This engine never submits applications automatically.
          </p>
        </Card>

        <Card>
          <h2 className="mb-3 text-lg font-semibold">Notes</h2>
          <textarea
            className="h-28 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-800"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add notes about this application…"
          />
          <Button className="mt-2" variant="secondary" onClick={saveNotes} disabled={busy}>Save notes</Button>
        </Card>

        <Card className="lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold">Documents</h2>
          {app.documents.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              No documents linked. {app.material_id ? "" : "Materials have not been generated yet."}
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {app.documents.map((d) => (
                <Badge key={d.id} tone="indigo">{d.kind} · {d.fmt}</Badge>
              ))}
            </div>
          )}
          {app.job_id && (
            <Button className="mt-3" variant="ghost" onClick={() => navigate(`/jobs/${app.job_id}`)}>
              View job & materials →
            </Button>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold">Application answers</h2>
          {app.answers.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">No answers captured.</p>
          ) : (
            <dl className="space-y-3">
              {app.answers.map((a) => (
                <div key={a.id}>
                  <dt className="text-sm font-medium">{a.question}</dt>
                  <dd className="text-sm text-slate-600 dark:text-slate-300">{a.answer ?? "—"}</dd>
                </div>
              ))}
            </dl>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <h2 className="mb-3 text-lg font-semibold">Timeline</h2>
          {app.events.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">No events recorded.</p>
          ) : (
            <ol className="space-y-2">
              {app.events.map((e) => (
                <li key={e.id} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-slate-400">{fmtDate(e.created_at)}</span>
                  <Badge tone={appStateTone(e.previous_state)}>{e.previous_state ?? "—"}</Badge>
                  <span className="text-slate-400">→</span>
                  <Badge tone={appStateTone(e.new_state)}>{e.new_state}</Badge>
                  <span className="text-slate-500 dark:text-slate-400">by {e.actor}</span>
                  {e.reason && <span className="text-xs text-slate-400">({e.reason})</span>}
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>
    </div>
  );
}
