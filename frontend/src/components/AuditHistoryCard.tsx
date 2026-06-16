import { useEffect, useState } from "react";

import { AuditApi } from "../lib/api";
import { fmtDate } from "../lib/format";
import type { AuditOut } from "../lib/types";
import { Badge, Card, Spinner } from "./ui";

/** All audit-log entries scoped to a single job (Phase 7B). */
export function AuditHistoryCard({ jobId }: { jobId: string }) {
  const [events, setEvents] = useState<AuditOut[] | null>(null);

  useEffect(() => {
    let active = true;
    AuditApi.list({ entity: "job", entity_id: jobId, limit: 200 })
      .then((e) => active && setEvents(e))
      .catch(() => active && setEvents([]));
    return () => {
      active = false;
    };
  }, [jobId]);

  return (
    <Card className="lg:col-span-2">
      <h2 className="mb-3 text-lg font-semibold">Audit history</h2>
      {events === null ? (
        <Spinner />
      ) : events.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No audit events for this job.</p>
      ) : (
        <ol className="space-y-2">
          {events.map((e) => (
            <li key={e.id} className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-slate-400">{fmtDate(e.created_at)}</span>
              <Badge tone="slate">{e.action}</Badge>
              <span className="text-slate-500 dark:text-slate-400">by {e.actor}</span>
              {e.payload && Object.keys(e.payload).length > 0 && (
                <span className="text-xs text-slate-400">{JSON.stringify(e.payload)}</span>
              )}
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}
