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

export async function analyze(body: AnalyzeRequest): Promise<FinalReport> {
  const response = await fetch(`${BACKEND_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

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
