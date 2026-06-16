import { useEffect, useState } from "react";

import { useToast } from "../context/ToastContext";
import { ApplicationsApi } from "../lib/api";
import type { ChecklistOut, PacketOut } from "../lib/types";
import { Badge, Button, Card, Spinner } from "./ui";

/**
 * Manual Apply Assistant (Phase 8C). Shows the application checklist, lets the
 * user generate and download a self-contained packet, and confirm they are
 * ready to apply. It never submits — the user applies manually.
 */
export function ManualApplyCard({
  appId,
  onConfirmed,
}: {
  appId: string;
  onConfirmed?: () => void;
}) {
  const toast = useToast();
  const [checklist, setChecklist] = useState<ChecklistOut | null>(null);
  const [packet, setPacket] = useState<PacketOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    const [c, p] = await Promise.all([
      ApplicationsApi.checklist(appId),
      ApplicationsApi.packetStatus(appId).catch(() => null),
    ]);
    setChecklist(c);
    setPacket(p);
  };

  useEffect(() => {
    let active = true;
    refresh()
      .catch(() => active && toast.error("Failed to load checklist"))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId]);

  const generate = async () => {
    setBusy(true);
    try {
      setPacket(await ApplicationsApi.generatePacket(appId));
      await refresh();
      toast.success("Packet generated");
    } catch (err: any) {
      toast.error(err?.response?.status === 400 ? "Generate materials first" : "Packet generation failed");
    } finally {
      setBusy(false);
    }
  };

  const download = async (fmt: string) => {
    try {
      await ApplicationsApi.downloadPacket(appId, fmt);
    } catch {
      toast.error("Download failed");
    }
  };

  const confirm = async () => {
    setBusy(true);
    try {
      await ApplicationsApi.confirmReady(appId);
      await refresh();
      toast.success("Marked ready to apply");
      onConfirmed?.();
    } catch {
      toast.error("Could not confirm");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Card className="lg:col-span-2"><Spinner /></Card>;

  return (
    <Card className="lg:col-span-2">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Manual apply assistant</h2>
        {checklist && (
          <Badge tone={checklist.complete ? "green" : "amber"}>
            {checklist.complete ? "Checklist complete" : "Checklist incomplete"}
          </Badge>
        )}
      </div>

      {checklist && (
        <ul className="mb-4 space-y-1.5">
          {checklist.items.map((i) => (
            <li key={i.key} className="flex items-center gap-2 text-sm">
              <span className={i.done ? "text-emerald-600 dark:text-emerald-400" : "text-slate-400"}>
                {i.done ? "✓" : "○"}
              </span>
              <span className={i.done ? "" : "text-slate-500 dark:text-slate-400"}>{i.label}</span>
              {i.required && !i.done && <Badge tone="red">required</Badge>}
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={generate} disabled={busy}>
          {packet?.generated ? "Regenerate packet" : "Generate packet"}
        </Button>
        {packet?.generated &&
          packet.formats.map((f) => (
            <Button key={f} variant="secondary" onClick={() => download(f)}>
              ⬇ {f.toUpperCase()}
            </Button>
          ))}
        <Button
          variant={checklist?.ready_confirmed ? "ghost" : "primary"}
          onClick={confirm}
          disabled={busy || checklist?.ready_confirmed}
        >
          {checklist?.ready_confirmed ? "Ready confirmed ✓" : "Mark ready to apply"}
        </Button>
      </div>

      <p className="mt-3 text-xs text-slate-400">
        The packet bundles your resume, cover letter, answers, and notes for manual submission.
        Nothing is submitted automatically.
      </p>
    </Card>
  );
}
