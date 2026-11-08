"""Agent service skeleton (FastAPI).

Phase 1 scope: health, fixture jobs, and validated job submission
into the filesystem store. Phase 2 scope: submission ceilings, the
queue view, submitter deletion, and takedown requests. Phase 3
scope: the reproduction loop behind POST /api/jobs/{id}/run, which
starts the job in a background thread and returns 202 so the job page
can watch it live over GET /api/jobs/{id}/stream (SSE) or by polling
the job detail. Attempts land in the job record as they finish.
"""

import json
import threading
import time

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import config, events, limits
from app.fixtures import FIXTURES, get_fixture
from app.github_url import parse_issue_url
from app.job_store import (
    count_active_jobs,
    create_job,
    delete_job,
    get_job,
    record_takedown_request,
)
from app.pipeline import run_job


class JobRequest(BaseModel):
    issue_url: str


class TakedownRequest(BaseModel):
    contact: str = Field(default="", max_length=256)
    reason: str = Field(min_length=1, max_length=1000)


class AnalyticsEvent(BaseModel):
    event: str = Field(max_length=64)
    verdict: str | None = Field(default=None, max_length=32)


def create_app() -> FastAPI:
    app = FastAPI(title="PatchPilot agent service")
    # The demo API is public by design (no accounts, D2): the Vercel
    # frontend and local dev both call it from the browser, so it
    # answers cross-origin. The delete token, not origin, guards deletion.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "service": config.SERVICE_NAME,
            "version": config.SERVICE_VERSION,
        }

    @app.get("/api/stats")
    def stats():
        store = config.job_dir()
        return {
            "events": events.event_counts(store),
            "verdicts": events.verdict_distribution(store),
            "jobs_today": limits.global_today(store),
            "ceiling_stops_today": limits.rejections_today(store),
        }

    @app.post("/api/events", status_code=202)
    def record_analytics_event(body: AnalyticsEvent):
        try:
            events.record_event(config.job_dir(), body.event, body.verdict)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"status": "recorded"}

    @app.get("/api/limits")
    def limit_status(request: Request):
        store = config.job_dir()
        used = limits.usage(store, limits.client_ip(request))
        active = count_active_jobs(store)
        return {
            **used,
            "active_jobs": active,
            "queue_position_for_next": active + 1,
            "paused": limits.is_paused(store),
        }

    @app.get("/api/jobs/fixtures")
    def fixture_list():
        return FIXTURES

    @app.get("/api/jobs/fixtures/{fixture_id}")
    def fixture_detail(fixture_id: str):
        fixture = get_fixture(fixture_id)
        if fixture is None:
            raise HTTPException(status_code=404, detail="fixture not found")
        return fixture

    @app.post("/api/jobs", status_code=201)
    def submit_job(body: JobRequest, request: Request):
        try:
            owner, repo, number = parse_issue_url(body.issue_url)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        store = config.job_dir()
        ip = limits.client_ip(request)
        try:
            limits.check_limits(store, ip)
        except limits.LimitExceeded as exc:
            limits.record_rejection(store, exc.kind)
            raise HTTPException(
                status_code=exc.status_code, detail=exc.message
            ) from exc
        job = create_job(store, owner, repo, number)
        limits.record_submission(store, ip)
        return job

    @app.post("/api/jobs/{job_id}/run", status_code=202)
    def run_job_endpoint(job_id: str):
        job = get_job(config.job_dir(), job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        if limits.is_paused(config.job_dir()):
            raise HTTPException(
                status_code=503,
                detail="PatchPilot is paused right now. Queued jobs cannot "
                "start until the founder resumes the demo.",
            )
        if job.get("status") != "queued":
            raise HTTPException(status_code=409, detail="only queued jobs can be run")
        # A job runs for minutes; the caller watches it live instead of
        # holding one HTTP request open for the whole run.
        from app.job_store import update_job

        update_job(config.job_dir(), job_id, status="running")
        thread = threading.Thread(
            target=run_job, args=(config.job_dir(), job_id), daemon=True
        )
        thread.start()
        return get_job(config.job_dir(), job_id)

    @app.get("/api/jobs/{job_id}/stream")
    def job_stream(job_id: str):
        if get_job(config.job_dir(), job_id) is None:
            raise HTTPException(status_code=404, detail="job not found")

        def events():
            last = None
            for _ in range(config.MAX_JOB_SECONDS + 60):
                job = get_job(config.job_dir(), job_id)
                if job is None:
                    break
                snapshot = (
                    job.get("status"),
                    len(job.get("attempts") or []),
                    job.get("verdict"),
                )
                if snapshot != last:
                    last = snapshot
                    yield f"data: {json.dumps(job)}\n\n"
                if job.get("status") in ("done", "failed"):
                    break
                time.sleep(1)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/api/jobs/{job_id}")
    def job_detail(job_id: str):
        job = get_job(config.job_dir(), job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    @app.delete("/api/jobs/{job_id}", status_code=204)
    def remove_job(job_id: str, request: Request):
        token = request.headers.get("x-delete-token")
        try:
            deleted = delete_job(config.job_dir(), job_id, token)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="job not found")
        return Response(status_code=204)

    @app.post("/api/jobs/{job_id}/takedown-request", status_code=202)
    def takedown_request(job_id: str, body: TakedownRequest):
        if get_job(config.job_dir(), job_id) is None:
            raise HTTPException(status_code=404, detail="job not found")
        record_takedown_request(
            config.job_dir(), job_id, body.contact.strip(), body.reason.strip()
        )
        return {
            "status": "received",
            "detail": "Takedown request recorded. The report stays up until "
            "its owner reviews the request.",
        }

    return app


app = create_app()
