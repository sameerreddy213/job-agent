import { useEffect, useMemo, useState } from "react";

import { Badge, Button, Card, EmptyState, Field, Input, PageHeader, Select, Spinner } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { AuditApi } from "../lib/api";
import { downloadCsv, fmtDate } from "../lib/format";
import type { AuditOut } from "../lib/types";

export function AuditLogs() {
  const toast = useToast();
  const [entries, setEntries] = useState<AuditOut[]>([]);
  const [loading, setLoading] = useState(true);

  // Server-side filters
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [limit, setLimit] = useState(50);

  // Client-side free-text search
  const [search, setSearch] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { limit };
      if (action.trim()) params.action = action.trim();
      if (actor.trim()) params.actor = actor.trim();
      setEntries(await AuditApi.list(params));
    } catch {
      toast.error("Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  };

  // Reload whenever the server-side filters change.
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [action, actor, limit]);

  const displayed = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return entries;
    return entries.filter((e) => {
      const haystack = [
        e.action,
        e.actor,
        e.entity ?? "",
        e.entity_id ?? "",
        JSON.stringify(e.payload ?? {}),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [entries, search]);

  const exportCsv = () => {
    if (!displayed.length) {
      toast.info("Nothing to export");
      return;
    }
    const rows = displayed.map((e) => ({
      created_at: e.created_at,
      actor: e.actor,
      action: e.action,
      entity: e.entity ?? "",
      entity_id: e.entity_id ?? "",
      payload: JSON.stringify(e.payload ?? {}),
    }));
    downloadCsv("audit.csv", rows);
    toast.success(`Exported ${rows.length} ${rows.length === 1 ? "entry" : "entries"}`);
  };

  return (
    <div>
      <PageHeader
        title="Audit Logs"
        subtitle="System and user activity history"
        actions={
          <Button variant="secondary" onClick={exportCsv} disabled={!displayed.length}>
            Export CSV
          </Button>
        }
      />

      <Card className="mb-5">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Action">
            <Input
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="e.g. login"
            />
          </Field>
          <Field label="Actor">
            <Input
              value={actor}
              onChange={(e) => setActor(e.target.value)}
              placeholder="e.g. admin"
            />
          </Field>
          <Field label="Search">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter displayed rows…"
            />
          </Field>
          <Field label="Limit">
            <Select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </Select>
          </Field>
        </div>
      </Card>

      {loading ? (
        <Spinner />
      ) : displayed.length === 0 ? (
        <EmptyState
          title="No audit entries"
          hint={
            entries.length > 0 && search.trim()
              ? "No rows match your search."
              : "Adjust the filters above or trigger some activity."
          }
        />
      ) : (
        <>
          {/* Mobile: stacked cards */}
          <div className="space-y-3 md:hidden">
            {displayed.map((e) => (
              <Card key={e.id}>
                <div className="flex items-start justify-between gap-2">
                  <Badge tone="indigo">{e.action}</Badge>
                  <span className="text-xs text-slate-500 dark:text-slate-400">{fmtDate(e.created_at)}</span>
                </div>
                <dl className="mt-2 space-y-1 text-sm text-slate-600 dark:text-slate-300">
                  <div className="flex justify-between gap-2">
                    <dt className="text-slate-500 dark:text-slate-400">Actor</dt>
                    <dd className="truncate font-medium">{e.actor}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-slate-500 dark:text-slate-400">Entity</dt>
                    <dd className="truncate">{e.entity ?? "—"}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-slate-500 dark:text-slate-400">Entity ID</dt>
                    <dd className="truncate font-mono text-xs">{e.entity_id ?? "—"}</dd>
                  </div>
                </dl>
                <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-slate-50 p-2 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {JSON.stringify(e.payload ?? {}, null, 2)}
                </pre>
              </Card>
            ))}
          </div>

          {/* Desktop: table */}
          <Card className="hidden overflow-hidden p-0 md:block">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
                  <tr>
                    <th className="px-4 py-3 font-medium">Time</th>
                    <th className="px-4 py-3 font-medium">Actor</th>
                    <th className="px-4 py-3 font-medium">Action</th>
                    <th className="px-4 py-3 font-medium">Entity</th>
                    <th className="px-4 py-3 font-medium">Entity ID</th>
                    <th className="px-4 py-3 font-medium">Payload</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {displayed.map((e) => (
                    <tr key={e.id} className="align-top hover:bg-slate-50 dark:hover:bg-slate-800/40">
                      <td className="whitespace-nowrap px-4 py-3 text-slate-500 dark:text-slate-400">
                        {fmtDate(e.created_at)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-medium">{e.actor}</td>
                      <td className="px-4 py-3">
                        <Badge tone="indigo">{e.action}</Badge>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-slate-600 dark:text-slate-300">
                        {e.entity ?? "—"}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-500 dark:text-slate-400">
                        {e.entity_id ?? "—"}
                      </td>
                      <td className="max-w-xs px-4 py-3">
                        <span
                          className="block truncate font-mono text-xs text-slate-500 dark:text-slate-400"
                          title={JSON.stringify(e.payload ?? {})}
                        >
                          {JSON.stringify(e.payload ?? {})}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            Showing {displayed.length} of {entries.length} loaded {entries.length === 1 ? "entry" : "entries"}.
          </p>
        </>
      )}
    </div>
  );
}
