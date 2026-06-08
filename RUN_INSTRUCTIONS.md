# Run Instructions — Test Case Generator

Prerequisites
- macOS / Linux (instructions use bash/zsh)
- Python 3.10+ (venv)
- Node.js + npm (for frontend)

Environment
- Create a `.env` file at the repository root with at least:
  - `JIRA_INSTANCE_URL` (e.g. https://your-org.atlassian.net)
  - `JIRA_USERNAME`
  - `JIRA_API_TOKEN`
  - `GROK_API_KEY` or `OPENAI_API_KEY` (if using OpenAI/Grok)

Backend (Python)
1. Create & activate virtual environment

```bash
cd /path/to/ai-agent-langgraph
python -m venv .venv
source .venv/bin/activate
```

2. Install Python dependencies

```bash
# If there is a requirements.txt
pip install -r requirements.txt
# Ensure essential packages are present (safe to run again)
pip install uvicorn fastapi python-dotenv requests httpx urllib3 langchain-openai langchain-core
```

3. Start the backend (development)

```bash
# from repo root
source .venv/bin/activate
python -m uvicorn backend:app --reload --port 8000
```

Notes:
- The backend will try to serve the React production build from `test-case-generator-ui/build` if present.
- If you see warnings about missing build, run the frontend dev server or build the frontend (see below).

Frontend (React / Vite)
1. Install npm deps and run dev server

```bash
cd test-case-generator-ui
npm install
npm run dev
```

- Vite dev server defaults to http://localhost:3000/
- To create a production build (optional):

```bash
npm run build
# then the backend can serve the static files from test-case-generator-ui/build
```

Common troubleshooting
- "No module named ..." → activate `.venv` then `pip install <package>` (e.g. `pip install httpx`)
- Port in use (8000/3000) → find/kill process: `lsof -ti:8000 | xargs kill -9`
- SSL / corporate proxy: some code disables SSL verification; only do this in trusted dev environments.

Quick summary (copy/paste)

```bash
# Backend
cd /path/to/ai-agent-langgraph
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn backend:app --reload --port 8000

# Frontend (separate terminal)
cd /path/to/ai-agent-langgraph/test-case-generator-ui
npm install
npm run dev
```

If you want, I can also:
- Add a `requirements.txt` / update it from the installed packages
- Run the backend & frontend here and verify the UI (I already started them earlier)

File locations
- Backend entry: backend.py
- Frontend app: test-case-generator-ui/

