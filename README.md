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

## Build log

TODO: keep this updated as you go. This is the part that turns into your
interview answers later, so treat it as worth the five minutes each time.

Things worth recording:
- decisions you made and why (e.g. "why four separate agents instead of
  one prompt")
- things that didn't work and what you changed
- what real users said, and what you changed because of it
- eval results once you have a test set (which drafts did the diagnostic
  agent get right vs wrong, compared to what a real coach would flag)

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

## Eval notes

TODO: once you have 5-6 real drafts with known "correct" coach verdicts,
track here how the diagnostic agent's flags compare. This is what turns
"I built an AI tool" into "I built an AI tool and measured whether it works."
