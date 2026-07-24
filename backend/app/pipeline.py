"""Orchestrates the six stages: plan → retrieve → extract → verify → score → publish.

Stage transitions and progress are streamed to the event bus as they happen. A run always
terminates: external failures degrade the run and land in `warnings`, they never raise.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from uuid import UUID

from .config import get_settings
from .events import BUS
from .models import (
    CompanyProfile,
    RejectedRecord,
    Run,
    RunEvent,
    RunStage,
    TargetRow,
)
from .octen.executor import Executor
from .octen.extractor import Extractor
from .octen.planner import build_plan
from .octen.scorer import Scorer
from .octen.verifier import Verifier
from .store.repo import REPO

log = logging.getLogger("proofline.pipeline")

DEGRADED_FAILURE_RATE = 0.30


async def _emit(run: Run, event_type, message: str | None = None, **data) -> None:
    await BUS.publish(RunEvent(type=event_type, run_id=run.run_id, stage=run.stage, message=message, data=data))


async def _set_stage(run: Run, stage: RunStage, message: str) -> None:
    run.stage = stage
    run.status = "running"
    await REPO.save_run(run)
    await _emit(run, "stage_changed", message)


class Pipeline:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._executor = Executor(settings=self._settings)
        self._verifier = Verifier(settings=self._settings)
        self._extractor = Extractor()
        self._scorer = Scorer(self._settings)

    def cancelled(self, run_id: UUID) -> bool:
        return run_id in REPO.cancelled_runs

    async def run(self, run: Run, profile: CompanyProfile) -> None:
        started = time.perf_counter()
        today = date.today()
        try:
            await _set_stage(run, "planning", "Converting the profile into a structured search plan")
            plan = await build_plan(profile)
            REPO.plans[run.run_id] = plan
            run.progress.queries_total = plan.query_count
            await REPO.save_run(run)
            await _emit(
                run,
                "stage_changed",
                f"Plan ready: {len(plan.intents)} intents, {plan.query_count} queries",
                intents=len(plan.intents),
                queries=plan.query_count,
                generated_by=plan.generated_by,
            )
            if self.cancelled(run.run_id):
                return await self._cancel(run)

            await _set_stage(run, "retrieving", f"Firing {plan.query_count} narrow queries concurrently")

            async def on_progress(done: int, total: int, _: int) -> None:
                run.progress.queries_done = done
                run.progress.queries_total = total
                await _emit(run, "query_batch_done", f"{done}/{total} queries returned", done=done, total=total)

            bundle = await self._executor.execute(plan, on_progress=on_progress)
            run.retrieval_stats = bundle.stats
            run.progress.results = bundle.stats.results
            run.progress.queries_done = bundle.stats.queries_issued
            run.sources_searched = len({r.url for o in bundle.outcomes for r in o.results})
            if bundle.stats.failure_rate > DEGRADED_FAILURE_RATE:
                run.warnings.append("retrieval_degraded")
            await REPO.save_run(run)
            if self.cancelled(run.run_id):
                return await self._cancel(run)

            await _set_stage(run, "extracting", "Distilling raw results into dated evidence records")
            top_urls = [
                result.url
                for outcome in sorted(bundle.outcomes, key=lambda o: -len(o.results))
                for result in outcome.results
            ]
            await self._executor.extract_content(bundle, list(dict.fromkeys(top_urls)))
            report = await self._extractor.extract(bundle)
            run.progress.evidence = len(report.records)
            await REPO.save_run(run)
            await _emit(
                run,
                "stage_changed",
                f"{len(report.records)} dated records from {report.results_seen} results",
                evidence_yield=round(report.yield_rate, 3),
                drops=report.drops,
            )
            if self.cancelled(run.run_id):
                return await self._cancel(run)

            await _set_stage(run, "verifying", "Re-verifying volatile facts before anything is surfaced")

            async def on_rejection(rejected: RejectedRecord) -> None:
                await _emit(
                    run,
                    "record_rejected",
                    f"Rejected {rejected.investor_person or rejected.investor_firm}: {rejected.reason}",
                    firm=rejected.investor_firm,
                    person=rejected.investor_person,
                    reason=rejected.reason,
                    detail=rejected.detail,
                )

            verification = await self._verifier.verify(report.investors, today=today, on_rejection=on_rejection)
            run.rejected_count = len(verification.rejected)
            await REPO.save_run(run)

            await _set_stage(run, "scoring", "Ranking on evidence strength and recency")
            scoring = self._scorer.score(verification.investors, profile, run.run_id, today=today)
            run.rejected_count += len(scoring.dropped)
            for rejected in scoring.dropped:
                await on_rejection(rejected)

            await REPO.put_targets(run.run_id, scoring.rows)
            for row in scoring.rows:
                await _emit(
                    run,
                    "investor_found",
                    f"{row.investor_person or row.investor_firm} — {int(row.score * 100)} fit",
                    target_id=str(row.target_id),
                    firm=row.investor_firm,
                    person=row.investor_person,
                    score=row.score,
                    lead_claim=row.lead_evidence.claim,
                )

            run.progress.investors = len(scoring.rows)
            run.list_underfilled = scoring.list_underfilled
            if scoring.list_underfilled:
                run.warnings.append("list_underfilled")
            run.stage = "complete"
            run.status = "complete"
            run.completed_at = datetime.now(timezone.utc)
            REPO.warnings[run.run_id] = run.warnings
            await REPO.save_run(run)
            await _emit(
                run,
                "run_complete",
                f"{len(scoring.rows)} verified investors, {run.rejected_count} records rejected",
                investors=len(scoring.rows),
                rejected=run.rejected_count,
                wall_time_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:  # a run terminates, always
            log.exception("run %s failed", run.run_id)
            run.status = "failed"
            run.stage = "failed"
            run.error = f"{type(exc).__name__}: {exc}"
            run.completed_at = datetime.now(timezone.utc)
            await REPO.save_run(run)
            await _emit(run, "run_failed", run.error)
        finally:
            await BUS.close(run.run_id)

    async def reverify(self, run: Run, rows: list[TargetRow]) -> list[TargetRow]:
        """Re-run the freshness pass only, keeping extracted evidence (API_ENDPOINTS §4)."""
        today = date.today()
        now = datetime.now(timezone.utc)
        for row in rows:
            for record in row.evidence:
                record.verified_at = now
                age = record.age_days(today)
                threshold = get_settings().freshness_max_age_days
                from .models import FRESHNESS_MAX_AGE_DAYS

                record.stale = age is None or age > FRESHNESS_MAX_AGE_DAYS.get(record.kind, threshold)
            fresh = next((e for e in row.evidence if not e.stale), None)
            if fresh:
                row.lead_evidence = fresh
            elif row.status != "dismissed":
                row.status = "needs_review"
        await REPO.put_targets(run.run_id, rows)
        await _emit(run, "stage_changed", "Freshness pass re-run", reverified=len(rows))
        return rows

    async def _cancel(self, run: Run) -> None:
        run.status = "cancelled"
        run.stage = "cancelled"
        run.completed_at = datetime.now(timezone.utc)
        await REPO.save_run(run)
        await _emit(run, "run_failed", "Run cancelled")


PIPELINE = Pipeline()
