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
from agents import (
    context_agent,
    diagnostic_agent,
    exemplar_agent,
    rewrite_agent,
    new_deadline,
    PipelineError,
)

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


def get_client_ip(request: Request) -> str:
    # Behind Render's proxy, request.client.host is the proxy's own IP for
    # every request, which would collapse the per-user rate limit into one
    # shared limit. X-Forwarded-For carries the real client IP there; only
    # trust the first entry since Render sets this header itself.
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    # request.client is None for some transports (and in some test clients).
    # Fall back to a shared bucket rather than crashing - an unidentifiable
    # caller should still be rate limited, just not individually.
    if request.client is None:
        return "unknown"
    return request.client.host


def _evict_stale_ips(now: float) -> None:
    # _request_log is a defaultdict that only ever grew: every IP that ever
    # called kept an empty deque forever. Sweep the fully-expired ones so a
    # long-running instance doesn't leak an entry per unique caller.
    stale = [
        ip
        for ip, log in _request_log.items()
        if not log or now - log[-1] > RATE_LIMIT_WINDOW_SECONDS
    ]
    for ip in stale:
        del _request_log[ip]


def check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    _evict_stale_ips(now)
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
    check_rate_limit(get_client_ip(request))
    # One budget shared by all three Claude calls, so a slow early stage eats
    # into the later ones rather than extending the total. Without it the
    # stages only bound themselves individually and can still add up.
    deadline = new_deadline()
    try:
        brief = context_agent(body.job_description, body.question, deadline=deadline)
        diagnostic = diagnostic_agent(brief, body.draft_answer, deadline=deadline)
        exemplars = exemplar_agent(diagnostic.flags)
        rewrites = rewrite_agent(
            diagnostic.flags, exemplars, body.job_description, body.draft_answer, deadline=deadline
        )
    except PipelineError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return FinalReport(
        context=brief,
        flags=diagnostic.flags,
        rewrites=rewrites,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
