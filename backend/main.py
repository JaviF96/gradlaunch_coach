"""
main.py

The FastAPI app. One real endpoint: POST /analyze, which runs the four
agents in sequence and returns a FinalReport.

Run locally with:
    uvicorn main:app --reload

Then open http://localhost:8000/docs to test this endpoint directly in
the browser, no frontend needed yet.
"""

import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from schemas import FinalReport
from agents import context_agent, diagnostic_agent, exemplar_agent, rewrite_agent, PipelineError

app = FastAPI()

# Defaults to localhost for local dev. Set ALLOWED_ORIGINS (comma-separated)
# once this is deployed, e.g. "https://your-frontend.onrender.com".
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5500").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Simple in-memory, per-IP sliding-window rate limit on /analyze, since each
# request costs real money across 4 Claude calls. Resets on restart and
# doesn't share state across multiple instances - fine for a single-instance
# deployment; swap for a Redis-backed limiter if that ever changes.
RATE_LIMIT_MAX_REQUESTS = 5
RATE_LIMIT_WINDOW_SECONDS = 60
_request_log: dict[str, deque] = defaultdict(deque)


def check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    log = _request_log[client_ip]
    while log and now - log[0] > RATE_LIMIT_WINDOW_SECONDS:
        log.popleft()
    if len(log) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many requests. Try again in a minute.")
    log.append(now)


class AnalyzeRequest(BaseModel):
    job_description: str = Field(..., max_length=8000)
    question: str = Field(..., max_length=1000)
    draft_answer: str = Field(..., max_length=6000)

    @field_validator("job_description", "question", "draft_answer")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("This field cannot be empty.")
        return v


@app.post("/analyze", response_model=FinalReport)
def analyze(request: Request, body: AnalyzeRequest) -> FinalReport:
    check_rate_limit(request.client.host)
    try:
        brief = context_agent(body.job_description, body.question)
        diagnostic = diagnostic_agent(brief, body.draft_answer)
        exemplars = exemplar_agent(diagnostic.flags)
        rewrites = rewrite_agent(diagnostic.flags, exemplars)
    except PipelineError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return FinalReport(
        context=brief,
        flags=diagnostic.flags,
        rewrites=rewrites,
    )


@app.get("/health")
def health():
    # TODO: useful for checking the deployed backend is actually up
    return {"status": "ok"}


# TODO (week 2+): a second endpoint like POST /explain that takes a single
# flag and lets a student ask "why was this flagged?" conversationally.
# Keep it separate from /analyze, this is the optional chat layer on top
# of the core report, not a replacement for it.
