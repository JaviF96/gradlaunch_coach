// script.js
//
// Handles the form submit: sends the three inputs to the backend,
// and renders whatever comes back. index.html supplies the static
// shell (empty state, loading skeleton); everything else is built here.

// ============================================================
// Config
// ============================================================

// TODO: replace with your deployed backend URL once you deploy.
// Keep it as localhost while you're building locally.
const BACKEND_URL = "http://localhost:8000";

const DIMENSION_LABELS = {
  star_structure: "STAR structure",
  specificity: "Specificity",
  voice_authenticity: "Voice authenticity",
  trajectory_signal: "Trajectory signal",
  generic_phrasing: "Generic phrasing",
};

// ============================================================
// DOM references and state
// ============================================================

const form = document.getElementById("analyze-form");
const loadingEl = document.getElementById("loading");
const reportEl = document.getElementById("report");
const submitButton = document.getElementById("submit-button");

let reportState = null;   // the full FinalReport from the last successful fetch
let currentSlide = 0;     // 0 = summary, 1..N = flags[0..N-1]

// ============================================================
// Character counters
// ============================================================

for (const fieldId of ["job-description", "question", "draft-answer"]) {
  const field = document.getElementById(fieldId);
  const counter = document.getElementById(`${fieldId}-count`);
  const update = () => {
    counter.textContent = `${field.value.length} / ${field.maxLength}`;
  };
  field.addEventListener("input", update);
  update();
}

// ============================================================
// Submit → API call
// ============================================================

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const jobDescription = document.getElementById("job-description").value;
  const question = document.getElementById("question").value;
  const draftAnswer = document.getElementById("draft-answer").value;

  reportEl.innerHTML = "";
  reportState = null;
  loadingEl.hidden = false;
  submitButton.disabled = true;

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
    reportState = report;
    currentSlide = 0;
    renderSlide();
    reportEl.focus();

  } catch (error) {
    console.error("Analyze request failed:", error);
    const message = error instanceof TypeError
      ? "The feedback service couldn't be reached. Check the backend is running, then try again."
      : error.message;
    reportEl.innerHTML = `
      <div class="gl-flag gl-flag--critical">
        <span class="gl-flag-tag">Error</span>
        <p>${escapeHtml(message)}</p>
      </div>
    `;
  } finally {
    loadingEl.hidden = true;
    submitButton.disabled = false;
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

// ============================================================
// Renderers
// ============================================================

function buildSummaryContentHtml(context) {
  return `
    <article class="gl-flag gl-flag--note">
      <span class="gl-flag-tag">Question brief</span>
      <p class="summary-role">${escapeHtml(context.role_focus)}</p>
      <p>${escapeHtml(context.question_intent)}</p>
      <span class="gl-label summary-needs-label">A strong answer needs</span>
      <ul class="summary-needs">
        ${context.what_strong_answer_needs.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </article>
  `;
}

function buildNavHtml(totalFlags, current) {
  const dots = [navDotHtml(0, "Summary", current)];
  for (let i = 1; i <= totalFlags; i++) {
    dots.push(navDotHtml(i, `Flag ${i}`, current));
  }
  return `<nav class="carousel-nav" aria-label="Report sections">${dots.join("")}</nav>`;
}

function navDotHtml(index, label, current) {
  const active = index === current;
  return `<button type="button"
    class="carousel-dot${active ? " is-active" : ""}"
    data-action="jump" data-slide-index="${index}"
    ${active ? 'aria-current="true"' : ""}>${label}</button>`;
}

function buildSummarySlideHtml(context) {
  return `
    ${buildSummaryContentHtml(context)}
    <div class="carousel-controls">
      <span></span>
      <button type="button" class="gl-btn-secondary" data-action="next">View flags</button>
    </div>
  `;
}

function buildFlagSlideHtml(flag, rewrites, slideIndex, totalFlags) {
  const rewrite = rewrites.find((r) => r.original_text === flag.quoted_text);

  const rewriteHtml = rewrite ? `
    <div class="flag-rewrite">
      <span class="gl-label">Suggested rewrite</span>
      <p class="rewrite-text">${escapeHtml(rewrite.rewritten_text)}</p>
      <p class="rewrite-reason">${escapeHtml(rewrite.reason)}</p>
    </div>
  ` : "";

  const isLast = slideIndex === totalFlags;

  return `
    <article class="gl-flag gl-flag--attention">
      <div class="flag-head">
        <span class="gl-flag-tag">${escapeHtml(dimensionLabel(flag.dimension))}</span>
        <span class="flag-meta">Flag ${slideIndex} of ${totalFlags}</span>
      </div>
      <blockquote class="flag-quote">${escapeHtml(flag.quoted_text)}</blockquote>
      <p class="flag-reason">${escapeHtml(flag.reason)}</p>
      ${rewriteHtml}
    </article>
    <div class="carousel-controls">
      <button type="button" class="gl-btn-secondary" data-action="prev">Previous</button>
      ${isLast ? "<span></span>" : `<button type="button" class="gl-btn-secondary" data-action="next">Next flag</button>`}
    </div>
  `;
}

function renderSlide() {
  const { context, flags, rewrites } = reportState;

  if (flags.length === 0) {
    reportEl.innerHTML = buildSummaryContentHtml(context) + `
      <div class="gl-flag gl-flag--strength">
        <span class="gl-flag-tag">No flags</span>
        <p>Nothing here needs fixing — the draft already covers what the question is looking for.</p>
      </div>
    `;
    return;
  }

  const navHtml = buildNavHtml(flags.length, currentSlide);
  const slideHtml = currentSlide === 0
    ? buildSummarySlideHtml(context)
    : buildFlagSlideHtml(flags[currentSlide - 1], rewrites, currentSlide, flags.length);

  reportEl.innerHTML = navHtml + slideHtml;
}

// ============================================================
// Carousel navigation
// ============================================================

reportEl.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");
  if (!target || !reportState) return;

  const action = target.dataset.action;
  const totalFlags = reportState.flags.length;

  if (action === "next") {
    currentSlide = Math.min(currentSlide + 1, totalFlags);
  } else if (action === "prev") {
    currentSlide = Math.max(currentSlide - 1, 0);
  } else if (action === "jump") {
    currentSlide = Number(target.dataset.slideIndex);
  }

  renderSlide();

  // innerHTML replacement drops keyboard focus to <body>; restore it to
  // the equivalent control in the fresh DOM.
  const focusTarget =
    reportEl.querySelector(`.carousel-controls [data-action="${action}"]`) ||
    reportEl.querySelector(".carousel-dot.is-active");
  if (focusTarget) focusTarget.focus();
});
