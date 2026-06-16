import { useEffect, useState } from "react";

import { useToast } from "../context/ToastContext";
import { SettingsApi } from "../lib/api";
import type { TelegramSettings } from "../lib/types";
import { Badge, Button, Card, Field, Input, Spinner } from "./ui";

const PREFS: { key: keyof TelegramSettings; label: string }[] = [
  { key: "pref_high_match", label: "High match jobs (90+)" },
  { key: "pref_daily", label: "Daily summary (09:00 IST)" },
  { key: "pref_evening", label: "Evening summary (18:00 IST)" },
  { key: "pref_pipeline_failure", label: "Pipeline failures" },
  { key: "pref_sheets_failure", label: "Google Sheets failures" },
  { key: "pref_security", label: "Security alerts" },
];

export function TelegramCard() {
  const toast = useToast();
  const [s, setS] = useState<TelegramSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setS(await SettingsApi.telegram());
      } catch {
        /* non-fatal */
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const set = <K extends keyof TelegramSettings>(key: K, value: TelegramSettings[K]) =>
    setS((prev) => (prev ? { ...prev, [key]: value } : prev));

  const save = async () => {
    if (!s) return;
    setSaving(true);
    try {
      setS(await SettingsApi.updateTelegram(s));
      toast.success("Telegram settings saved");
    } catch {
      toast.error("Failed to save Telegram settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Telegram notifications</h2>
        {s && <Badge tone={s.configured ? "green" : "slate"}>{s.configured ? "bot token set" : "no bot token"}</Badge>}
      </div>

      {loading ? (
        <Spinner />
      ) : !s ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Settings unavailable.</p>
      ) : (
        <div className="space-y-4">
          {!s.configured && (
            <p className="text-sm text-amber-600 dark:text-amber-400">
              Set <code>TELEGRAM_BOT_TOKEN</code> in the environment to enable sending.
            </p>
          )}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={s.enabled}
              onChange={(e) => set("enabled", e.target.checked)}
              className="h-4 w-4 rounded"
            />
            <span className="text-slate-700 dark:text-slate-300">Enable Telegram notifications</span>
          </label>

          <Field label="Chat ID">
            <Input
              value={s.chat_id ?? ""}
              onChange={(e) => set("chat_id", e.target.value)}
              placeholder="e.g. 123456789 (falls back to TELEGRAM_CHAT_ID env)"
            />
          </Field>

          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Notification preferences
            </p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {PREFS.map(({ key, label }) => (
                <label key={key} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={Boolean(s[key])}
                    onChange={(e) => set(key, e.target.checked as never)}
                    className="h-4 w-4 rounded"
                  />
                  <span className="text-slate-700 dark:text-slate-300">{label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-end">
            <Button onClick={save} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
