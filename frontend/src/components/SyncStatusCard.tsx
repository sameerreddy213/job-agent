import { useEffect, useState } from "react";

import { useToast } from "../context/ToastContext";
import { AdminApi } from "../lib/api";
import { cn, fmtDate, healthTone } from "../lib/format";
import type { SyncStatus } from "../lib/types";
import { Badge, Button, Card, Spinner } from "./ui";

function statusTone(status: string | null) {
  if (status === "success") return healthTone("HEALTHY");
  if (status === "failed") return healthTone("FAILED");
  return healthTone("WARNING");
}

export function SyncStatusCard() {
  const toast = useToast();
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      setStatus(await AdminApi.syncStatus());
    } catch {
      /* non-fatal */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const syncNow = async () => {
    setBusy(true);
    try {
      const res = (await AdminApi.syncSheets()) as { status?: string };
      if (res.status === "success") toast.success("Sheets synced");
      else if (res.status === "not_configured") toast.info("Google Sheets not configured");
      else toast.error("Sync failed");
      await load();
    } catch {
      toast.error("Sync failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Google Sheets sync</h2>
        <Button onClick={syncNow} disabled={busy}>
          {busy ? "Syncing…" : "Sync now"}
        </Button>
      </div>

      {loading ? (
        <Spinner />
      ) : !status ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Status unavailable.</p>
      ) : !status.configured ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Not configured. Set <code>GOOGLE_SHEET_ID</code> and service-account credentials, then enable sync.
        </p>
      ) : (
        <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">Last sync</dt>
            <dd className="mt-1 font-medium">{fmtDate(status.last_sync_at)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">Status</dt>
            <dd className="mt-1">
              <Badge tone={statusTone(status.last_status)}>{status.last_status ?? "—"}</Badge>
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">Rows written</dt>
            <dd className="mt-1 font-medium">{status.rows_written}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">Latency</dt>
            <dd className="mt-1 font-medium">{status.duration_ms} ms</dd>
          </div>
          <div className="col-span-2 sm:col-span-4">
            <span className={cn("text-xs", status.enabled ? "text-emerald-600 dark:text-emerald-400" : "text-slate-500")}>
              Scheduled sync {status.enabled ? `on (every ${status.interval_minutes}m)` : "off"}
            </span>
            {status.error && <p className="mt-1 text-xs text-red-500">{status.error}</p>}
          </div>
        </dl>
      )}
    </Card>
  );
}
