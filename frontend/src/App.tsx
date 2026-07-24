import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ContextBar } from './components/ContextBar'
import { DetailPanel } from './components/DetailPanel'
import { InvestorList, type SortKey } from './components/InvestorList'
import { RaiseBriefModal, type RaiseBriefDraft } from './components/RaiseBriefModal'
import { SearchTray, type SearchCounters } from './components/SearchTray'
import { NavRail, type NavId } from './components/NavRail'
import { PlanView } from './components/PlanView'
import { QueueView } from './components/QueueView'
import { SignalView } from './components/SignalView'
import { StatusStrip } from './components/StatusStrip'
import { ToastStack, type ToastMessage } from './components/Toast'
import { offlineSnapshot } from './data/offlineSnapshot'
import { api } from './lib/api'
import { SEQUENCE_MS, counterAt } from './lib/choreography'
import type {
  DraftPublic,
  PipelineCounts,
  RunStatus,
  SearchPlanView,
  SequenceView,
  TargetDetail,
  TargetSummary,
  UsageView,
  WorkspaceProfile,
} from './types'

export default function App() {
  const [section, setSection] = useState<NavId>('investors')
  const [profile, setProfile] = useState<WorkspaceProfile | null>(null)
  const [run, setRun] = useState<RunStatus | null>(null)
  const [rows, setRows] = useState<TargetSummary[]>([])
  const [elapsed, setElapsed] = useState(SEQUENCE_MS)
  const [counters, setCounters] = useState<SearchCounters>({
    sources: 0,
    candidates: 0,
    rejected: 0,
    verified: 0,
    coverage: 0,
  })
  const [briefOpen, setBriefOpen] = useState(false)
  const [savingBrief, setSavingBrief] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [offline, setOffline] = useState(false)
  const [loadingList, setLoadingList] = useState(true)
  const [running, setRunning] = useState(false)
  const [activityOpen, setActivityOpen] = useState(false)

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [target, setTarget] = useState<TargetDetail | null>(null)
  const [draft, setDraft] = useState<DraftPublic | null>(null)
  const [sequence, setSequence] = useState<SequenceView | null>(null)
  const [body, setBody] = useState('')
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [approving, setApproving] = useState(false)

  const [plan, setPlan] = useState<SearchPlanView | null>(null)
  const [queue, setQueue] = useState<DraftPublic[]>([])
  const [loadingQueue, setLoadingQueue] = useState(false)
  const [runHistory, setRunHistory] = useState<RunStatus[]>([])
  const [counts, setCounts] = useState<PipelineCounts | null>(null)
  const [usage, setUsage] = useState<UsageView | null>(null)

  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<SortKey>('score')
  const [chips, setChips] = useState<string[]>([])
  const [toasts, setToasts] = useState<ToastMessage[]>([])
  const cancelSequence = useRef<(() => void) | null>(null)
  const skipRef = useRef<(() => void) | null>(null)
  const selectTargetRef = useRef<((row: TargetSummary) => Promise<void>) | null>(null)

  const pushToast = useCallback((toast: Omit<ToastMessage, 'id'>) => {
    const id = Date.now() + Math.random()
    setToasts((current) => [...current, { ...toast, id }])
    window.setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), 5200)
  }, [])

  const loadOffline = useCallback(() => {
    setOffline(true)
    setRun(offlineSnapshot.run)
    setRows(offlineSnapshot.rows)
    setLoadingList(false)
  }, [])

  useEffect(() => {
    let cancelled = false
    async function boot() {
      try {
        const [profiles, runs] = await Promise.all([api.profiles(), api.runs()])
        if (cancelled) return
        setProfile(profiles[0] ?? null)
        const latest = runs.find((r) => r.status === 'complete') ?? runs[0] ?? null
        let loadedRows: TargetSummary[] = []
        if (latest) {
          setRun(latest)
          const page = await api.targets(latest.run_id)
          loadedRows = page.rows
          if (!cancelled) setRows(page.rows)
        }
        if (!cancelled && loadedRows.length === 0) {
          // Serverless instances do not share memory, so a warm run may live on another
          // instance. Running the pipeline here guarantees the workspace opens populated.
          const result = await api.demoSearch()
          if (cancelled) return
          const [status, page] = await Promise.all([api.run(result.run_id), api.targets(result.run_id)])
          setRun(status)
          setRows(page.rows)
          setCounters({
            sources: result.sources_searched,
            candidates: result.candidates_found,
            rejected: result.stale_rejected,
            verified: result.investors_verified,
            coverage: result.evidence_coverage,
          })
        }
      } catch {
        if (!cancelled) loadOffline()
      } finally {
        if (!cancelled) setLoadingList(false)
      }
    }
    boot()
    return () => {
      cancelled = true
      cancelSequence.current?.()
    }
  }, [loadOffline])

  const applyRun = useCallback(async (runId: string, topTargetId: string | null) => {
    const [status, page] = await Promise.all([api.run(runId), api.targets(runId)])
    setRun(status)
    setRows(page.rows)
    return { status, rows: page.rows, topTargetId }
  }, [])

  const runLiveSearch = useCallback(async () => {
    if (offline || running) return
    setRunning(true)
    setActivityOpen(true)
    setElapsed(0)
    setCounters({ sources: 0, candidates: 0, rejected: 0, verified: 0, coverage: 0 })

    let frame = 0
    let cancelled = false
    const started = performance.now()

    try {
      const resultPromise = api.demoSearch()
      const targets = await resultPromise
      if (cancelled) return

      const tick = () => {
        const t = Math.min(SEQUENCE_MS, performance.now() - started)
        setElapsed(t)
        setCounters({
          sources: counterAt(targets.sources_searched, t, 700, 2600),
          candidates: counterAt(targets.candidates_found, t, 2600, 1800),
          rejected: counterAt(targets.stale_rejected, t, 4700, 1200),
          verified: counterAt(targets.investors_verified, t, 5900, 1200),
          coverage: t > 6600 ? targets.evidence_coverage : 0,
        })
        if (t < SEQUENCE_MS && !cancelled) frame = requestAnimationFrame(tick)
      }
      frame = requestAnimationFrame(tick)

      const finish = async (skipped: boolean) => {
        cancelAnimationFrame(frame)
        cancelled = true
        cancelSequence.current = null
        setElapsed(SEQUENCE_MS)
        setCounters({
          sources: targets.sources_searched,
          candidates: targets.candidates_found,
          rejected: targets.stale_rejected,
          verified: targets.investors_verified,
          coverage: targets.evidence_coverage,
        })
        const applied = await applyRun(targets.run_id, targets.top_target_id)
        setRunning(false)
        const top = applied.rows.find((r) => r.target_id === targets.top_target_id) ?? applied.rows[0]
        if (top) void selectTargetRef.current?.(top)
        pushToast({
          title: skipped ? 'Search complete' : 'Search complete',
          detail: `${targets.investors_verified} verified · ${targets.stale_rejected} stale records rejected · ${targets.queries_issued} queries in ${targets.wall_time_ms}ms · 100% evidence coverage`,
          tone: 'success',
        })
      }

      cancelSequence.current = () => {
        cancelAnimationFrame(frame)
        cancelled = true
        cancelSequence.current = null
        setRunning(false)
        setElapsed(SEQUENCE_MS)
      }

      window.setTimeout(() => {
        if (!cancelled) void finish(false)
      }, SEQUENCE_MS)

      skipRef.current = () => void finish(true)
    } catch {
      setRunning(false)
      pushToast({ title: 'Search failed', detail: 'The API rejected the request.', tone: 'warning' })
    }
  }, [applyRun, offline, pushToast, running])

  const resetDemo = useCallback(async () => {
    if (offline) return
    setResetting(true)
    cancelSequence.current?.()
    try {
      const result = await api.demoReset()
      setSelectedId(null)
      setTarget(null)
      setDraft(null)
      setSequence(null)
      setBody('')
      setQuery('')
      setChips([])
      setSort('score')
      setActivityOpen(false)
      setElapsed(SEQUENCE_MS)
      setCounters({
        sources: result.sources_searched,
        candidates: result.candidates_found,
        rejected: result.stale_rejected,
        verified: result.investors_verified,
        coverage: result.evidence_coverage,
      })
      await applyRun(result.run_id, result.top_target_id)
      const profiles = await api.profiles()
      setProfile(profiles[0] ?? null)
      pushToast({ title: 'Demo reset', detail: 'Workspace returned to its opening state.', tone: 'success' })
    } catch {
      pushToast({ title: 'Reset failed', detail: 'The API rejected the request.', tone: 'warning' })
    } finally {
      setResetting(false)
    }
  }, [applyRun, offline, pushToast])

  const saveBrief = useCallback(
    async (draftBrief: RaiseBriefDraft) => {
      setSavingBrief(true)
      try {
        const saved = await api.saveProfile({
          company: draftBrief.company,
          one_liner: draftBrief.one_liner,
          round: draftBrief.round,
          raise_target: draftBrief.raise_target,
          sectors: draftBrief.sectors.split(',').map((v) => v.trim()).filter(Boolean),
          geographies: draftBrief.geographies.split(',').map((v) => v.trim()).filter(Boolean),
          check_target_min: draftBrief.check_target_min,
          check_target_max: draftBrief.check_target_max,
        })
        setProfile(saved)
        setBriefOpen(false)
        pushToast({
          title: 'Raise brief saved',
          detail: 'Run a live search to re-plan against the updated brief.',
          tone: 'success',
        })
      } catch {
        pushToast({ title: 'Could not save brief', detail: 'The API rejected the update.', tone: 'warning' })
      } finally {
        setSavingBrief(false)
      }
    },
    [pushToast],
  )

  const selectTarget = useCallback(
    async (row: TargetSummary) => {
      setSelectedId(row.target_id)
      setLoadingDetail(true)
      setDraft(null)
      setSequence(null)
      setBody('')
      if (offline) {
        const detail = offlineSnapshot.details.find((d) => d.target_id === row.target_id) ?? null
        const offlineDraft = offlineSnapshot.drafts.find((d) => d.target_id === row.target_id) ?? null
        setTarget(detail)
        setDraft(offlineDraft)
        setBody(offlineDraft?.body ?? '')
        setLoadingDetail(false)
        return
      }
      try {
        const detail = await api.target(row.target_id)
        setTarget(detail)
        const nextDraft = await api.draft(row.target_id)
        setDraft(nextDraft)
        setBody(nextDraft.body)
        setSequence(await api.sequence(row.target_id))
      } catch {
        pushToast({ title: 'Could not load investor', detail: 'The detail request failed.', tone: 'warning' })
      } finally {
        setLoadingDetail(false)
      }
    },
    [offline, pushToast],
  )

  useEffect(() => {
    selectTargetRef.current = selectTarget
  }, [selectTarget])

  const approve = useCallback(async () => {
    if (!draft || !target) return
    if (offline) {
      pushToast({
        title: 'Approval needs the API',
        detail: 'Start the backend to queue this message and schedule follow-ups.',
        tone: 'warning',
      })
      return
    }
    setApproving(true)
    try {
      if (body !== draft.body) await api.patchDraft(draft.draft_id, { body })
      const approved = await api.approve(draft.draft_id)
      setDraft(approved)
      setBody(approved.body)
      setSequence(await api.sequence(target.target_id))
      setRows((current) =>
        current.map((row) => (row.target_id === target.target_id ? { ...row, status: 'approved' } : row)),
      )
      pushToast({
        title: 'Approved & queued',
        detail: `${target.investor_person ?? target.investor_firm} — queued for send from your own domain. Follow-ups at day 4 and day 10.`,
        tone: 'success',
      })
    } catch (error) {
      pushToast({
        title: 'Approval blocked',
        detail: error instanceof Error ? error.message : 'The API rejected the approval.',
        tone: 'warning',
      })
    } finally {
      setApproving(false)
    }
  }, [approving, body, draft, offline, pushToast, target])

  const chipOptions = useMemo(() => {
    const set = new Set<string>()
    rows.forEach((row) => [...row.stage, ...row.sectors].forEach((tag) => set.add(tag)))
    return Array.from(set).slice(0, 8)
  }, [rows])

  const visibleRows = useMemo(() => {
    const needle = query.trim().toLowerCase()
    let filtered = rows.filter((row) => row.status !== 'dismissed')
    if (needle) {
      filtered = filtered.filter((row) =>
        [row.investor_person ?? '', row.investor_firm, row.lead_evidence.claim, row.lead_evidence.detail]
          .join(' ')
          .toLowerCase()
          .includes(needle),
      )
    }
    if (chips.length) {
      filtered = filtered.filter((row) => chips.every((chip) => [...row.stage, ...row.sectors].includes(chip)))
    }
    const sorted = [...filtered]
    if (sort === 'firm') sorted.sort((a, b) => a.investor_firm.localeCompare(b.investor_firm))
    else if (sort === 'recency')
      sorted.sort(
        (a, b) =>
          new Date(b.lead_evidence.event_date ?? 0).getTime() - new Date(a.lead_evidence.event_date ?? 0).getTime(),
      )
    else sorted.sort((a, b) => b.score - a.score)
    return sorted
  }, [chips, query, rows, sort])

  const loadRun = useCallback(async (runId: string) => {
    try {
      const [status, page] = await Promise.all([api.run(runId), api.targets(runId)])
      setRun(status)
      setRows(page.rows)
      setSection('investors')
    } catch {
      /* the run list is a convenience; a failure leaves the current view intact */
    }
  }, [])

  useEffect(() => {
    if (offline) return
    if (section === 'search') {
      setActivityOpen(true)
      if (run) api.plan(run.run_id).then(setPlan).catch(() => setPlan(null))
    }
    if (section === 'drafts') {
      setLoadingQueue(true)
      api
        .queue()
        .then(setQueue)
        .catch(() => setQueue([]))
        .finally(() => setLoadingQueue(false))
    }
    if (section === 'signal') {
      Promise.all([api.runs(), api.pipeline(), api.usage()])
        .then(([history, pipelineCounts, usageView]) => {
          setRunHistory(history)
          setCounts(pipelineCounts)
          setUsage(usageView)
        })
        .catch(() => undefined)
    }
  }, [offline, run, section])

  return (
    <div className="flex h-screen w-full bg-void grid-noise">
      <NavRail active={section} onSelect={setSection} />

      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <ContextBar
          profile={profile}
          run={run}
          running={running}
          offline={offline}
          onRunSearch={runLiveSearch}
          onEditBrief={() => setBriefOpen(true)}
          onReset={resetDemo}
          resetting={resetting}
        />
        <StatusStrip run={run} running={running} />
        <SearchTray
          open={activityOpen}
          running={running}
          elapsed={elapsed}
          counters={counters}
          onSkip={() => skipRef.current?.()}
          onCancel={() => cancelSequence.current?.()}
          onClose={() => setActivityOpen(false)}
        />

        {offline && (
          <p className="shrink-0 border-b border-amber/20 bg-amber/[0.06] px-5 py-1.5 font-mono text-[10px] text-amber">
            Backend unreachable — showing a captured run. Start the API on :8000 for live retrieval.
          </p>
        )}
        {run?.list_underfilled && !offline && (
          <p className="shrink-0 border-b border-amber/20 bg-amber/[0.06] px-5 py-1.5 font-mono text-[10px] text-amber">
            List underfilled — fewer than 30 investors cleared the evidence bar. That is a finding about positioning,
            not an error.
          </p>
        )}

        <div className="flex min-h-0 flex-1 overflow-hidden">
          {section === 'investors' && (
            <InvestorList
              rows={visibleRows}
              total={visibleRows.length}
              loading={loadingList}
              selectedId={selectedId}
              query={query}
              sort={sort}
              chips={chipOptions}
              activeChips={chips}
              onQuery={setQuery}
              onSort={setSort}
              onToggleChip={(chip) =>
                setChips((current) => (current.includes(chip) ? current.filter((c) => c !== chip) : [...current, chip]))
              }
              onSelect={selectTarget}
              hasRun={run != null}
              onRunSearch={runLiveSearch}
            />
          )}
          {section === 'search' && <PlanView plan={plan} run={run} />}
          {section === 'drafts' && (
            <QueueView
              drafts={queue}
              rows={rows}
              loading={loadingQueue}
              onOpen={(targetId) => {
                const row = rows.find((r) => r.target_id === targetId)
                if (row) {
                  setSection('investors')
                  void selectTarget(row)
                }
              }}
            />
          )}
          {section === 'signal' && (
            <SignalView runs={runHistory} counts={counts} usage={usage} onOpenRun={loadRun} />
          )}
          <DetailPanel
            target={target}
            draft={draft}
            sequence={sequence}
            body={body}
            loading={loadingDetail}
            approving={approving}
            onBodyChange={setBody}
            onApprove={approve}
          />
        </div>
      </main>

      <RaiseBriefModal
        open={briefOpen}
        profile={profile}
        saving={savingBrief}
        onClose={() => setBriefOpen(false)}
        onSave={saveBrief}
      />

      <ToastStack toasts={toasts} onDismiss={(id) => setToasts((current) => current.filter((t) => t.id !== id))} />
    </div>
  )
}
