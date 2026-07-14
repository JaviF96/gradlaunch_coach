// script.js
//
// Handles the form submit: sends the three inputs to the backend,
// and renders whatever comes back.

// TODO: replace with your deployed backend URL once you deploy.
// Keep it as localhost while you're building locally.
const BACKEND_URL = "http://localhost:8000";

const form = document.getElementById("analyze-form");
const loadingEl = document.getElementById("loading");
const reportEl = document.getElementById("report");

const DIMENSION_LABELS = {
  star_structure: "STAR structure",
  specificity: "Specificity",
  voice_authenticity: "Voice authenticity",
  trajectory_signal: "Trajectory signal",
  generic_phrasing: "Generic phrasing",
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const jobDescription = document.getElementById("job-description").value;
  const question = document.getElementById("question").value;
  const draftAnswer = document.getElementById("draft-answer").value;

  reportEl.innerHTML = "";
  loadingEl.style.display = "block";

  try {
    const response = await fetch(`${BACKEND_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_description: jobDescription,
        question: question,
        draft_answer: draftAnswer,
      }),
    });

    if (!response.ok) {
      throw new Error(await extractErrorMessage(response));
    }

    const report = await response.json();
    renderReport(report);

  } catch (error) {
    console.error("Analyze request failed:", error);
    reportEl.innerHTML = `<p class="error-message">Something went wrong: ${escapeHtml(error.message)}</p>`;
  } finally {
    loadingEl.style.display = "none";
  }
});


// Parses a failed response's body into a readable message. FastAPI sends
// `detail` as a plain string for our own HTTPExceptions (429, 502), but as
// a list of {msg, ...} objects for automatic 422 validation errors - handle
// both rather than dumping raw JSON at the user.
async function extractErrorMessage(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail.map((d) => d.msg).join("; ");
    }
  } catch {
    // response wasn't JSON - fall through to the generic message below
  }
  return `Request failed (${response.status})`;
}

// Escapes text before it's interpolated into innerHTML. quoted_text and
// original_text echo back the student's own submitted draft answer, so
// this isn't just cosmetic - unescaped HTML in a draft answer would
// otherwise execute in the page.
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function dimensionLabel(dimension) {
  return DIMENSION_LABELS[dimension] || dimension.replace(/_/g, " ");
}

function renderReport(report) {
  const { context, flags, rewrites } = report;

  const summaryHtml = `
    <div class="summary">
      <h2>${escapeHtml(context.role_focus)}</h2>
      <p>${escapeHtml(context.question_intent)}</p>
      <ul>
        ${context.what_strong_answer_needs.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </div>
  `;

  if (flags.length === 0) {
    reportEl.innerHTML = summaryHtml + `<p class="no-flags">No issues found - nice work.</p>`;
    return;
  }

  const flagCardsHtml = flags.map((flag) => {
    const rewrite = rewrites.find((r) => r.original_text === flag.quoted_text);

    const rewriteHtml = rewrite ? `
      <div class="flag-rewrite">
        <div class="rewrite-label">Suggested rewrite</div>
        <p class="rewrite-text">${escapeHtml(rewrite.rewritten_text)}</p>
        <p class="rewrite-reason">${escapeHtml(rewrite.reason)}</p>
      </div>
    ` : "";

    return `
      <div class="flag-card" data-dimension="${escapeHtml(flag.dimension)}">
        <div class="flag-dimension">${escapeHtml(dimensionLabel(flag.dimension))}</div>
        <blockquote class="flag-quote">${escapeHtml(flag.quoted_text)}</blockquote>
        <p class="flag-reason">${escapeHtml(flag.reason)}</p>
        ${rewriteHtml}
      </div>
    `;
  }).join("");

  reportEl.innerHTML = summaryHtml + flagCardsHtml;
}
