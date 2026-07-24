export type EvidenceKind =
  | 'portfolio_investment'
  | 'thesis_publication'
  | 'fund_close'
  | 'portfolio_gap'
  | 'exit'
  | 'personnel'
  | 'other'

export interface EvidenceRecord {
  id: string
  kind: EvidenceKind
  claim: string
  detail: string
  event_date: string | null
  source_url: string
  source_name: string
  source_published_at: string | null
  confidence: number
  verified_at: string | null
  stale: boolean
  intent_kind: string
}

export type TargetStatus =
  | 'new'
  | 'drafted'
  | 'approved'
  | 'sent'
  | 'replied'
  | 'dismissed'
  | 'needs_review'

export interface TargetSummary {
  target_id: string
  run_id: string
  investor_firm: string
  investor_person: string | null
  role: string | null
  score: number
  status: TargetStatus
  contact_email: string | null
  firm_domain: string | null
  evidence_count: number
  has_stale_evidence: boolean
  lead_evidence: EvidenceRecord
  location: string | null
  check_min: number | null
  check_max: number | null
  stage: string[]
  sectors: string[]
  draft_id: string | null
}

export interface TargetDetail extends Omit<TargetSummary, 'evidence_count' | 'has_stale_evidence'> {
  evidence: EvidenceRecord[]
  score_breakdown: Record<string, number>
  list_underfilled: boolean
  notes: string | null
}

export interface DraftPublic {
  draft_id: string
  target_id: string
  run_id: string
  subject: string
  body: string
  word_count: number
  lead_evidence_id: string
  prior_contact: { found: boolean; last_thread_at: string | null; summary: string | null }
  blockers: string[]
  version: number
  updated_at: string
  approved_at: string | null
  approved_by: string | null
  generated_by: string
}

export interface SequenceStepView {
  n: number
  offset_days: number
  channel: 'email' | 'linkedin'
  intent: string
  preview: string
  scheduled_for: string | null
  sent_at: string | null
  status: 'pending' | 'scheduled' | 'delivered' | 'cancelled' | 'failed'
}

export interface SequenceView {
  target_id: string
  draft_id: string | null
  state: 'active' | 'stopped_reply' | 'stopped_manual' | 'complete'
  steps: SequenceStepView[]
  stop_reason: string | null
}

export type RunStage =
  | 'queued'
  | 'planning'
  | 'retrieving'
  | 'extracting'
  | 'verifying'
  | 'scoring'
  | 'complete'
  | 'failed'
  | 'cancelled'

export interface RunStatus {
  run_id: string
  profile_id: string
  status: 'queued' | 'running' | 'complete' | 'failed' | 'cancelled'
  stage: RunStage
  progress: {
    queries_total: number
    queries_done: number
    results: number
    evidence: number
    investors: number
  }
  retrieval_stats: {
    queries_issued: number
    wall_time_ms: number
    p50_latency_ms: number
    max_concurrency: number
    failed_queries: number
    cache_hits: number
    results: number
    transport: string
  }
  warnings: string[]
  started_at: string
  completed_at: string | null
  list_underfilled: boolean
  rejected_count: number
  sources_searched: number
}

export interface RunEvent {
  type:
    | 'stage_changed'
    | 'query_batch_done'
    | 'investor_found'
    | 'record_rejected'
    | 'run_complete'
    | 'run_failed'
    | 'heartbeat'
  run_id: string
  at: string
  stage: RunStage | null
  message: string | null
  data: Record<string, unknown>
}

export interface WorkspaceProfile {
  id: string
  company: string
  round: string
  raise_target: string
  one_liner: string
  founder_name: string
  sectors?: string[]
  geographies?: string[]
  check_target_min?: number
  check_target_max?: number
}

export interface SearchIntentView {
  id: string
  kind: string
  rationale: string
  queries: string[]
  domain_hints: string[]
  recency_days: number | null
}

export interface SearchPlanView {
  profile_id: string
  intents: SearchIntentView[]
  generated_by: string
}

export interface PipelineCounts {
  sent: number
  opened: number | null
  replied: number
  meetings: number
  by_run: Array<Record<string, string | number>>
}

export interface UsageView {
  runs_used: number
  queries_consumed: number
  prompt_tokens: number
  completion_tokens: number
  estimated_cost_usd: number
  by_stage: Record<string, Record<string, number>>
}

export interface Choreography {
  run_id: string
  sources_searched: number
  candidates_found: number
  stale_rejected: number
  investors_verified: number
  evidence_coverage: number
  queries_issued: number
  wall_time_ms: number
  top_target_id: string | null
}

export type OutreachState = 'draft' | 'queued'
