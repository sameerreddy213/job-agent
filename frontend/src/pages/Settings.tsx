import { FormEvent, ReactNode, useEffect, useState } from "react";

import { TelegramCard } from "../components/TelegramCard";
import { Badge, Button, Card, EmptyState, Field, Input, PageHeader, Select, Spinner } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { ProfileApi, SettingsApi } from "../lib/api";
import { fmtDate } from "../lib/format";
import type { CompanyBlacklistOut, KeywordBlacklistOut, ProfileOut, SettingsOut } from "../lib/types";

type ProfileForm = {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  notice_period: string;
  experience_level: string;
  work_auth: string;
  relocation: boolean;
  expected_ctc: string;
  linkedin_url: string;
  github_url: string;
  portfolio_url: string;
};

const EMPTY_PROFILE: ProfileForm = {
  full_name: "",
  email: "",
  phone: "",
  location: "",
  notice_period: "",
  experience_level: "",
  work_auth: "",
  relocation: false,
  expected_ctc: "",
  linkedin_url: "",
  github_url: "",
  portfolio_url: "",
};

function toForm(p: ProfileOut): ProfileForm {
  return {
    full_name: p.full_name ?? "",
    email: p.email ?? "",
    phone: p.phone ?? "",
    location: p.location ?? "",
    notice_period: p.notice_period ?? "",
    experience_level: p.experience_level ?? "",
    work_auth: p.work_auth ?? "",
    relocation: p.relocation ?? false,
    expected_ctc: p.expected_ctc ?? "",
    linkedin_url: p.linkedin_url ?? "",
    github_url: p.github_url ?? "",
    portfolio_url: p.portfolio_url ?? "",
  };
}

const APPLIES_TO_OPTIONS = ["both", "title", "description"] as const;

export function Settings() {
  const toast = useToast();

  const [settings, setSettings] = useState<SettingsOut | null>(null);
  const [profile, setProfile] = useState<ProfileForm>(EMPTY_PROFILE);
  const [companies, setCompanies] = useState<CompanyBlacklistOut[]>([]);
  const [keywords, setKeywords] = useState<KeywordBlacklistOut[]>([]);

  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);

  // Blacklist add-row state
  const [companyInput, setCompanyInput] = useState("");
  const [companyReason, setCompanyReason] = useState("");
  const [addingCompany, setAddingCompany] = useState(false);

  const [keywordInput, setKeywordInput] = useState("");
  const [keywordReason, setKeywordReason] = useState("");
  const [keywordApplies, setKeywordApplies] = useState<string>("both");
  const [addingKeyword, setAddingKeyword] = useState(false);

  const loadProfile = async () => {
    try {
      const p = await ProfileApi.get();
      setProfile(toForm(p));
    } catch (err: any) {
      // 404 -> no profile yet; treat as an empty editable form.
      if (err?.response?.status === 404) {
        setProfile(EMPTY_PROFILE);
      } else {
        toast.error("Failed to load profile");
      }
    }
  };

  const loadCompanies = async () => {
    setCompanies(await SettingsApi.companies());
  };

  const loadKeywords = async () => {
    setKeywords(await SettingsApi.keywords());
  };

  const load = async () => {
    setLoading(true);
    try {
      const [s] = await Promise.all([
        SettingsApi.get(),
        loadProfile(),
        loadCompanies().catch(() => setCompanies([])),
        loadKeywords().catch(() => setKeywords([])),
      ]);
      setSettings(s);
    } catch {
      toast.error("Failed to load settings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setField = <K extends keyof ProfileForm>(key: K, value: ProfileForm[K]) => {
    setProfile((p) => ({ ...p, [key]: value }));
  };

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      const payload: Partial<ProfileOut> = {
        full_name: profile.full_name,
        email: profile.email,
        phone: profile.phone,
        location: profile.location,
        notice_period: profile.notice_period || null,
        experience_level: profile.experience_level || null,
        work_auth: profile.work_auth || null,
        relocation: profile.relocation,
        expected_ctc: profile.expected_ctc || null,
        linkedin_url: profile.linkedin_url || null,
        github_url: profile.github_url || null,
        portfolio_url: profile.portfolio_url || null,
      };
      const updated = await ProfileApi.update(payload);
      setProfile(toForm(updated));
      toast.success("Profile saved");
    } catch {
      toast.error("Failed to save profile");
    } finally {
      setSavingProfile(false);
    }
  };

  const addCompany = async (e: FormEvent) => {
    e.preventDefault();
    const company = companyInput.trim();
    if (!company) return;
    setAddingCompany(true);
    try {
      await SettingsApi.addCompany(company, companyReason.trim() || undefined);
      setCompanyInput("");
      setCompanyReason("");
      await loadCompanies();
      toast.success("Company blacklisted");
    } catch (err: any) {
      if (err?.response?.status === 409) {
        toast.error("Already blacklisted");
      } else {
        toast.error("Failed to add company");
      }
    } finally {
      setAddingCompany(false);
    }
  };

  const removeCompany = async (id: string) => {
    try {
      await SettingsApi.removeCompany(id);
      await loadCompanies();
      toast.success("Removed from blacklist");
    } catch {
      toast.error("Failed to remove company");
    }
  };

  const addKeyword = async (e: FormEvent) => {
    e.preventDefault();
    const keyword = keywordInput.trim();
    if (!keyword) return;
    setAddingKeyword(true);
    try {
      await SettingsApi.addKeyword(keyword, keywordApplies, keywordReason.trim() || undefined);
      setKeywordInput("");
      setKeywordReason("");
      setKeywordApplies("both");
      await loadKeywords();
      toast.success("Keyword blacklisted");
    } catch (err: any) {
      if (err?.response?.status === 409) {
        toast.error("Already blacklisted");
      } else {
        toast.error("Failed to add keyword");
      }
    } finally {
      setAddingKeyword(false);
    }
  };

  const removeKeyword = async (id: string) => {
    try {
      await SettingsApi.removeKeyword(id);
      await loadKeywords();
      toast.success("Removed from blacklist");
    } catch {
      toast.error("Failed to remove keyword");
    }
  };

  if (loading) return <Spinner />;

  return (
    <div>
      <PageHeader title="Settings" subtitle="Configuration, applicant profile, and blacklist management" />

      <div className="space-y-6">
        {/* 1) Configuration (read-only) */}
        <Card>
          <h2 className="mb-3 text-lg font-semibold">Configuration</h2>
          {!settings ? (
            <EmptyState title="No configuration" hint="Settings could not be loaded." />
          ) : (
            <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <ConfigItem label="Scan interval">{settings.scan_interval_minutes} min</ConfigItem>
              <ConfigItem label="Test mode">
                <Badge tone={settings.test_mode ? "amber" : "slate"}>{settings.test_mode ? "ON" : "OFF"}</Badge>
              </ConfigItem>
              <ConfigItem label="Data retention">{settings.data_retention_days} days</ConfigItem>
              <ConfigItem label="Weight · Freshers">{settings.scoring_weights.freshers}</ConfigItem>
              <ConfigItem label="Weight · Skills">{settings.scoring_weights.skills}</ConfigItem>
              <ConfigItem label="Weight · Location">{settings.scoring_weights.location}</ConfigItem>
              <ConfigItem label="Weight · Role">{settings.scoring_weights.role}</ConfigItem>
              <ConfigItem label="Threshold · Auto approve">{settings.thresholds.auto_approve}</ConfigItem>
              <ConfigItem label="Threshold · Review">{settings.thresholds.review}</ConfigItem>
            </dl>
          )}
        </Card>

        {/* 2) Profile */}
        <Card>
          <h2 className="mb-3 text-lg font-semibold">Profile</h2>
          <form onSubmit={saveProfile} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Full name">
                <Input value={profile.full_name} onChange={(e) => setField("full_name", e.target.value)} />
              </Field>
              <Field label="Email">
                <Input
                  type="email"
                  value={profile.email}
                  onChange={(e) => setField("email", e.target.value)}
                  autoComplete="email"
                />
              </Field>
              <Field label="Phone">
                <Input value={profile.phone} onChange={(e) => setField("phone", e.target.value)} />
              </Field>
              <Field label="Location">
                <Input value={profile.location} onChange={(e) => setField("location", e.target.value)} />
              </Field>
              <Field label="Notice period">
                <Input value={profile.notice_period} onChange={(e) => setField("notice_period", e.target.value)} />
              </Field>
              <Field label="Experience level">
                <Input
                  value={profile.experience_level}
                  onChange={(e) => setField("experience_level", e.target.value)}
                />
              </Field>
              <Field label="Work authorization">
                <Input value={profile.work_auth} onChange={(e) => setField("work_auth", e.target.value)} />
              </Field>
              <Field label="Expected CTC">
                <Input value={profile.expected_ctc} onChange={(e) => setField("expected_ctc", e.target.value)} />
              </Field>
              <Field label="LinkedIn URL">
                <Input value={profile.linkedin_url} onChange={(e) => setField("linkedin_url", e.target.value)} />
              </Field>
              <Field label="GitHub URL">
                <Input value={profile.github_url} onChange={(e) => setField("github_url", e.target.value)} />
              </Field>
              <Field label="Portfolio URL">
                <Input value={profile.portfolio_url} onChange={(e) => setField("portfolio_url", e.target.value)} />
              </Field>
            </div>

            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={profile.relocation}
                onChange={(e) => setField("relocation", e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800"
              />
              <span className="text-slate-700 dark:text-slate-300">Open to relocation</span>
            </label>

            <div className="flex justify-end">
              <Button type="submit" disabled={savingProfile}>
                {savingProfile ? "Saving…" : "Save profile"}
              </Button>
            </div>
          </form>
        </Card>

        {/* 3) Blacklist management */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold">Blacklist management</h2>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Companies */}
            <div>
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Companies
              </h3>

              <form onSubmit={addCompany} className="mb-3 flex flex-col gap-2 sm:flex-row">
                <Input
                  placeholder="Company name"
                  value={companyInput}
                  onChange={(e) => setCompanyInput(e.target.value)}
                />
                <Input
                  placeholder="Reason (optional)"
                  value={companyReason}
                  onChange={(e) => setCompanyReason(e.target.value)}
                />
                <Button type="submit" disabled={addingCompany || !companyInput.trim()} className="sm:shrink-0">
                  {addingCompany ? "Adding…" : "Add"}
                </Button>
              </form>

              {companies.length === 0 ? (
                <EmptyState title="No companies blacklisted" />
              ) : (
                <ul className="space-y-2">
                  {companies.map((c) => (
                    <li
                      key={c.id}
                      className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-800 dark:bg-slate-900"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{c.company}</p>
                        {c.reason && (
                          <p className="truncate text-xs text-slate-500 dark:text-slate-400">{c.reason}</p>
                        )}
                        <p className="text-xs text-slate-400 dark:text-slate-500">{fmtDate(c.created_at)}</p>
                      </div>
                      <Button variant="danger" onClick={() => removeCompany(c.id)} className="shrink-0">
                        Remove
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Keywords */}
            <div>
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Keywords
              </h3>

              <form onSubmit={addKeyword} className="mb-3 flex flex-col gap-2">
                <Input
                  placeholder="Keyword"
                  value={keywordInput}
                  onChange={(e) => setKeywordInput(e.target.value)}
                />
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Select value={keywordApplies} onChange={(e) => setKeywordApplies(e.target.value)}>
                    {APPLIES_TO_OPTIONS.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </Select>
                  <Input
                    placeholder="Reason (optional)"
                    value={keywordReason}
                    onChange={(e) => setKeywordReason(e.target.value)}
                  />
                  <Button type="submit" disabled={addingKeyword || !keywordInput.trim()} className="sm:shrink-0">
                    {addingKeyword ? "Adding…" : "Add"}
                  </Button>
                </div>
              </form>

              {keywords.length === 0 ? (
                <EmptyState title="No keywords blacklisted" />
              ) : (
                <ul className="space-y-2">
                  {keywords.map((k) => (
                    <li
                      key={k.id}
                      className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-800 dark:bg-slate-900"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="truncate text-sm font-medium">{k.keyword}</p>
                          <Badge tone="indigo">{k.applies_to}</Badge>
                        </div>
                        {k.reason && (
                          <p className="truncate text-xs text-slate-500 dark:text-slate-400">{k.reason}</p>
                        )}
                        <p className="text-xs text-slate-400 dark:text-slate-500">{fmtDate(k.created_at)}</p>
                      </div>
                      <Button variant="danger" onClick={() => removeKeyword(k.id)} className="shrink-0">
                        Remove
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </Card>

        <TelegramCard />
      </div>
    </div>
  );
}

function ConfigItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="mt-1 text-sm font-semibold">{children}</dd>
    </div>
  );
}
