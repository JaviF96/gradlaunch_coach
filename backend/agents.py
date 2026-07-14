"""
agents.py

Four functions, one per stage of the pipeline. Each one:
  1. builds a system prompt describing its ONE job
  2. calls Claude
  3. parses the JSON response into the matching schema from schemas.py

The `call_claude_json` helper below is working infrastructure code, you
shouldn't need to change it much. The system prompts inside each agent
function are left as TODOs on purpose. That's the actual rubric IP, the
part worth building carefully yourself rather than having handed to you.
"""

import os
import json
import logging
from pathlib import Path
from anthropic import Anthropic, APIError
from dotenv import load_dotenv
from pydantic import ValidationError

from schemas import ContextBrief, DiagnosticReport, Flag, ExemplarMatch, RewriteSuggestion

load_dotenv()

logger = logging.getLogger(__name__)

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

EXEMPLARS_PATH = Path(__file__).parent / "exemplars.json"

# TODO: check docs.claude.com for the current recommended model name.
# Pick something capable, this pipeline is doing real reasoning at each stage.
MODEL_NAME = "claude-haiku-4-5"

# Per-stage output caps. context_agent's output is a handful of short
# strings; diagnostic_agent/rewrite_agent return lists that grow with the
# number of flags, so they get more headroom to avoid silent truncation.
CONTEXT_MAX_TOKENS = 1000
DIAGNOSTIC_MAX_TOKENS = 2000
REWRITE_MAX_TOKENS = 2000


class PipelineError(Exception):
    """Raised when a pipeline stage can't produce a usable result - a Claude
    API failure, an empty/refused response, unparseable JSON, or a response
    that doesn't match the expected schema. main.py catches this as the one
    signal that a stage failed, and turns it into a clean HTTP error."""


def call_claude_json(system_prompt: str, user_message: str, *, max_tokens: int, _retry: bool = True) -> dict:
    """
    Shared helper: sends one message to Claude, expects ONLY valid JSON back,
    and parses it. All four Claude-calling agents route through this.

    If Claude wraps the JSON in markdown fences, that's stripped. If the JSON
    fails to parse, this retries once before giving up.
    """
    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
    except APIError as e:
        raise PipelineError(f"Claude API request failed: {e}") from e

    if not response.content:
        raise PipelineError(f"Claude returned no content (stop_reason={response.stop_reason!r})")

    raw_text = response.content[0].text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        raw_text = raw_text.rsplit("```", 1)[0].strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        if _retry:
            return call_claude_json(system_prompt, user_message, max_tokens=max_tokens, _retry=False)
        raise PipelineError(f"Agent did not return valid JSON after retry. Raw response: {raw_text}")


# ---- Agent 1: Context Agent ----

def context_agent(job_description: str, question: str) -> ContextBrief:
    """
    Reads the job description and the interview/application question.
    Figures out what this role actually values and what a strong answer
    to THIS question needs to contain.

    TODO: write the system prompt. Things to think about:
    - What should it look for in a job description? (seniority, technical
      vs soft skill emphasis, specific tools/domains mentioned)
    - What question types should it recognise? (behavioural, technical,
      motivation, "tell me about a time...")
    - Tell it explicitly to return ONLY JSON matching the ContextBrief shape:
      role_focus, question_intent, what_strong_answer_needs (a list)
    """
    system_prompt = """
      You are the first stage in an application-coaching pipeline. Your only job
      is to read a job description and a single application or interview question,
      and figure out what a genuinely strong answer to THIS question, for THIS
      role, would need to contain.

      Do not evaluate any answer. You have not been given one. Just analyse the
      job description and question.

      Think about:
      - What does this role actually seem to value? (e.g. technical depth,
        stakeholder communication, ownership under ambiguity, speed of execution)
      - What is this specific question testing? (e.g. a behavioural question
        testing resilience is different from a technical question testing
        problem-solving depth)
      - What would a strong answer need to include to prove that, specifically?
        Aim for 3 to 5 concrete things, not generic advice like "be confident."

      Respond with ONLY valid JSON, no markdown fences, no preamble, no
      commentary before or after. Match this exact shape:

      {
        "role_focus": "short phrase describing what this role/question values",
        "question_intent": "one sentence on what this question is really testing",
        "what_strong_answer_needs": [
          "concrete thing one",
          "concrete thing two",
          "concrete thing three"
        ]
      }
      """

    user_message = f"""
    Job description:
    {job_description}

    Question:
    {question}
    """

    result = call_claude_json(system_prompt, user_message, max_tokens=CONTEXT_MAX_TOKENS)
    try:
        return ContextBrief(**result)
    except ValidationError as e:
        raise PipelineError(f"Claude's context response didn't match the expected shape: {e}") from e


# ---- Agent 2: Diagnostic Agent ----

def diagnostic_agent(brief: ContextBrief, draft_answer: str) -> DiagnosticReport:
    """
    Scores the draft answer against Lorna's rubric dimensions, using the
    brief from the context agent to make the scoring specific rather than
    generic.

    TODO: this is where the actual rubric lives. Write the system prompt
    to check for, at minimum, the dimensions discussed:
    - STAR structure / outcome with a number attached
    - specificity (real tools/figures vs vague phrases)
    - voice authenticity (too polished/corporate for the person's stage)
    - trajectory signal (direction over finished portfolio)
    - generic cover-letter tells

    Tell it to return ONLY JSON matching DiagnosticReport: a list of flags,
    each with dimension, quoted_text (exact phrase from the draft), and reason.
    """
    system_prompt = """
    You are the diagnostic stage in an application-coaching pipeline. You have
    been given a brief describing what a strong answer needs, and a student's
    actual draft answer. Your job is to find real, specific problems in the
    draft, not to rewrite it and not to give generic praise.

    Check the draft against these dimensions. Only flag a dimension if there is
    a genuine, specific issue, do not invent flags to fill a quota, and if the
    draft is already strong on a dimension, say nothing about it.

    - star_structure: does the answer describe a situation, action, and a
      result, and does the result include a real number or concrete outcome?
      Flag if the result is vague or missing entirely.
    - specificity: does the answer name real tools, technologies, numbers, or
      outcomes, or does it lean on vague phrases like "AI tools" or "improved
      efficiency" without saying how much or which ones?
    - voice_authenticity: does the answer sound like a genuine student or
      early-career voice, or does it read as overly polished, corporate, or
      AI-generated?
    - trajectory_signal: does the answer show direction and growth, or does it
      just list a finished achievement with no sense of what it led to next?
    - generic_phrasing: does the answer contain stock phrases or structures
      common in AI-written or template cover letters (e.g. rigid three-part
      sentences, hollow enthusiasm with no substance behind it)?

    For each issue you find, quote the EXACT sentence or phrase from the draft
    answer that triggered the flag, word for word, so it can be located and
    highlighted later. Do not paraphrase the quoted text.

    Respond with ONLY valid JSON, no markdown fences, no preamble, no
    commentary before or after. Match this exact shape:

    {
      "flags": [
        {
          "dimension": "one of: star_structure, specificity, voice_authenticity, trajectory_signal, generic_phrasing",
          "quoted_text": "the exact phrase from the draft answer",
          "reason": "plain-language explanation of why this is a problem, written the way a coach would say it to a student"
        }
      ]
    }

    If the draft has no real issues, return an empty flags list. Do not force
    flags that aren't genuinely there.
    """

    user_message = f"""
    Context brief:
    {brief.model_dump_json()}

    Draft answer:
    {draft_answer}
    """

    result = call_claude_json(system_prompt, user_message, max_tokens=DIAGNOSTIC_MAX_TOKENS)
    try:
        return DiagnosticReport(**result)
    except ValidationError as e:
        raise PipelineError(f"Claude's diagnostic response didn't match the expected shape: {e}") from e


# ---- Agent 3: Exemplar Agent ----

def _load_exemplars() -> dict[str, dict]:
    try:
        with open(EXEMPLARS_PATH) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise PipelineError(f"Could not load exemplars.json: {e}") from e
    return {e["dimension"]: e for e in data["exemplars"]}


def exemplar_agent(flags: list[Flag]) -> list[ExemplarMatch]:
    """
    For each flagged dimension, pulls a real before/after example from
    exemplars.json. Early version: simple lookup by dimension, not a full
    retrieval system.

    Dedupes by dimension (multiple flags on the same dimension only need one
    exemplar). If a dimension has no curated exemplar yet, logs a warning and
    skips it rather than inventing a placeholder, so gaps in exemplars.json
    surface without blocking the rest of the pipeline.
    """
    exemplars_by_dimension = _load_exemplars()

    matches = []
    seen_dimensions = set()
    for flag in flags:
        if flag.dimension in seen_dimensions:
            continue
        seen_dimensions.add(flag.dimension)

        exemplar = exemplars_by_dimension.get(flag.dimension)
        if exemplar is None:
            logger.warning(
                "No exemplar found for dimension '%s' - add one to exemplars.json",
                flag.dimension,
            )
            continue

        matches.append(ExemplarMatch(
            dimension=exemplar["dimension"],
            before_example=exemplar["before_example"],
            after_example=exemplar["after_example"],
        ))

    return matches


# ---- Agent 4: Rewrite Agent ----

def rewrite_agent(flags: list[Flag], exemplars: list[ExemplarMatch]) -> list[RewriteSuggestion]:
    """
    Rewrites ONLY the flagged sentences, using the matched exemplar as a
    grounding reference so the output sounds like real coaching rather than
    generic AI polish.
    """
    system_prompt = """
    You are the final stage in an application-coaching pipeline. You have been
    given a list of flagged issues from a student's draft answer, and for each
    flag, a matched exemplar showing a real before/after fix for that same kind
    of issue.

    Your job is to rewrite ONLY the flagged text, one rewrite per flag. Do not
    rewrite the whole answer, and do not touch any part of the draft that
    wasn't flagged.

    Ground each rewrite in the matched exemplar's after_example, but do not copy
    it directly, the exemplar shows the STYLE of fix for that dimension, not the
    literal words to use. The rewrite must still be about the student's own
    project, tools, and experience as described in their original quoted_text,
    just expressed the way the exemplar demonstrates.

    Keep the student's own voice. Do not make the rewrite sound uniformly
    "professional" or corporate. If the original flagged text was casual, the
    fix should still sound like the same person, just clearer or more specific,
    not like a different, more polished writer took over.

    If a flag has no matched exemplar, still write a rewrite, just rely on the
    flag's own dimension and reason to guide the fix instead.

    Respond with ONLY valid JSON, no markdown fences, no preamble, no
    commentary before or after. Match this exact shape, a JSON array with one
    object per flag, in the same order the flags were given:

    [
      {
        "original_text": "the exact quoted_text from the flag, unchanged",
        "rewritten_text": "the improved version of that specific text",
        "reason": "one sentence on what changed and why, in coaching language"
      }
    ]
    """

    user_message = f"""
    Flags:
    {json.dumps([f.model_dump() if hasattr(f, "model_dump") else f for f in flags])}

    Matched exemplars:
    {json.dumps([e.model_dump() for e in exemplars])}
    """

    result = call_claude_json(system_prompt, user_message, max_tokens=REWRITE_MAX_TOKENS)
    try:
        return [RewriteSuggestion(**r) for r in result]
    except ValidationError as e:
        raise PipelineError(f"Claude's rewrite response didn't match the expected shape: {e}") from e
