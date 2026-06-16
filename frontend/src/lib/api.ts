// Central API client. baseURL is /api on the same origin (nginx proxies to the
// backend; Vite dev server proxies /api -> localhost:8000).
//
// Auth: access + refresh tokens in localStorage. A 401 triggers a single
// refresh attempt (rotating the refresh token); on failure the user is logged
// out via a window event the AuthContext listens for.
import axios, {
  AxiosError,
  AxiosRequestConfig,
  InternalAxiosRequestConfig,
} from "axios";

import type {
  AnalyticsOverview,
  ApplicationAnalytics,
  ApplicationDetailOut,
  ApplicationEventOut,
  ApplicationOut,
  ApprovalStats,
  AtsBreakdown,
  ChecklistOut,
  PacketOut,
  ReadinessItem,
  ReadinessReport,
  AuditOut,
  CompanyBlacklistOut,
  DashboardSummary,
  BulkResult,
  JobDetailOut,
  JobOut,
  JobStateHistory,
  TimelineEvent,
  WorkflowAnalytics,
  KeywordBlacklistOut,
  MaterialOut,
  ProfileOut,
  QueueCounts,
  ResumeDetailOut,
  ResumeOut,
  ResumeSummaryOut,
  RunHealthOut,
  SettingsOut,
  SourceOut,
  SyncStatus,
  TelegramSettings,
  TokenPair,
  User,
} from "./types";

const ACCESS_KEY = "ja_access";
const REFRESH_KEY = "ja_refresh";
export const LOGOUT_EVENT = "ja:logout";

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(tokens: TokenPair) {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.access;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  const refresh = tokenStore.refresh;
  if (!refresh) return null;
  try {
    const { data } = await axios.post<TokenPair>("/api/auth/refresh", {
      refresh_token: refresh,
    });
    tokenStore.set(data);
    return data.access_token;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as (AxiosRequestConfig & { _retried?: boolean }) | undefined;
    const status = error.response?.status;
    const isAuthCall = original?.url?.includes("/auth/");

    if (status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true;
      refreshing = refreshing ?? doRefresh();
      const newToken = await refreshing;
      refreshing = null;
      if (newToken) {
        original.headers = { ...original.headers, Authorization: `Bearer ${newToken}` };
        return api(original);
      }
      tokenStore.clear();
      window.dispatchEvent(new Event(LOGOUT_EVENT));
    }
    return Promise.reject(error);
  },
);

// --------------------------------------------------------------------------- //
// Typed endpoint helpers
// --------------------------------------------------------------------------- //
export const AuthApi = {
  async login(username: string, password: string): Promise<TokenPair> {
    const body = new URLSearchParams({ username, password });
    const { data } = await api.post<TokenPair>("/auth/login", body, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    tokenStore.set(data);
    return data;
  },
  async me(): Promise<User> {
    return (await api.get<User>("/auth/me")).data;
  },
  async logout(): Promise<void> {
    const refresh = tokenStore.refresh;
    if (refresh) {
      try {
        await api.post("/auth/logout", { refresh_token: refresh });
      } catch {
        /* ignore */
      }
    }
    tokenStore.clear();
  },
};

export const DashboardApi = {
  async summary(): Promise<DashboardSummary> {
    return (await api.get<DashboardSummary>("/dashboard/summary")).data;
  },
};

export const JobsApi = {
  async list(params: Record<string, unknown> = {}): Promise<JobOut[]> {
    return (await api.get<JobOut[]>("/jobs", { params })).data;
  },
  async get(id: string): Promise<JobDetailOut> {
    return (await api.get<JobDetailOut>(`/jobs/${id}`)).data;
  },
  async setResume(id: string, category: string): Promise<JobDetailOut> {
    return (await api.post<JobDetailOut>(`/jobs/${id}/resume`, { category })).data;
  },
  async rematch(id: string): Promise<JobDetailOut> {
    return (await api.post<JobDetailOut>(`/jobs/${id}/rematch`)).data;
  },
  // --- Workflow actions (Phase 7A) ---
  async approve(id: string): Promise<JobDetailOut> {
    return (await api.post<JobDetailOut>(`/jobs/${id}/approve`)).data;
  },
  async reject(id: string, reason?: string): Promise<JobDetailOut> {
    return (await api.post<JobDetailOut>(`/jobs/${id}/reject`, { reason })).data;
  },
  async archive(id: string, reason?: string): Promise<JobDetailOut> {
    return (await api.post<JobDetailOut>(`/jobs/${id}/archive`, { reason })).data;
  },
  async snooze(id: string, hours = 24): Promise<JobDetailOut> {
    return (await api.post<JobDetailOut>(`/jobs/${id}/snooze`, { hours })).data;
  },
  async history(id: string): Promise<JobStateHistory[]> {
    return (await api.get<JobStateHistory[]>(`/jobs/${id}/workflow/history`)).data;
  },
  async bulkApprove(ids: string[]): Promise<BulkResult> {
    return (await api.post<BulkResult>("/jobs/bulk/approve", { ids })).data;
  },
  async bulkReject(ids: string[]): Promise<BulkResult> {
    return (await api.post<BulkResult>("/jobs/bulk/reject", { ids })).data;
  },
  async bulkArchive(ids: string[]): Promise<BulkResult> {
    return (await api.post<BulkResult>("/jobs/bulk/archive", { ids })).data;
  },
};

export const QueueApi = {
  async list(params: Record<string, unknown> = {}): Promise<JobOut[]> {
    return (await api.get<JobOut[]>("/queue", { params })).data;
  },
  async counts(): Promise<QueueCounts> {
    return (await api.get<QueueCounts>("/queue/counts")).data;
  },
};

export const AnalyticsApi = {
  async overview(days = 30, topN = 10): Promise<AnalyticsOverview> {
    return (await api.get<AnalyticsOverview>("/analytics/overview", { params: { days, top_n: topN } })).data;
  },
};

export const WorkflowApi = {
  async stateCounts(): Promise<Record<string, number>> {
    return (await api.get<Record<string, number>>("/workflow/state-counts")).data;
  },
  async timeline(params: { job_id?: string; limit?: number } = {}): Promise<TimelineEvent[]> {
    return (await api.get<TimelineEvent[]>("/workflow/timeline", { params })).data;
  },
  async analytics(days = 30): Promise<WorkflowAnalytics> {
    return (await api.get<WorkflowAnalytics>("/workflow/analytics", { params: { days } })).data;
  },
  async approvalStats(days = 30): Promise<ApprovalStats> {
    return (await api.get<ApprovalStats>("/workflow/approval-stats", { params: { days } })).data;
  },
};

export const ApplicationsApi = {
  async list(params: Record<string, unknown> = {}): Promise<ApplicationOut[]> {
    return (await api.get<ApplicationOut[]>("/applications", { params })).data;
  },
  async get(id: string): Promise<ApplicationDetailOut> {
    return (await api.get<ApplicationDetailOut>(`/applications/${id}`)).data;
  },
  async create(jobId: string): Promise<ApplicationDetailOut> {
    return (await api.post<ApplicationDetailOut>("/applications", { job_id: jobId })).data;
  },
  async update(id: string, patch: { notes?: string; resume_category?: string }): Promise<ApplicationDetailOut> {
    return (await api.patch<ApplicationDetailOut>(`/applications/${id}`, patch)).data;
  },
  async remove(id: string): Promise<void> {
    await api.delete(`/applications/${id}`);
  },
  async transition(id: string, newState: string, reason?: string): Promise<ApplicationDetailOut> {
    return (await api.post<ApplicationDetailOut>(`/applications/${id}/transition`, { new_state: newState, reason })).data;
  },
  async timeline(id: string): Promise<ApplicationEventOut[]> {
    return (await api.get<ApplicationEventOut[]>(`/applications/${id}/timeline`)).data;
  },
  async analytics(): Promise<ApplicationAnalytics> {
    return (await api.get<ApplicationAnalytics>("/applications/analytics")).data;
  },
  // ATS integration layer (Phase 8B)
  async readiness(readyOnly = false): Promise<ReadinessItem[]> {
    return (await api.get<ReadinessItem[]>("/applications/readiness", { params: { ready_only: readyOnly } })).data;
  },
  async readyQueue(): Promise<ReadinessItem[]> {
    return (await api.get<ReadinessItem[]>("/applications/ready-queue")).data;
  },
  async atsBreakdown(): Promise<AtsBreakdown> {
    return (await api.get<AtsBreakdown>("/applications/ats-breakdown")).data;
  },
  async appReadiness(id: string): Promise<ReadinessReport> {
    return (await api.get<ReadinessReport>(`/applications/${id}/readiness`)).data;
  },
  async detectAts(id: string): Promise<ApplicationDetailOut> {
    return (await api.post<ApplicationDetailOut>(`/applications/${id}/detect-ats`)).data;
  },
  // Manual apply assistant (Phase 8C)
  async checklist(id: string): Promise<ChecklistOut> {
    return (await api.get<ChecklistOut>(`/applications/${id}/checklist`)).data;
  },
  async confirmReady(id: string): Promise<ApplicationDetailOut> {
    return (await api.post<ApplicationDetailOut>(`/applications/${id}/confirm-ready`)).data;
  },
  async packetStatus(id: string): Promise<PacketOut> {
    return (await api.get<PacketOut>(`/applications/${id}/packet`)).data;
  },
  async generatePacket(id: string): Promise<PacketOut> {
    return (await api.post<PacketOut>(`/applications/${id}/packet`)).data;
  },
  async downloadPacket(id: string, fmt: string): Promise<void> {
    const res = await api.get(`/applications/${id}/packet/download/${fmt}`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data as Blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `application-packet.${fmt}`;
    a.click();
    URL.revokeObjectURL(url);
  },
};

export const SourcesApi = {
  async list(): Promise<SourceOut[]> {
    return (await api.get<SourceOut[]>("/sources")).data;
  },
  async update(id: number, patch: Partial<Pick<SourceOut, "enabled" | "apply_policy" | "config">>): Promise<SourceOut> {
    return (await api.patch<SourceOut>(`/sources/${id}`, patch)).data;
  },
  async health(): Promise<RunHealthOut[]> {
    return (await api.get<RunHealthOut[]>("/health/sources")).data;
  },
};

export const SettingsApi = {
  async get(): Promise<SettingsOut> {
    return (await api.get<SettingsOut>("/settings")).data;
  },
  async companies(): Promise<CompanyBlacklistOut[]> {
    return (await api.get<CompanyBlacklistOut[]>("/settings/blacklist/companies")).data;
  },
  async addCompany(company: string, reason?: string): Promise<CompanyBlacklistOut> {
    return (await api.post<CompanyBlacklistOut>("/settings/blacklist/companies", { company, reason })).data;
  },
  async removeCompany(id: string): Promise<void> {
    await api.delete(`/settings/blacklist/companies/${id}`);
  },
  async keywords(): Promise<KeywordBlacklistOut[]> {
    return (await api.get<KeywordBlacklistOut[]>("/settings/blacklist/keywords")).data;
  },
  async addKeyword(keyword: string, applies_to: string, reason?: string): Promise<KeywordBlacklistOut> {
    return (await api.post<KeywordBlacklistOut>("/settings/blacklist/keywords", { keyword, applies_to, reason })).data;
  },
  async removeKeyword(id: string): Promise<void> {
    await api.delete(`/settings/blacklist/keywords/${id}`);
  },
  async telegram(): Promise<TelegramSettings> {
    return (await api.get<TelegramSettings>("/settings/telegram")).data;
  },
  async updateTelegram(patch: Partial<TelegramSettings>): Promise<TelegramSettings> {
    return (await api.put<TelegramSettings>("/settings/telegram", patch)).data;
  },
};

export const ProfileApi = {
  async get(): Promise<ProfileOut> {
    return (await api.get<ProfileOut>("/profile")).data;
  },
  async update(payload: Partial<ProfileOut>): Promise<ProfileOut> {
    return (await api.put<ProfileOut>("/profile", payload)).data;
  },
};

export const ResumesApi = {
  async summary(): Promise<ResumeSummaryOut[]> {
    return (await api.get<ResumeSummaryOut[]>("/resumes/summary")).data;
  },
  async list(): Promise<ResumeOut[]> {
    return (await api.get<ResumeOut[]>("/resumes")).data;
  },
  async versions(category: string): Promise<ResumeDetailOut> {
    return (await api.get<ResumeDetailOut>(`/resumes/${category}/versions`)).data;
  },
  async upload(category: string, file: File): Promise<ResumeDetailOut> {
    const form = new FormData();
    form.append("file", file);
    return (await api.post<ResumeDetailOut>(`/resumes/${category}/versions`, form)).data;
  },
  async rollback(category: string, version: number): Promise<ResumeDetailOut> {
    return (await api.post<ResumeDetailOut>(`/resumes/${category}/rollback/${version}`)).data;
  },
};

export const MaterialsApi = {
  async get(jobId: string): Promise<MaterialOut> {
    return (await api.get<MaterialOut>(`/jobs/${jobId}/materials`)).data;
  },
  async generate(jobId: string, coverLetter = true, category?: string): Promise<MaterialOut> {
    const params: Record<string, unknown> = { cover_letter: coverLetter };
    if (category) params.category = category;
    return (await api.post<MaterialOut>(`/jobs/${jobId}/materials/generate`, null, { params })).data;
  },
  // Download via the browser so the auth header is attached and the file saves.
  async download(jobId: string, fmt: string): Promise<void> {
    const res = await api.get(`/jobs/${jobId}/materials/download/${fmt}`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data as Blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `application-packet.${fmt}`;
    a.click();
    URL.revokeObjectURL(url);
  },
};

export const AdminApi = {
  async runNow(): Promise<Record<string, unknown>> {
    return (await api.post("/admin/run-now")).data;
  },
  async syncSheets(): Promise<Record<string, unknown>> {
    return (await api.post("/admin/sync-sheets")).data;
  },
  async syncStatus(): Promise<SyncStatus> {
    return (await api.get<SyncStatus>("/admin/sync-sheets/status")).data;
  },
};

export const AuditApi = {
  async list(params: Record<string, unknown> = {}): Promise<AuditOut[]> {
    return (await api.get<AuditOut[]>("/audit", { params })).data;
  },
};
