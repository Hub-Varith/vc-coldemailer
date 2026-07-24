import type {
  Choreography,
  DraftPublic,
  PipelineCounts,
  RunEvent,
  RunStatus,
  SearchPlanView,
  SequenceView,
  TargetDetail,
  TargetSummary,
  UsageView,
  WorkspaceProfile,
} from '../types'

const BASE = '/api/v1'

class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(BASE + path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  })
  const text = await response.text()
  const payload = text ? JSON.parse(text) : null
  if (!response.ok) {
    const error = payload?.error
    throw new ApiError(error?.message ?? response.statusText, error?.code ?? 'unknown', response.status)
  }
  return payload as T
}

export const api = {
  health: () => request<{ status: string; retrieval: string; llm: string }>('/health'),
  profiles: () => request<WorkspaceProfile[]>('/profiles'),
  runs: () => request<RunStatus[]>('/runs'),
  startRun: () => request<{ run_id: string }>('/runs', { method: 'POST', body: '{}' }),
  run: (runId: string) => request<RunStatus>(`/runs/${runId}`),
  reverify: (runId: string) => request<RunStatus>(`/runs/${runId}/reverify`, { method: 'POST' }),
  targets: (runId: string) =>
    request<{ rows: TargetSummary[]; total: number; list_underfilled: boolean }>(
      `/runs/${runId}/targets?limit=80`,
    ),
  target: (targetId: string) => request<TargetDetail>(`/targets/${targetId}`),
  draft: (targetId: string) => request<DraftPublic>(`/targets/${targetId}/draft`, { method: 'POST' }),
  patchDraft: (draftId: string, body: { subject?: string; body?: string }) =>
    request<DraftPublic>(`/drafts/${draftId}`, { method: 'PATCH', body: JSON.stringify(body) }),
  approve: (draftId: string) =>
    request<DraftPublic>(`/drafts/${draftId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: 'founder' }),
    }),
  sequence: (targetId: string) => request<SequenceView>(`/sequences/${targetId}`),
  queue: () => request<DraftPublic[]>('/queue'),
  plan: (runId: string) => request<SearchPlanView>(`/runs/${runId}/plan`),
  pipeline: () => request<PipelineCounts>('/pipeline'),
  usage: () => request<UsageView>('/usage'),
  demoSearch: () => request<Choreography>('/demo/search', { method: 'POST' }),
  demoReset: () => request<Choreography>('/demo/reset', { method: 'POST' }),
  demoProfile: () => request<WorkspaceProfile>('/demo/profile'),
  saveProfile: (body: Record<string, unknown>) =>
    request<WorkspaceProfile>('/demo/profile', { method: 'PUT', body: JSON.stringify(body) }),
}

export function streamRun(runId: string, onEvent: (event: RunEvent) => void): () => void {
  const source = new EventSource(`${BASE}/runs/${runId}/events`)
  const types = [
    'stage_changed',
    'query_batch_done',
    'investor_found',
    'record_rejected',
    'run_complete',
    'run_failed',
  ] as const
  types.forEach((type) => {
    source.addEventListener(type, (event) => {
      try {
        onEvent(JSON.parse((event as MessageEvent).data) as RunEvent)
      } catch {
        /* a malformed frame is a dropped update, never a crash */
      }
    })
  })
  source.addEventListener('stream_end', () => source.close())
  source.onerror = () => source.close()
  return () => source.close()
}

export { ApiError }
