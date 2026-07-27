# GradLaunch application coach

An agent pipeline that gives structured feedback on a draft application
answer, checked against a real coaching rubric rather than generic AI polish.

## Architecture

Browser form -> FastAPI backend -> four agents run in sequence -> structured
report back to the browser.

1. **Context agent** — reads the job description and question, figures out
   what a strong answer needs
2. **Diagnostic agent** — scores the draft against the rubric, flags issues
3. **Exemplar agent** — pulls a real before/after example for each flag
4. **Rewrite agent** — rewrites only the flagged text, grounded in the exemplar

See `backend/agents.py` for the actual implementation, and `backend/schemas.py`
for the data shapes passing between stages.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # then fill in your real ANTHROPIC_API_KEY
```

Test the pipeline in isolation first, before touching the frontend:

```bash
python test_agents.py
```

Once the agents work, run the backend:

```bash
uvicorn main:app --reload
```

Open http://localhost:8000/docs to test the /analyze endpoint directly.

Then run the frontend (Vite + React, requires Node):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5500 to use the actual form. The dev server is pinned
to port 5500 so it matches the backend's default CORS allowlist.

## Deployment

Live at:
- Frontend: https://gradlaunch-coach-feedback.onrender.com
- Backend: https://gradlaunch-coach.onrender.com

Two separate Render services:
- Backend: Render web service, root directory `backend/`, start command
  `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Frontend: Render static site, root directory `frontend/`, build command
  `npm install && npm run build`, publish directory `frontend/dist`
- `ANTHROPIC_API_KEY` is set as an environment variable on the backend
  service in the Render dashboard, not in code
- `VITE_BACKEND_URL` is set to the backend's URL above, on the frontend
  service in the Render dashboard. This is a **build-time** Vite variable —
  changing it requires a manual redeploy of the frontend, editing local
  `.env` does nothing for the deployed site
- `ALLOWED_ORIGINS` is set to the frontend's URL above, on the backend
  service in the Render dashboard — `backend/main.py` reads it and defaults
  to `http://localhost:5500` if unset (local dev only)

## Build log:

### Entries

- **2026-07-14 — Initial pipeline.** Got the four-agent pipeline (context →
  diagnostic → exemplar → rewrite) working end to end, with a plain
  HTML/CSS/JS frontend. Left the system prompts as deliberate TODOs at
  first — the rubric itself is the actual IP here, worth designing
  carefully rather than scaffolding on autopilot.

- **2026-07-22 — Rate-limit fix, carousel, panel layout.** Ran an audit of
  the codebase and found the rate limiter was keying off
  `request.client.host`, which behind a reverse proxy (e.g. Render) is the
  proxy's own IP for every request — that would have collapsed every user
  into a single shared limit. Fixed it before it could bite anyone, even
  though it wasn't affecting real users yet: cheaper to fix a correctness
  bug on paper than after it's live. Separately, reworked the report view
  from a single flat list that kept growing with every flag into a
  carousel with a left/right split panel layout — a meaningful UX
  improvement once a draft had more than two or three issues to review.

- **2026-07-23 — Rebuilt the frontend on React.** Rewrote the frontend from
  vanilla JS/CSS to Vite + React + TypeScript. This was a deliberate bet
  on a framework to raise the ceiling on how polished the UI could look
  and how maintainable it would stay as more components (carousel, flag
  cards, rewrite blocks) got added.

- **2026-07-25 — Flag IDs, a model switch, and hardening error handling.**
  Realized the diagnostic-to-rewrite pairing was fragile: flags and
  rewrites were being matched by comparing text, so if the model
  paraphrased the rewritten text even slightly, the match would fail
  silently and the rewrite would just vanish from the UI with no error.
  Set myself the task of fixing this properly by having the backend
  assign a stable `flag.id` and threading it through as `flag_id`, so
  pairing no longer depends on the model reproducing text exactly.
  Separately, after comparing output quality, tried switching the model
  from Haiku to Sonnet — which immediately broke JSON parsing, since
  Sonnet returns a thinking block ahead of its text response and Haiku
  doesn't; the code was blindly reading the first content block as text.
  Fixed by filtering to text-type blocks only. A second audit that day
  turned up a bigger risk: the Anthropic SDK's default timeouts and
  retries meant a single hung call could tie up a request for a very long
  time behind a spinner promising 10–20 seconds. Closed that off with
  explicit per-call and per-pipeline timeout budgets, and took the
  opportunity to distinguish failure types (timeout vs. API error vs.
  malformed response) so each one surfaces a clear, specific message
  instead of a generic failure.

- **2026-07-26 — Fixed hallucinated rewrites and overlapping flags.**
  Spent this session focused purely on output quality: put several runs
  side by side and compared what the rewrite agent was actually
  producing. Found it was stating things as fact — outcomes, numbers,
  results — that sounded ideal but that the student had never actually
  confirmed, which is a serious problem for a tool giving application
  advice. Fixed it by having the model insert explicit `[[ADD: ...]]`
  placeholders wherever a rewrite needed a real detail it didn't have,
  instead of inventing one, paired with an explicit instruction never to
  fabricate. Also noticed the diagnostic agent could flag the same
  underlying issue twice under two different dimension names; fixed by
  detecting overlapping flagged text and discarding the less specific
  duplicate.

- **2026-07-26 — First deploy, and a same-origin bug.** Deployed the backend
  as a Render web service and the frontend as a Render static site. First
  live test failed instantly with a JSON parse error in the browser instead
  of a real response. Network tab showed why: a 200 with `Content-Length: 0`
  in 65ms, and the request URL was the frontend's own domain, not the
  backend's — `VITE_BACKEND_URL` had been pointed at the frontend site
  itself, so `/analyze` was hitting Render's static-site edge, not FastAPI,
  which is also why the backend's own logs never showed the request at all.
  Fixed by pointing `VITE_BACKEND_URL` at the actual backend URL and
  rebuilding — worth remembering that Vite bakes this in at build time, so
  editing `.env` alone (local or via Render dashboard) does nothing without
  a redeploy.

- **2026-07-26 — Rewrites losing context after real testing.** Ran a handful
  of real questions through the live deployment and started seeing rewrites
  that didn't actually make sense in place — a rewritten clause substituted
  back into the draft would read as a disconnected, ungrammatical fragment.
  Root cause: the rewrite agent was only ever given the flagged `quoted_text`
  in isolation, never the sentences around it, so it had no way to know
  whether that text was, say, the back half of a sentence introduced by a
  colon. Fixed by passing the full `draft_answer` into `rewrite_agent` for
  context and adding an explicit instruction to treat `rewritten_text` as a
  literal drop-in replacement — check the sentence immediately before and
  after the flag, and keep a dependent clause or list item fitted to that
  same grammatical role instead of turning it into a standalone sentence.
  While investigating, also tightened the diagnostic agent's quoting rules:
  `quoted_text` now has to be one or more complete sentences, never a
  fragment that only parses attached to a neighbor, and a repeated pattern
  (e.g. a templated "Firstly / Secondly / Thirdly" list) gets flagged as one
  span covering every instance instead of just the first.

- **2026-07-27 — Cleanup pass before calling this done.** Went through the
  whole codebase looking for stale comments, dead code, and anything that
  wouldn't hold up in a public repo. Removed a dead `.gl-btn-secondary` CSS
  rule that no component referenced, a stray trailing whitespace in
  `schemas.py`, and the deferred `/explain` TODO in `main.py`. Also stopped
  tracking `.claude/settings.local.json` (local tool permission grants, not
  meant to be shared) and added it to `.gitignore`.

