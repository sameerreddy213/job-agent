// TypeScript mirrors of the backend Pydantic schemas. Keep in sync with
// docs/API_SPEC.md. These are the ONLY shapes the UI relies on.

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: string;
  username: string;
  role: string;
  created_at: string;
}

export interface ScoreOut {
  freshers_score: number;
  skills_score: number;
  location_score: number;
  role_score: number;
  total_score: number;
  classification: string; // AUTO_APPROVE_ELIGIBLE | REVIEW_QUEUE | REJECT
  matched_resume_category: string | null;
  reasoning: string | null;
  passed_filters: boolean;
  // Resume intelligence (Phase 5A)
  resume_match_score: number;
  resume_confidence: number;
  matched_skills: string[];
  missing_skills: string[];
  resume_reasoning: string | null;
  resume_override: boolean;
}

export const RESUME_CATEGORIES = [
  "SDE", "SDE_1", "Software_Engineer", "Associate_Software_Engineer",
  "Graduate_Engineer_Trainee", "Frontend", "Backend_Developer", "Full_Stack",
  "MERN_Stack", "React_Developer", "Node_js_Developer", "Java_Developer",
  "AI_Data_Platform_Engineer",
] as const;

export interface JobOut {
  id: string;
  source: string;
  external_id: string | null;
  fingerprint: string;
  company: string;
  title: string;
  location: string | null;
  experience: string | null;
  apply_url: string | null;
  posted_date: string | null;
  employment_type: string | null;
  remote_status: string | null;
  status: string;
  discovered_at: string;
  archived: boolean;
  score: ScoreOut | null;
}

export interface JobDetailOut extends JobOut {
  description: string | null;
}

export interface RunHealthOut {
  source: string;
  run_at: string;
  jobs_found: number;
  new_jobs: number;
  errors: number;
  response_time_ms: number;
  status: string; // HEALTHY | WARNING | FAILED
  detail: string | null;
}

export interface DashboardSummary {
  total_jobs: number;
  new_today: number;
  auto_eligible: number;
  review_queue: number;
  rejected: number;
  archived: number;
  last_run: string | null;
  sources: RunHealthOut[];
}

export interface CountPoint {
  label: string;
  count: number;
}
export interface DayPoint {
  day: string;
  count: number;
}
export interface ResumeStat {
  category: string;
  matched_jobs: number;
  applied: number;
  interviews: number;
  success_rate: number;
}
export interface AnalyticsOverview {
  jobs_per_day: DayPoint[];
  applications_per_day: DayPoint[];
  top_companies: CountPoint[];
  top_locations: CountPoint[];
  top_skills: CountPoint[];
  resume_stats: ResumeStat[];
  interview_conversion_rate: number;
  note: string | null;
}

export interface SourceOut {
  id: number;
  name: string;
  kind: string;
  apply_policy: string;
  enabled: boolean;
  config: Record<string, unknown>;
  last_run: string | null;
  last_status: string | null;
  last_error: string | null;
}

export interface ProfileOut {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  location: string;
  notice_period: string | null;
  experience_level: string | null;
  work_auth: string | null;
  relocation: boolean;
  expected_ctc: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  // Extended profile (Phase 8D)
  first_name: string | null;
  middle_name: string | null;
  last_name: string | null;
  college_email: string | null;
  date_of_birth: string | null;
  gender: string | null;
  nationality: string | null;
  address_line: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  preferred_locations: string | null;
  qualification: string | null;
  college_name: string | null;
  degree: string | null;
  branch: string | null;
  joined_date: string | null;
  graduation_date: string | null;
  graduation_year: string | null;
  cgpa: string | null;
  class12_board: string | null;
  class12_stream: string | null;
  class12_school: string | null;
  class12_percentage: string | null;
  class12_year: string | null;
  class10_board: string | null;
  class10_school: string | null;
  class10_percentage: string | null;
  class10_year: string | null;
  languages: string | null;
  current_ctc: string | null;
  shift_preference: string | null;
  updated_at: string;
}

export interface ResumeVersionOut {
  id: string;
  version_number: number;
  file_path: string;
  skills_detected: string[];
  role_category: string;
  upload_date: string;
  is_current: boolean;
}
export interface ResumeOut {
  id: string;
  category: string;
  is_active: boolean;
  created_at: string;
  current_version: ResumeVersionOut | null;
}
export interface ResumeDetailOut extends ResumeOut {
  versions: ResumeVersionOut[];
}
export interface ResumeSummaryOut {
  category: string;
  current_version: ResumeVersionOut | null;
  previous_versions: number;
  last_updated: string | null;
}

export interface AuditOut {
  id: string;
  actor: string;
  action: string;
  entity: string | null;
  entity_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface SettingsOut {
  scan_interval_minutes: number;
  test_mode: boolean;
  data_retention_days: number;
  scoring_weights: { freshers: number; skills: number; location: number; role: number };
  thresholds: { auto_approve: number; review: number };
}

export interface CompanyBlacklistOut {
  id: string;
  company: string;
  reason: string | null;
  created_at: string;
}
export interface KeywordBlacklistOut {
  id: string;
  keyword: string;
  applies_to: string;
  reason: string | null;
  created_at: string;
}

export interface QueueCounts {
  auto_eligible: number;
  review_queue: number;
}

export interface JobStateHistory {
  id: string;
  previous_state: string | null;
  new_state: string;
  actor: string;
  reason: string | null;
  created_at: string;
}

export interface TimelineEvent {
  id: string;
  job_id: string;
  company: string | null;
  title: string | null;
  previous_state: string | null;
  new_state: string;
  actor: string;
  reason: string | null;
  created_at: string;
}

export interface StatePoint {
  state: string;
  count: number;
}
export interface DayCount {
  day: string;
  count: number;
}

export interface WorkflowAnalytics {
  days: number;
  jobs_by_state: StatePoint[];
  total_transitions: number;
  approvals: number;
  rejections: number;
  snoozes: number;
  archives: number;
  decisions: number;
  approval_pct: number;
  rejection_pct: number;
  snooze_pct: number;
  avg_review_seconds: number | null;
  pending_review_trend: DayCount[];
}

export interface ApprovalStats {
  days: number;
  approved: number;
  rejected: number;
  archived: number;
  snoozed: number;
  approval_rate: number;
  rejection_rate: number;
  approved_per_day: DayCount[];
  rejected_per_day: DayCount[];
}

export interface BulkResult {
  requested: number;
  succeeded: number;
  failed: number;
  results: { id: string; ok: boolean; error?: string }[];
}

export interface TelegramSettings {
  enabled: boolean;
  chat_id: string | null;
  pref_high_match: boolean;
  pref_daily: boolean;
  pref_evening: boolean;
  pref_pipeline_failure: boolean;
  pref_sheets_failure: boolean;
  pref_security: boolean;
  configured: boolean;
}

export interface SyncStatus {
  configured: boolean;
  enabled: boolean;
  interval_minutes: number;
  last_sync_at: string | null;
  last_status: string | null;
  rows_written: number;
  duration_ms: number;
  error: string | null;
  tabs: Record<string, number>;
}

export interface AnswerItem {
  question: string;
  answer: string;
}

export interface MaterialOut {
  id: string;
  job_id: string;
  resume_category: string | null;
  cover_letter_required: boolean;
  cover_letter_text: string | null;
  resume_summary_text: string | null;
  application_answers: AnswerItem[];
  generated_at: string;
  formats: string[];
}

// --------------------------------------------------------------------------- //
// Application engine (Phase 8A)
// --------------------------------------------------------------------------- //
export const APPLICATION_STATES = [
  "NOT_STARTED", "READY", "IN_PROGRESS", "SUBMITTED", "INTERVIEW",
  "ASSESSMENT", "REJECTED", "OFFER", "ACCEPTED", "WITHDRAWN",
] as const;
export type ApplicationState = (typeof APPLICATION_STATES)[number];

// Mirror of the backend state machine, for UX (the backend still enforces it).
export const APP_TRANSITIONS: Record<ApplicationState, ApplicationState[]> = {
  NOT_STARTED: ["READY", "IN_PROGRESS", "WITHDRAWN"],
  READY: ["IN_PROGRESS", "SUBMITTED", "WITHDRAWN"],
  IN_PROGRESS: ["SUBMITTED", "WITHDRAWN"],
  SUBMITTED: ["INTERVIEW", "ASSESSMENT", "REJECTED", "OFFER", "WITHDRAWN"],
  INTERVIEW: ["ASSESSMENT", "OFFER", "REJECTED", "WITHDRAWN"],
  ASSESSMENT: ["INTERVIEW", "OFFER", "REJECTED", "WITHDRAWN"],
  OFFER: ["ACCEPTED", "REJECTED", "WITHDRAWN"],
  REJECTED: [],
  ACCEPTED: [],
  WITHDRAWN: [],
};

export interface ApplicationOut {
  id: string;
  job_id: string;
  material_id: string | null;
  status: string;
  resume_category: string | null;
  notes: string | null;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
  ats_type: string;
  ats_version: string | null;
  application_url: string | null;
  supports_easy_apply: boolean;
  requires_manual_fields: boolean;
  ready_confirmed: boolean;
  ready_confirmed_at: string | null;
  packet_generated_at: string | null;
  company: string | null;
  title: string | null;
}

export interface ChecklistItem {
  key: string;
  label: string;
  done: boolean;
  required: boolean;
}
export interface ChecklistOut {
  application_id: string;
  items: ChecklistItem[];
  complete: boolean;
  ready_confirmed: boolean;
}
export interface PacketOut {
  application_id: string;
  generated: boolean;
  generated_at: string | null;
  formats: string[];
}

export interface ReadinessReport {
  application_id: string;
  ready_score: number;
  ready: boolean;
  missing_materials: boolean;
  missing_resume: boolean;
  missing_answers: boolean;
  manual_review_required: boolean;
  reasons: string[];
}

export interface ReadinessItem extends ApplicationOut {
  ready_score: number;
  ready: boolean;
  manual_review_required: boolean;
}

export interface AtsCount {
  ats_type: string;
  count: number;
}
export interface AtsBreakdown {
  total: number;
  detected: number;
  unknown: number;
  ready_to_apply: number;
  manual_review_required: number;
  by_ats: AtsCount[];
}

export interface ApplicationDocumentOut {
  id: string;
  material_id: string | null;
  kind: string;
  fmt: string;
  path: string | null;
  created_at: string;
}
export interface ApplicationAnswerOut {
  id: string;
  question: string;
  answer: string | null;
  created_at: string;
}
export interface ApplicationEventOut {
  id: string;
  previous_state: string | null;
  new_state: string;
  actor: string;
  reason: string | null;
  created_at: string;
}
export interface ApplicationDetailOut extends ApplicationOut {
  documents: ApplicationDocumentOut[];
  answers: ApplicationAnswerOut[];
  events: ApplicationEventOut[];
}

export interface ApplicationStateCount {
  state: string;
  count: number;
}
export interface ApplicationAnalytics {
  total: number;
  by_state: ApplicationStateCount[];
  created: number;
  submitted: number;
  interviews: number;
  assessments: number;
  offers: number;
  rejections: number;
  accepted: number;
  withdrawn: number;
  submit_rate: number;
  interview_rate: number;
  offer_rate: number;
  acceptance_rate: number;
}
