"""
schemas.py

These are the data shapes that flow between agents. Get these right first,
before writing any prompts, because every agent's system prompt is really
just an instruction to "fill in this shape."

FastAPI/Pydantic will validate whatever JSON comes back from Claude against
these models. If a model's required field is missing, you'll get a clear
error here instead of a silent bug three steps later in the pipeline.

"""

from pydantic import BaseModel
from typing import List


# ---- Agent 1: Context Agent ----

class ContextBrief(BaseModel):
    role_focus: str
    # what does this role/question actually value? e.g. "technical depth
    # under pressure" vs "stakeholder communication"

    question_intent: str
    # what is this specific question testing? motivation, teamwork,
    # technical skill, resilience, etc.

    what_strong_answer_needs: List[str]
    # a short list of things a strong answer to THIS question, for
    # THIS role, would need to contain. This is what makes the rubric
    # specific instead of generic.


# ---- Agent 2: Diagnostic Agent ----

class Flag(BaseModel):
    dimension: str
    # which rubric dimension this violates, e.g. "specificity",
    # "STAR structure", "voice authenticity", "trajectory signal"

    quoted_text: str
    # the exact sentence/phrase from the student's draft that triggered this flag

    reason: str
    # plain-language explanation of why this is a problem, written the
    # way Lorna would explain it to a student, not a generic AI explanation

    id: str
    # unique identifier for this flag, so the frontend can track it across


class DiagnosticReport(BaseModel):
    flags: List[Flag]


# ---- Agent 3: Exemplar Agent ----

class ExemplarMatch(BaseModel):
    dimension: str
    # should match a Flag's dimension so the rewrite agent can pair them up

    before_example: str
    after_example: str
    # pulled from your curated exemplars.json, not invented by the model


# ---- Agent 4: Rewrite Agent ----

class RewriteSuggestion(BaseModel):
    original_text: str
    # should match a Flag's quoted_text

    rewritten_text: str
    reason: str
    # short note on why this rewrite fixes the flagged issue

    flag_id: str
    # should match a Flag's Id so the frontend can pair them up


# ---- Final combined report returned to the frontend ----

class FinalReport(BaseModel):
    context: ContextBrief
    flags: List[Flag]
    rewrites: List[RewriteSuggestion]
