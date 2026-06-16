import { useEffect, useState } from "react";

import { JobsApi } from "../lib/api";
import { fmtDate } from "../lib/format";
import type { JobStateHistory } from "../lib/types";
import { Badge, Card, Spinner } from "./ui";

export function WorkflowHistoryCard({ jobId, currentState }: { jobId: string; currentState: string }) {
  const [history, setHistory] = useState<JobStateHistory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    JobsApi.history(jobId)
      .then((h) => active && setHistory(h))
      .catch(() => undefined)
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [jobId]);

  return (
    <Card className="lg:col-span-2">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Workflow history</h2>
        <Badge tone="indigo">{currentState}</Badge>
      </div>
      {loading ? (
        <Spinner />
      ) : history.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No transitions recorded.</p>
      ) : (
        <ol className="space-y-2">
          {history.map((h) => (
            <li key={h.id} className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-slate-400">{fmtDate(h.created_at)}</span>
              <span className="font-medium">
                {h.previous_state ?? "—"} → {h.new_state}
              </span>
              <span className="text-slate-500 dark:text-slate-400">by {h.actor}</span>
              {h.reason && <span className="text-xs text-slate-400">({h.reason})</span>}
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}
