"""
agents.py

Four functions, one per stage of the pipeline. Each one:
  1. builds a system prompt describing its ONE job
  2. calls Claude
  3. parses the JSON response into the matching schema from schemas.py

"""

import os
import json
import logging
import time
from pathlib import Path
from anthropic import Anthropic, APIError, APITimeoutError
from dotenv import load_dotenv
from pydantic import ValidationError

from schemas import ContextBrief, DiagnosticReport, Flag, ExemplarMatch, RewriteSuggestion

load_dotenv()

logger = logging.getLogger(__name__)

EXEMPLARS_PATH = Path(__file__).parent / "exemplars.json"

MODEL_NAME = "claude-sonnet-5"

# Per-stage output caps. context_agent's output is a handful of short
# strings; diagnostic_agent/rewrite_agent return lists that grow with the
# number of flags, so they get more headroom to avoid silent truncation.
CONTEXT_MAX_TOKENS = 2000
DIAGNOSTIC_MAX_TOKENS = 4000
REWRITE_MAX_TOKENS = 4000

# Timeouts. The SDK defaults to a 600s read timeout and 2 internal retries,
# so one hung call could tie up a request for 30 minutes behind a spinner
# that promises 10-20 seconds. These bound it instead:
#
#   CLAUDE_TIMEOUT_SECONDS  ceiling on any single HTTP attempt
#   CLAUDE_MAX_RETRIES      SDK-level retries per call (down from 2)
#   PIPELINE_BUDGET_SECONDS wall-clock budget for all 3 calls in a request
#
# The budget is the real guarantee: each call gets whatever is left of it,
# capped at the per-attempt ceiling, so the pipeline cannot outrun it no
# matter how the individual stages behave. Keep the frontend's abort in
# api.ts comfortably above PIPELINE_BUDGET_SECONDS so the backend's own
# clean error wins the race and the user sees a real message.
CLAUDE_TIMEOUT_SECONDS = 60.0
CLAUDE_MAX_RETRIES = 1
PIPELINE_BUDGET_SECONDS = 150.0

# Below this there isn't enough budget left for a call to plausibly finish,
# so fail immediately rather than burn a request that is going to time out.
MIN_CALL_SECONDS = 5.0


class PipelineError(Exception):
    """Raised when a pipeline stage can't produce a usable result - a Claude
    API failure, an empty/refused response, unparseable JSON, or a response
    that doesn't match the expected schema. main.py catches this as the one
    signal that a stage failed, and turns it into a clean HTTP error."""


_client: Anthropic | None = None


def get_client() -> Anthropic:
    """
    Builds the Anthropic client on first use rather than at import time.

    Constructing it at import would raise if ANTHROPIC_API_KEY is missing,
    which kills the whole app at startup - /health included - over what is
    really a per-request failure. Deferring it means the app always boots and
    a missing key surfaces as a clean 502 naming the actual problem.
    """
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise PipelineError(
                "ANTHROPIC_API_KEY is not set. Copy backend/.env.example to backend/.env and add your key."
            )
        _client = Anthropic(
            api_key=api_key,
            timeout=CLAUDE_TIMEOUT_SECONDS,
            max_retries=CLAUDE_MAX_RETRIES,
        )
    return _client


def new_deadline() -> float:
    """Wall-clock instant by which a whole /analyze request must be done."""
    return time.monotonic() + PIPELINE_BUDGET_SECONDS


def _timeout_for_call(deadline: float | None) -> float:
    """
    How long the next Claude call may take: whatever is left of the request
    budget, capped at the per-attempt ceiling. Raises if the budget is spent,
    so a slow first stage can't drag the later ones past the deadline.
    """
    if deadline is None:
        return CLAUDE_TIMEOUT_SECONDS
    remaining = deadline - time.monotonic()
    if remaining < MIN_CALL_SECONDS:
        raise PipelineError(
            "Analysis took too long and was stopped. Try again, or shorten your draft answer."
        )
    return min(remaining, CLAUDE_TIMEOUT_SECONDS)


def call_claude_json(
    system_prompt: str,
    user_message: str,
    *,
    max_tokens: int,
    expect: type,
    deadline: float | None = None,
    _retry: bool = True,
) -> dict | list:
    """
    Shared helper: sends one message to Claude, expects ONLY valid JSON back,
    and parses it. All three Claude-calling agents route through this.

    `expect` is the container type the caller needs (dict or list). Anything
    else - most commonly a {"rewrites": [...]} wrapper where a bare array was
    asked for - is a PipelineError rather than an AttributeError/TypeError
    thrown three lines later in the caller.

    If Claude wraps the JSON in markdown fences, that's stripped. If the JSON
    fails to parse, this retries once before giving up.
    """
    try:
        response = get_client().messages.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            timeout=_timeout_for_call(deadline),
        )
    except APITimeoutError as e:
        # Checked before the general APIError branch - it's a subclass, and a
        # timeout is worth its own message since the fix is different.
        logger.error("Claude call timed out after %.0fs", CLAUDE_TIMEOUT_SECONDS)
        raise PipelineError(
            "The feedback service took too long to respond. Try again, or shorten your draft answer."
        ) from e
    except APIError as e:
        logger.error("Claude API request failed: %s", e)
        raise PipelineError("The feedback service is unavailable right now. Try again in a moment.") from e

    if not response.content:
        raise PipelineError(f"Claude returned no content (stop_reason={response.stop_reason!r})")

    # Read only text blocks. Models with thinking on (e.g. Sonnet) put a
    # ThinkingBlock first, so response.content[0] isn't guaranteed to be text -
    # blindly reading .text off it raises AttributeError. Join all text blocks
    # in case the model splits its output across more than one.
    text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    if not text_blocks:
        raise PipelineError(f"Claude returned no text block (stop_reason={response.stop_reason!r})")

    raw_text = "".join(text_blocks).strip()

    if raw_text.startswith("```"):
        # partition, not split(...)[1] - a bare "```json" with no newline after
        # it would make the latter raise IndexError. Here it just yields an
        # empty string, which falls through to the JSON error below.
        raw_text = raw_text.partition("\n")[2]
        raw_text = raw_text.rsplit("```", 1)[0].strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        # A truncated response is the most likely cause of unparseable JSON,
        # and retrying reproduces it at exactly the same length for double the
        # cost. Only retry when the model actually finished its turn.
        if response.stop_reason == "max_tokens":
            logger.error("Response hit max_tokens (%d) and was cut off mid-JSON: %s", max_tokens, raw_text)
            raise PipelineError(
                "The response was cut off before it finished. Try a shorter draft answer."
            ) from e
        if _retry:
            logger.warning("Response was not valid JSON, retrying once: %s", raw_text)
            return call_claude_json(
                system_prompt,
                user_message,
                max_tokens=max_tokens,
                expect=expect,
                deadline=deadline,
                _retry=False,
            )
        # The raw text goes to the logs, not into the exception - main.py puts
        # the message straight into an HTTP detail the browser renders, and a
        # wall of unparsed model output is neither useful nor safe there.
        logger.error("Response was not valid JSON after retry: %s", raw_text)
        raise PipelineError("The feedback service returned a malformed response. Try again.") from e

    # A bare array was asked for, but the model wrapped it in a single-key
    # object like {"rewrites": [...]}. Unwrap rather than fail - this is a
    # common model quirk, not a real shape mismatch.
    if expect is list and isinstance(parsed, dict) and len(parsed) == 1:
        (only_value,) = parsed.values()
        if isinstance(only_value, list):
            parsed = only_value

    # No retry here: the JSON parsed fine, the model just chose a different
    # shape. A second identical call is unlikely to change that and costs real
    # money, so fail loudly instead.
    if not isinstance(parsed, expect):
        logger.error(
            "Response was %s, expected %s: %s", type(parsed).__name__, expect.__name__, raw_text
        )
        raise PipelineError(
            f"The feedback service returned the wrong shape of response "
            f"({type(parsed).__name__} instead of {expect.__name__}). Try again."
        )

    return parsed


# ---- Agent 1: Context Agent ----

def context_agent(job_description: str, question: str, *, deadline: float | None = None) -> ContextBrief:
    """
    Reads the job description and the interview/application question.
    Figures out what this role actually values and what a strong answer
    to THIS question needs to contain.

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

    result = call_claude_json(
        system_prompt, user_message, max_tokens=CONTEXT_MAX_TOKENS, expect=dict, deadline=deadline
    )
    try:
        return ContextBrief(**result)
    except (ValidationError, TypeError) as e:
        logger.error("Context response didn't match ContextBrief: %s", e)
        raise PipelineError("The feedback service returned an unexpected context response. Try again.") from e


# ---- Agent 2: Diagnostic Agent ----

def diagnostic_agent(
    brief: ContextBrief, draft_answer: str, *, deadline: float | None = None
) -> DiagnosticReport:
    """
    Scores the draft answer against Lorna's rubric dimensions, using the
    brief from the context agent to make the scoring specific rather than
    generic. The rubric itself lives in the system prompt below: star_structure,
    specificity, voice_authenticity, trajectory_signal, generic_phrasing.
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
      Before flagging a missing or vague result, check whether a nearby
      sentence - even the very next one - already supplies some form of
      outcome or takeaway. If the result is still genuinely absent or too
      vague, quote through to that sentence rather than just the action
      alone, so the fix can build on what's already there instead of
      ignoring or duplicating it.
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

    Check across all five dimensions as one set before finalizing, not each in
    isolation. If two candidate flags would quote the same or overlapping text
    and point at essentially the same underlying gap - even if one calls it a
    missing outcome and another calls it missing detail - keep only ONE: the
    dimension and reason that name the actual problem most precisely. Never
    flag the same piece of text twice for what is really one issue described
    two ways.

    For each issue you find, quote the EXACT sentence or phrase from the draft
    answer that triggered the flag, word for word, so it can be located and
    highlighted later. Do not paraphrase the quoted text.

    quoted_text must be one or more COMPLETE sentences - never a fragment that
    only makes grammatical sense attached to the sentence before or after it.
    In particular, never quote just the portion of a sentence that follows a
    colon or semicolon as if it stood alone; quote the whole sentence.

    If the same underlying issue repeats across more than one sentence (e.g. a
    templated "Firstly / Secondly / Thirdly" list), quoted_text must span
    EVERY affected sentence, from the first instance through the last, as ONE
    flag - not just the first occurrence - so a single rewrite can fix the
    whole pattern at once.

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

    result = call_claude_json(
        system_prompt, user_message, max_tokens=DIAGNOSTIC_MAX_TOKENS, expect=dict, deadline=deadline
    )

    flags = result.get("flags", [])
    if not isinstance(flags, list):
        raise PipelineError(f"Diagnostic agent returned 'flags' as {type(flags).__name__}, expected a list.")
    for flag in flags:
        if not isinstance(flag, dict):
            raise PipelineError(f"Diagnostic agent returned a {type(flag).__name__} in 'flags', expected an object.")

    # Backstop for the prompt instruction above: even when the model doesn't
    # catch it, two flags whose quoted_text overlaps by full containment are
    # the same underlying gap counted twice. Drop the contained one - the
    # containing flag's rewrite already spans that exact text - and reassign
    # into result so DiagnosticReport(**result) sees the deduped list too.
    flags = _dedupe_overlapping_flags(flags)
    result["flags"] = flags

    # The id is assigned here rather than asked for in the prompt, so the
    # frontend can pair rewrites to flags without trusting the model to invent
    # unique ids.
    for i, flag in enumerate(flags):
        flag["id"] = f"flag-{i}"

    try:
        return DiagnosticReport(**result)
    except (ValidationError, TypeError) as e:
        logger.error("Diagnostic response didn't match DiagnosticReport: %s", e)
        raise PipelineError("The feedback service returned unexpected flags. Try again.") from e


def _dedupe_overlapping_flags(flags: list[dict]) -> list[dict]:
    """
    Drops flags whose quoted_text is fully contained in another flag's
    quoted_text - the same underlying gap flagged twice, whether under the
    same dimension or two different ones. Keeps the containing flag: its
    rewrite already spans the smaller flag's target text, so nothing is lost.

    Processes longest quoted_text first so containment is checked against
    spans already confirmed to survive, then filters the original list to
    preserve input order. Equal-length duplicate quotes are handled the same
    way: the first one processed is kept, the second is dropped (a string
    contains an identical string).
    """
    texts = [f.get("quoted_text", "") for f in flags]
    order = sorted(range(len(flags)), key=lambda i: -len(texts[i]))
    kept_texts: list[str] = []
    dropped: set[int] = set()
    for i in order:
        text = texts[i]
        if not text:
            continue
        if any(text in kept for kept in kept_texts):
            dropped.add(i)
            continue
        kept_texts.append(text)
    return [f for i, f in enumerate(flags) if i not in dropped]


# ---- Agent 3: Exemplar Agent ----

def _load_exemplars() -> dict[str, ExemplarMatch]:
    """
    Reads exemplars.json and validates every entry up front, so a malformed
    file fails here with a clear message rather than as a KeyError deep in
    exemplar_agent.

    encoding is pinned to utf-8: this file is curated prose, and without it
    Python picks the platform default (cp1252 on Windows), so the first curly
    quote anyone pastes in would load on Linux and crash locally.
    """
    try:
        with open(EXEMPLARS_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise PipelineError(f"Could not load exemplars.json: {e}") from e

    try:
        return {entry["dimension"]: ExemplarMatch(**entry) for entry in data["exemplars"]}
    except (KeyError, TypeError, ValidationError) as e:
        raise PipelineError(f"exemplars.json is malformed: {e}") from e


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

        matches.append(exemplar)

    return matches


# ---- Agent 4: Rewrite Agent ----

def rewrite_agent(
    flags: list[Flag],
    exemplars: list[ExemplarMatch],
    job_description: str,
    draft_answer: str,
    *,
    deadline: float | None = None,
) -> list[RewriteSuggestion]:
    """
    Rewrites ONLY the flagged sentences, using the matched exemplar as a
    grounding reference so the output sounds like real coaching rather than
    generic AI polish.

    draft_answer is passed for context only, so a rewrite can be checked
    against the sentences immediately around it - the model still rewrites
    only the flagged quoted_text, nothing else in the draft.
    """
    system_prompt = """
    You are the final stage in an application-coaching pipeline. You have been
    given a list of flagged issues from a student's draft answer, a matched
    exemplar for each flag showing a real before/after fix for that same kind
    of issue, and the job description the student is applying against.

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

    NEVER FABRICATE. Do not invent outcomes, metrics, numbers, rankings, tool
    names, or any other specific detail that is not either (a) already present
    somewhere in the flag's original_text, or (b) literally present in the job
    description below. This holds even when the matched exemplar's after_example
    contains a specific number or fact - the exemplar is illustrating STYLE
    only, its literal figures are never real and must never be copied or
    imitated with a different invented figure.

    This applies with extra force to anything about the employer: if a flag
    calls for more specificity about the company, its products, deals, or
    scale, you may only reference details that appear verbatim or near-verbatim
    in the job description text. Do not state a fact about the employer from
    your own general knowledge, even if you believe it to be true - it may be
    outdated, wrong, or unverifiable, and the student would repeat it as fact
    in a real application.

    If a fix genuinely needs information you don't have - a real outcome the
    student achieved, a specific company detail not present in the job
    description - do not guess or invent a plausible-sounding stand-in. Insert
    an explicit marker instead, in exactly this format: [[ADD: instruction]].
    The instruction inside must be specific and actionable, telling the student
    exactly what kind of thing to go find or supply, e.g.:
      - "...that ended up [[ADD: how it placed - a ranking out of X teams, or
        how many people used it]]"
      - "[[ADD: a specific Morgan Stanley business line, platform, or deal
        you've actually researched - not a guessed figure]]"
    Never write a generic, non-actionable marker like [[ADD: more detail]] or
    [[ADD: a result]].

    Insert the marker only in place of the specific missing piece. Keep every
    other word around it exactly as the student wrote it - do not restructure
    or pad the rest of the sentence to compensate, and do not add a marker for
    something the original_text or job description already supplies.

    Keep each rewrite as close as possible to the original_text's length.
    These are answers to word-limited application questions, so a flagged
    phrase should come back roughly the same size, not meaningfully expanded,
    except where an [[ADD: ...]] marker itself accounts for the extra length.

    You have also been given the student's full original draft answer, for
    context only. Before writing each rewrite, find the flag's original_text
    inside it and read the sentence(s) immediately before and after. Your
    rewritten_text must work as a literal drop-in replacement: if it were
    substituted for original_text at that exact spot, the result must still
    read as one grammatically correct, coherent passage with whatever comes
    immediately before and after it. In particular, if original_text depends
    grammatically on what precedes it (for example, it is the back half of a
    sentence introduced by a colon, or one item in a list), the rewrite must
    still fit that same grammatical role - do not turn a dependent clause or
    list item into a disconnected, freestanding sentence.

    Use the surrounding draft only to judge whether your rewrite fits - never
    as material to pull into the rewrite, and never rewrite or reference any
    part of the draft outside the flag's own original_text.

    Each rewrite must also carry the flag_id of the flag it addresses.

    Respond with ONLY valid JSON, no markdown fences, no preamble, no
    commentary before or after. Match this exact shape, a JSON array with one
    object per flag, in the same order the flags were given:

    [
      {
        "original_text": "the exact quoted_text from the flag, unchanged",
        "rewritten_text": "the improved version of that specific text",
        "reason": "one sentence on what changed and why, in coaching language",
        "flag_id": "the id of the flag this rewrite addresses"
      }
    ]
    """

    user_message = f"""
    Job description:
    {job_description}

    Student's full draft answer (context only - rewrite ONLY the flagged
    text below, nothing else in this draft):
    {draft_answer}

    Flags:
    {json.dumps([f.model_dump() if hasattr(f, "model_dump") else f for f in flags])}

    Matched exemplars:
    {json.dumps([e.model_dump() for e in exemplars])}
    """

    result = call_claude_json(
        system_prompt, user_message, max_tokens=REWRITE_MAX_TOKENS, expect=list, deadline=deadline
    )
    for r in result:
        if not isinstance(r, dict):
            raise PipelineError(f"Rewrite agent returned a {type(r).__name__} in its list, expected an object.")

    try:
        rewrites = [RewriteSuggestion(**r) for r in result]
    except (ValidationError, TypeError) as e:
        logger.error("Rewrite response didn't match RewriteSuggestion: %s", e)
        raise PipelineError("The feedback service returned unexpected rewrites. Try again.") from e

    # The frontend pairs rewrites to flags on flag_id and renders nothing when
    # the lookup misses, so a hallucinated id degrades to a silently missing
    # rewrite. Not worth failing the whole request over - the flag itself is
    # still useful - but it must not vanish without a trace.
    known_ids = {flag.id for flag in flags}
    unmatched = [r.flag_id for r in rewrites if r.flag_id not in known_ids]
    if unmatched:
        logger.warning(
            "Rewrite agent returned flag_ids that match no flag: %s (known ids: %s)",
            unmatched,
            sorted(known_ids),
        )
    missing = sorted(known_ids - {r.flag_id for r in rewrites})
    if missing:
        logger.warning("No rewrite returned for flags: %s", missing)

    return rewrites
