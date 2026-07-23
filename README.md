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

TODO once you're ready:
- Backend: Render web service, root directory `backend/`, start command
  `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Frontend: Render static site, root directory `frontend/`, build command
  `npm install && npm run build`, publish directory `frontend/dist`
- Set `ANTHROPIC_API_KEY` as an environment variable in the Render dashboard,
  not in code
- Set `VITE_BACKEND_URL` to the deployed backend URL when building the
  frontend (it defaults to http://localhost:8000 for local dev)
- Update `allow_origins` in `backend/main.py` to your deployed frontend URL
  instead of `"*"`

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

- [date] — TODO

## Eval notes

TODO: once you have 5-6 real drafts with known "correct" coach verdicts,
track here how the diagnostic agent's flags compare. This is what turns
"I built an AI tool" into "I built an AI tool and measured whether it works."
