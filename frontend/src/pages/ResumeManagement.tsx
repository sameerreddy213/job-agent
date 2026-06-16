import { useEffect, useRef, useState } from "react";

import { Badge, Button, Card, EmptyState, Field, PageHeader, Select, Spinner } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { ResumesApi } from "../lib/api";
import { fmtDate } from "../lib/format";
import type { ResumeDetailOut, ResumeSummaryOut } from "../lib/types";

const KNOWN_CATEGORIES = [
  "SDE",
  "SDE_1",
  "Software_Engineer",
  "Associate_Software_Engineer",
  "Graduate_Engineer_Trainee",
  "Frontend",
  "Backend_Developer",
  "Full_Stack",
  "MERN_Stack",
  "React_Developer",
  "Node_js_Developer",
  "Java_Developer",
  "AI_Data_Platform_Engineer",
];

export function ResumeManagement() {
  const toast = useToast();
  const [summary, setSummary] = useState<ResumeSummaryOut[]>([]);
  const [loading, setLoading] = useState(true);

  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<ResumeDetailOut | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [uploading, setUploading] = useState<string | null>(null);
  const [rollingBack, setRollingBack] = useState<number | null>(null);

  const [newCategory, setNewCategory] = useState<string>("");
  const [addUploading, setAddUploading] = useState(false);
  const newFileRef = useRef<HTMLInputElement | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setSummary(await ResumesApi.summary());
    } catch {
      toast.error("Failed to load resumes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const upload = async (category: string, file: File | undefined) => {
    if (!file) {
      toast.error("Select a file to upload");
      return;
    }
    setUploading(category);
    try {
      await ResumesApi.upload(category, file);
      toast.success(`Uploaded new resume for ${category}`);
      if (expanded === category) {
        await openHistory(category);
      }
      await load();
    } catch {
      toast.error("Upload failed");
    } finally {
      setUploading(null);
    }
  };

  const openHistory = async (category: string) => {
    setHistoryLoading(true);
    try {
      setDetail(await ResumesApi.versions(category));
    } catch {
      toast.error("Failed to load version history");
      setDetail(null);
    } finally {
      setHistoryLoading(false);
    }
  };

  const toggleHistory = async (category: string) => {
    if (expanded === category) {
      setExpanded(null);
      setDetail(null);
      return;
    }
    setExpanded(category);
    setDetail(null);
    await openHistory(category);
  };

  const rollback = async (category: string, version: number) => {
    setRollingBack(version);
    try {
      await ResumesApi.rollback(category, version);
      toast.success(`Rolled back ${category} to version ${version}`);
      await openHistory(category);
      await load();
    } catch {
      toast.error("Rollback failed");
    } finally {
      setRollingBack(null);
    }
  };

  const addCategory = async () => {
    if (!newCategory) {
      toast.error("Select a category");
      return;
    }
    const file = newFileRef.current?.files?.[0];
    if (!file) {
      toast.error("Select a file to upload");
      return;
    }
    setAddUploading(true);
    try {
      await ResumesApi.upload(newCategory, file);
      toast.success(`Uploaded new resume for ${newCategory}`);
      if (newFileRef.current) newFileRef.current.value = "";
      setNewCategory("");
      await load();
    } catch {
      toast.error("Upload failed");
    } finally {
      setAddUploading(false);
    }
  };

  const existing = new Set(summary.map((s) => s.category));
  const availableToAdd = KNOWN_CATEGORIES.filter((c) => !existing.has(c));

  return (
    <div>
      <PageHeader title="Resumes" subtitle="Manage role-specific resume versions" />

      <Card className="mb-6">
        <h2 className="mb-3 text-sm font-semibold">Add a new category</h2>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="sm:w-64">
            <Field label="Category">
              <Select value={newCategory} onChange={(e) => setNewCategory(e.target.value)}>
                <option value="">Select category…</option>
                {availableToAdd.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <div className="flex-1">
            <Field label="Resume file">
              <input
                ref={newFileRef}
                type="file"
                className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-600 file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-indigo-500 dark:text-slate-300"
              />
            </Field>
          </div>
          <Button onClick={addCategory} disabled={addUploading || availableToAdd.length === 0}>
            {addUploading ? "Uploading…" : "Upload"}
          </Button>
        </div>
        {availableToAdd.length === 0 && (
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">All known categories already have resumes.</p>
        )}
      </Card>

      {loading ? (
        <Spinner />
      ) : summary.length === 0 ? (
        <EmptyState title="No resumes yet" hint="Upload a resume for a role category." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {summary.map((s) => (
            <ResumeCard
              key={s.category}
              summary={s}
              expanded={expanded === s.category}
              detail={expanded === s.category ? detail : null}
              historyLoading={expanded === s.category && historyLoading}
              uploading={uploading === s.category}
              rollingBack={expanded === s.category ? rollingBack : null}
              onUpload={(file) => upload(s.category, file)}
              onToggleHistory={() => toggleHistory(s.category)}
              onRollback={(version) => rollback(s.category, version)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ResumeCard({
  summary,
  expanded,
  detail,
  historyLoading,
  uploading,
  rollingBack,
  onUpload,
  onToggleHistory,
  onRollback,
}: {
  summary: ResumeSummaryOut;
  expanded: boolean;
  detail: ResumeDetailOut | null;
  historyLoading: boolean;
  uploading: boolean;
  rollingBack: number | null;
  onUpload: (file: File | undefined) => void;
  onToggleHistory: () => void;
  onRollback: (version: number) => void;
}) {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const current = summary.current_version;

  const handleUpload = () => {
    onUpload(fileRef.current?.files?.[0]);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <Card className={expanded ? "sm:col-span-2 lg:col-span-3" : undefined}>
      <div className="flex items-start justify-between gap-2">
        <span className="font-medium">{summary.category}</span>
        <Badge tone={current ? "green" : "slate"}>{current ? `v${current.version_number}` : "none"}</Badge>
      </div>

      <dl className="mt-2 space-y-1 text-sm text-slate-500 dark:text-slate-400">
        <div className="flex justify-between">
          <dt>Previous versions</dt>
          <dd>{summary.previous_versions}</dd>
        </div>
        <div className="flex justify-between">
          <dt>Last updated</dt>
          <dd>{fmtDate(summary.last_updated)}</dd>
        </div>
      </dl>

      {current && current.skills_detected.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {current.skills_detected.map((skill) => (
            <Badge key={skill} tone="indigo">
              {skill}
            </Badge>
          ))}
        </div>
      )}

      <div className="mt-4 space-y-2">
        <input
          ref={fileRef}
          type="file"
          className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-200 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-300 dark:text-slate-300 dark:file:bg-slate-700 dark:file:text-slate-200 dark:hover:file:bg-slate-600"
        />
        <div className="flex gap-2">
          <Button onClick={handleUpload} disabled={uploading}>
            {uploading ? "Uploading…" : "Upload"}
          </Button>
          <Button variant="secondary" onClick={onToggleHistory}>
            {expanded ? "Hide history" : "View history"}
          </Button>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 border-t border-slate-200 pt-4 dark:border-slate-800">
          <h3 className="mb-2 text-sm font-semibold">Version history</h3>
          {historyLoading ? (
            <Spinner />
          ) : !detail || detail.versions.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">No versions yet.</p>
          ) : (
            <ul className="space-y-2">
              {detail.versions.map((v) => (
                <li
                  key={v.id}
                  className="flex flex-col gap-2 rounded-lg border border-slate-200 p-3 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">v{v.version_number}</span>
                    {v.is_current && <Badge tone="green">current</Badge>}
                    <span className="text-xs text-slate-500 dark:text-slate-400">{fmtDate(v.upload_date)}</span>
                  </div>
                  {!v.is_current && (
                    <Button
                      variant="secondary"
                      onClick={() => onRollback(v.version_number)}
                      disabled={rollingBack !== null}
                    >
                      {rollingBack === v.version_number ? "Rolling back…" : "Rollback"}
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}
