import { useEffect, useState } from "react";

import { WorkflowApi } from "../lib/api";
import { fmtDate, workflowTone } from "../lib/format";
import type { TimelineEvent } from "../lib/types";
import { Badge, Button, Modal, Spinner } from "./ui";

/** Read-only transition timeline for a single job, shown from the Queue. */
export function TransitionHistoryModal({
  jobId,
  title,
  onClose,
}: {
  jobId: string;
  title: string;
  onClose: () => void;
}) {
  const [events, setEvents] = useState<TimelineEvent[] | null>(null);

  useEffect(() => {
    let active = true;
    WorkflowApi.timeline({ job_id: jobId })
      .then((e) => active && setEvents(e))
      .catch(() => active && setEvents([]));
    return () => {
      active = false;
    };
  }, [jobId]);

  return (
    <Modal
      open
      title={`Transition history — ${title}`}
      onClose={onClose}
      footer={
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      }
    >
      {events === null ? (
        <Spinner />
      ) : events.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No transitions recorded.</p>
      ) : (
        <ol className="space-y-3">
          {events.map((e) => (
            <li key={e.id} className="border-l-2 border-slate-200 pl-3 dark:border-slate-700">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <Badge tone={workflowTone(e.previous_state)}>{e.previous_state ?? "—"}</Badge>
                <span className="text-slate-400">→</span>
                <Badge tone={workflowTone(e.new_state)}>{e.new_state}</Badge>
                <span className="text-slate-500 dark:text-slate-400">by {e.actor}</span>
              </div>
              <p className="mt-0.5 text-xs text-slate-400">
                {fmtDate(e.created_at)}
                {e.reason ? ` · ${e.reason}` : ""}
              </p>
            </li>
          ))}
        </ol>
      )}
    </Modal>
  );
}
