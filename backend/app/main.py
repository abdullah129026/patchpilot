"""Agent service skeleton (FastAPI).

Phase 1 scope only: health, fixture jobs, and validated job submission
into the filesystem store. The reproduction loop, GitHub fetching, and
Docker running arrive in Phase 3; ceilings and takedown arrive in
Phase 2. Submitted jobs stay queued until Phase 3 builds the runner.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import config
from app.fixtures import FIXTURES, get_fixture
from app.github_url import parse_issue_url
from app.job_store import create_job, get_job


class JobRequest(BaseModel):
    issue_url: str


def create_app() -> FastAPI:
    app = FastAPI(title="PatchPilot agent service")

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "service": config.SERVICE_NAME,
            "version": config.SERVICE_VERSION,
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
    def submit_job(body: JobRequest):
        try:
            owner, repo, number = parse_issue_url(body.issue_url)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return create_job(config.job_dir(), owner, repo, number)

    @app.get("/api/jobs/{job_id}")
    def job_detail(job_id: str):
        job = get_job(config.job_dir(), job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    return app


app = create_app()
