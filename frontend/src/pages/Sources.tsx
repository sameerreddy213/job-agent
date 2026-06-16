import { useEffect, useState } from "react";

import { Badge, Button, Card, EmptyState, PageHeader, Spinner } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { SourcesApi } from "../lib/api";
import { fmtDate, healthTone } from "../lib/format";
import type { RunHealthOut, SourceOut } from "../lib/types";

export function Sources() {
  const toast = useToast();
  const [sources, setSources] = useState<SourceOut[]>([]);
  const [health, setHealth] = useState<Record<string, RunHealthOut>>({});
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [srcs, runs] = await Promise.all([SourcesApi.list(), SourcesApi.health()]);
      const map: Record<string, RunHealthOut> = {};
      for (const run of runs) {
        const existing = map[run.source];
        if (!existing || new Date(run.run_at).getTime() > new Date(existing.run_at).getTime()) {
          map[run.source] = run;
        }
      }
      setSources(srcs);
      setHealth(map);
    } catch {
      toast.error("Failed to load sources");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const toggleEnabled = async (source: SourceOut) => {
    setUpdatingId(source.id);
    try {
      const updated = await SourcesApi.update(source.id, { enabled: !source.enabled });
      setSources((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
      toast.success(`${updated.name} ${updated.enabled ? "enabled" : "disabled"}`);
    } catch {
      toast.error("Failed to update source");
    } finally {
      setUpdatingId(null);
    }
  };

  if (loading) return <Spinner />;

  return (
    <div>
      <PageHeader title="Sources" subtitle={`${sources.length} configured source${sources.length === 1 ? "" : "s"}`} />

      {sources.length === 0 ? (
        <EmptyState title="No sources" hint="No job sources are configured yet." />
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {sources.map((source) => {
            const run = health[source.name];
            const errorText = run?.detail ?? source.last_error;
            return (
              <Card key={source.id}>
                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium capitalize">{source.name}</span>
                    <Badge tone="indigo">{source.apply_policy}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={source.enabled ? "green" : "slate"}>
                      {source.enabled ? "Enabled" : "Disabled"}
                    </Badge>
                    <Button
                      variant="secondary"
                      onClick={() => toggleEnabled(source)}
                      disabled={updatingId === source.id}
                    >
                      {updatingId === source.id ? "Saving…" : source.enabled ? "Disable" : "Enable"}
                    </Button>
                  </div>
                </div>

                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{source.kind}</p>

                <div className="mt-3 border-t border-slate-100 pt-3 dark:border-slate-800">
                  {run ? (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          Health
                        </span>
                        <Badge tone={healthTone(run.status)}>{run.status}</Badge>
                      </div>
                      <dl className="mt-2 space-y-1 text-sm text-slate-500 dark:text-slate-400">
                        <div className="flex justify-between">
                          <dt>Jobs found</dt>
                          <dd>{run.jobs_found}</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt>Errors</dt>
                          <dd>{run.errors}</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt>Response</dt>
                          <dd>{run.response_time_ms} ms</dd>
                        </div>
                        <div className="flex justify-between">
                          <dt>Last run</dt>
                          <dd>{fmtDate(run.run_at)}</dd>
                        </div>
                      </dl>
                    </>
                  ) : (
                    <p className="text-sm text-slate-500 dark:text-slate-400">No health data yet.</p>
                  )}

                  {errorText && <p className="mt-2 text-xs text-red-500">{errorText}</p>}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
