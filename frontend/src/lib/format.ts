// Small formatting + style helpers shared across pages.

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

export function fmtDay(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString();
}

// CSV export helper (used by Audit Logs).
export function downloadCsv(filename: string, rows: Record<string, unknown>[]): void {
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const esc = (v: unknown) => {
    const s = v == null ? "" : typeof v === "object" ? JSON.stringify(v) : String(v);
    return `"${s.replace(/"/g, '""')}"`;
  };
  const csv = [headers.join(","), ...rows.map((r) => headers.map((h) => esc(r[h])).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export type Tone = "green" | "amber" | "red" | "slate" | "indigo";

export function classificationTone(classification: string | undefined | null): Tone {
  switch (classification) {
    case "AUTO_APPROVE_ELIGIBLE":
      return "green";
    case "REVIEW_QUEUE":
      return "amber";
    case "REJECT":
    case "REJECTED_FILTER":
      return "red";
    default:
      return "slate";
  }
}

export function healthTone(status: string | undefined | null): Tone {
  switch (status) {
    case "HEALTHY":
      return "green";
    case "WARNING":
      return "amber";
    case "FAILED":
      return "red";
    default:
      return "slate";
  }
}

export function scoreTone(score: number | undefined | null): Tone {
  if (score == null) return "slate";
  if (score >= 90) return "green";
  if (score >= 70) return "amber";
  return "red";
}

// Workflow-state badge colour (Phase 7B).
export function workflowTone(state: string | undefined | null): Tone {
  switch (state) {
    case "APPROVED":
    case "MATERIALS_GENERATED":
    case "READY_TO_APPLY":
    case "APPLIED":
      return "green";
    case "REVIEW_QUEUE":
    case "SCORED":
      return "amber";
    case "REJECTED":
    case "FILTERED":
    case "FAILED":
      return "red";
    case "DISCOVERED":
      return "indigo";
    default:
      return "slate";
  }
}

// Application-state badge colour (Phase 8A).
export function appStateTone(state: string | undefined | null): Tone {
  switch (state) {
    case "OFFER":
    case "ACCEPTED":
      return "green";
    case "SUBMITTED":
    case "READY":
      return "indigo";
    case "INTERVIEW":
    case "ASSESSMENT":
    case "IN_PROGRESS":
      return "amber";
    case "REJECTED":
    case "WITHDRAWN":
      return "red";
    default:
      return "slate";
  }
}

// Humanise a duration given in seconds, e.g. 5400 -> "1.5h", 90 -> "1.5m".
export function fmtDuration(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
  return `${(seconds / 86400).toFixed(1)}d`;
}
