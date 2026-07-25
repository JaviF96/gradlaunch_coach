// The network boundary. The request and response shapes here are the
// backend's contract — do not change field names or the fetch shape
// without changing backend/schemas.py to match.

const BACKEND_URL: string =
  import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8000";

export interface ContextBrief {
  role_focus: string;
  question_intent: string;
  what_strong_answer_needs: string[];
}

export interface Flag {
  dimension: string;
  quoted_text: string;
  reason: string;
  id: string;
}

export interface Rewrite {
  original_text: string;
  rewritten_text: string;
  reason: string;
  flag_id: string;
}

export interface FinalReport {
  context: ContextBrief;
  flags: Flag[];
  rewrites: Rewrite[];
}

export interface AnalyzeRequest {
  job_description: string;
  question: string;
  draft_answer: string;
}

// Sits deliberately above the backend's own PIPELINE_BUDGET_SECONDS (150s in
// agents.py) so the backend almost always wins the race and the user gets its
// specific error instead of a bare client-side abort. This is the last-resort
// stop for a connection that dies without the backend ever replying.
const REQUEST_TIMEOUT_MS = 165_000;

export async function analyze(body: AnalyzeRequest): Promise<FinalReport> {
  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (error) {
    // An aborted fetch throws a DOMException named "TimeoutError", whose own
    // message ("signal timed out") means nothing to a student. Everything
    // else - a genuine network failure throws TypeError - passes through so
    // App.tsx can still tell the two apart.
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new Error(
        "The request timed out after " +
          Math.round(REQUEST_TIMEOUT_MS / 1000) +
          " seconds. The feedback service may be overloaded — try again in a moment.",
      );
    }
    throw error;
  }

  if (!response.ok) {
    throw new Error(await extractErrorMessage(response));
  }

  return (await response.json()) as FinalReport;
}

// FastAPI sends `detail` as a plain string for its own HTTPExceptions
// (429 rate limit, 502 pipeline failure), but as a list of {msg, ...}
// objects for automatic 422 validation errors — handle both rather than
// dumping raw JSON at the user.
async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail.map((d: { msg: string }) => d.msg).join("; ");
    }
  } catch {
    // response wasn't JSON - fall through to the generic message below
  }
  return `Request failed (${response.status})`;
}
