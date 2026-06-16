import { useEffect, useState } from "react";

import { useToast } from "../context/ToastContext";
import { MaterialsApi } from "../lib/api";
import { fmtDate } from "../lib/format";
import type { MaterialOut } from "../lib/types";
import { Badge, Button, Card, Spinner } from "./ui";

export function MaterialsCard({ jobId }: { jobId: string }) {
  const toast = useToast();
  const [material, setMaterial] = useState<MaterialOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [coverLetter, setCoverLetter] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const m = await MaterialsApi.get(jobId);
        if (active) setMaterial(m);
      } catch {
        if (active) setMaterial(null); // 404 = not generated yet
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [jobId]);

  const generate = async () => {
    setBusy(true);
    try {
      setMaterial(await MaterialsApi.generate(jobId, coverLetter));
      toast.success("Materials generated");
    } catch (err: any) {
      toast.error(err?.response?.status === 400 ? "Set your profile first (Settings)" : "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  const download = async (fmt: string) => {
    try {
      await MaterialsApi.download(jobId, fmt);
    } catch {
      toast.error(`Download (${fmt}) failed`);
    }
  };

  return (
    <Card className="lg:col-span-2">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Application materials</h2>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-300">
            <input type="checkbox" checked={coverLetter} onChange={(e) => setCoverLetter(e.target.checked)} className="h-4 w-4 rounded" />
            Cover letter
          </label>
          <Button onClick={generate} disabled={busy}>
            {busy ? "Generating…" : material ? "Regenerate" : "Generate"}
          </Button>
        </div>
      </div>

      {loading ? (
        <Spinner />
      ) : !material ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No materials yet. Generate a deterministic, truthful application packet from your profile and the
          selected resume.
        </p>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
            <span>Resume: <strong>{material.resume_category || "—"}</strong></span>
            <span>· Generated {fmtDate(material.generated_at)}</span>
            <span className="ml-auto flex gap-2">
              {material.formats.map((f) => (
                <Button key={f} variant="secondary" onClick={() => download(f)}>
                  {f.toUpperCase()}
                </Button>
              ))}
            </span>
          </div>

          {material.cover_letter_text && (
            <Preview title="Cover letter" body={material.cover_letter_text} />
          )}
          {material.resume_summary_text && (
            <Preview title="Resume summary" body={material.resume_summary_text} />
          )}

          {material.application_answers.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Application answers
              </p>
              <ul className="space-y-2">
                {material.application_answers.map((a, i) => (
                  <li key={i} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
                    <p className="font-medium">{a.question}</p>
                    <p className="text-slate-600 dark:text-slate-300">{a.answer}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-xs italic text-slate-400">
            Generated from verified profile data only — no skills, experience, or projects are invented.
          </p>
        </div>
      )}
    </Card>
  );
}

function Preview({ title, body }: { title: string; body: string }) {
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{title}</p>
        <Badge tone="indigo">template</Badge>
      </div>
      <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-slate-700 dark:bg-slate-800/60 dark:text-slate-200">
        {body}
      </pre>
    </div>
  );
}
