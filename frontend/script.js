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
const submitButton = document.getElementById("submit-button");

let reportState = null;   // the full FinalReport from the last successful fetch
let currentSlide = 0;     // 0 = summary, 1..N = flags[0..N-1]

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
  reportState = null;
  loadingEl.style.display = "block";
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

  } catch (error) {
    console.error("Analyze request failed:", error);
    reportEl.innerHTML = `<p class="error-message">Something went wrong: ${escapeHtml(error.message)}</p>`;
  } finally {
    loadingEl.style.display = "none";
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

function buildSummaryContentHtml(context) {
  return `
    <div class="summary">
      <div class="summary-label">This question is looking for:</div>
      <p class="summary-role-focus">${escapeHtml(context.role_focus)}</p>
      <p>${escapeHtml(context.question_intent)}</p>
      <ul>
        ${context.what_strong_answer_needs.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </div>
  `;
}

function buildNavHtml(totalFlags, current) {
  const dots = [
    `<button type="button" class="carousel-dot ${current === 0 ? "active" : ""}" data-action="jump" data-slide-index="0">Summary</button>`,
  ];
  for (let i = 1; i <= totalFlags; i++) {
    dots.push(
      `<button type="button" class="carousel-dot ${current === i ? "active" : ""}" data-action="jump" data-slide-index="${i}">Flag ${i}</button>`
    );
  }
  return `<div class="carousel-nav">${dots.join("")}</div>`;
}

function buildSummarySlideHtml(context) {
  return `
    ${buildSummaryContentHtml(context)}
    <div class="carousel-controls">
      <span></span>
      <button type="button" class="carousel-button" data-action="next">View flags</button>
    </div>
  `;
}

function buildFlagSlideHtml(flag, rewrites, slideIndex, totalFlags) {
  const rewrite = rewrites.find((r) => r.original_text === flag.quoted_text);

  const rewriteHtml = rewrite ? `
    <div class="flag-rewrite">
      <div class="rewrite-label">Suggested rewrite</div>
      <p class="rewrite-text">${escapeHtml(rewrite.rewritten_text)}</p>
      <p class="rewrite-reason">${escapeHtml(rewrite.reason)}</p>
    </div>
  ` : "";

  const isLast = slideIndex === totalFlags;

  return `
    <div class="flag-card" data-dimension="${escapeHtml(flag.dimension)}">
      <div class="flag-dimension">Flag ${slideIndex} of ${totalFlags} — ${escapeHtml(dimensionLabel(flag.dimension))}</div>
      <blockquote class="flag-quote">${escapeHtml(flag.quoted_text)}</blockquote>
      <p class="flag-reason">${escapeHtml(flag.reason)}</p>
      ${rewriteHtml}
    </div>
    <div class="carousel-controls">
      <button type="button" class="carousel-button" data-action="prev">Previous</button>
      ${isLast ? "<span></span>" : `<button type="button" class="carousel-button" data-action="next">Next flag</button>`}
    </div>
  `;
}

function renderSlide() {
  const { context, flags, rewrites } = reportState;

  if (flags.length === 0) {
    reportEl.innerHTML = buildSummaryContentHtml(context) + `<p class="no-flags">No issues found - nice work.</p>`;
    return;
  }

  const navHtml = buildNavHtml(flags.length, currentSlide);
  const slideHtml = currentSlide === 0
    ? buildSummarySlideHtml(context)
    : buildFlagSlideHtml(flags[currentSlide - 1], rewrites, currentSlide, flags.length);

  reportEl.innerHTML = navHtml + slideHtml;
}

reportEl.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");
  if (!target || !reportState) return;

  const totalFlags = reportState.flags.length;

  if (target.dataset.action === "next") {
    currentSlide = Math.min(currentSlide + 1, totalFlags);
  } else if (target.dataset.action === "prev") {
    currentSlide = Math.max(currentSlide - 1, 0);
  } else if (target.dataset.action === "jump") {
    currentSlide = Number(target.dataset.slideIndex);
  }

  renderSlide();
});
