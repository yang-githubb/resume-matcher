# Resume Matcher

Local-first resume ↔ job matcher with **hybrid scoring** (semantic embeddings + keyword overlap), **SQLite persistence**, **Ollama explanations + follow-up chat**, and **online job discovery** that pulls live postings from public job boards and ranks them against your resume.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python, FastAPI, SQLite |
| Embeddings | `sentence-transformers` (local CPU) |
| LLM | Ollama (`llama3.1:8b`) — uses **9070 XT** GPU when Ollama is running |
| Frontend | Vite + React + TypeScript + TanStack Query |
| Parsing | PyMuPDF (PDF), python-docx (DOCX), plain text paste |

## How to run

### Prerequisites

1. **Python 3.11+** and **Node.js 18+**
2. **Ollama** installed and running:
   ```powershell
   ollama pull llama3.1:8b
   ollama serve
   ```

### One-time setup

```powershell
cd c:\Users\Yang5\Documents\CodeProject\resume-matcher\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

cd ..\frontend
npm install
```

### Start everything (easiest)

```powershell
cd c:\Users\Yang5\Documents\CodeProject\resume-matcher\scripts
.\start-dev.ps1
```

Then open **http://localhost:5173**

### Manual start (two terminals)

**Terminal 1 — API**
```powershell
cd c:\Users\Yang5\Documents\CodeProject\resume-matcher\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — UI**
```powershell
cd c:\Users\Yang5\Documents\CodeProject\resume-matcher\frontend
npm run dev
```

| URL | What |
|-----|------|
| http://localhost:5173 | Web app |
| http://localhost:8000/docs | API docs |
| http://localhost:8000/health | Health check |

### Demo without UI (sample fixtures)

```powershell
cd c:\Users\Yang5\Documents\CodeProject\resume-matcher\scripts
.\demo-cli.bat
```

Or with explanations (needs Ollama):
```powershell
cd backend
python cli.py --job fixtures\sample_job.txt --resumes fixtures\sample_resume_strong.txt fixtures\sample_resume_weak.txt
```

### Run tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest -q
```

## Find jobs online

Instead of pasting postings by hand, **Find jobs online** collects your preferences
first (role, experience level, city, country, remote-only, how many to pull, minimum
match), then queries public job boards, ranks every result against your resume, and
links straight to the posting.

| Source | Key needed | Covers |
|--------|-----------|--------|
| Remotive | no | Remote roles |
| RemoteOK | no | Remote roles |
| Arbeitnow | no | EU roles (incl. onsite) |
| Jobicy | no | Remote roles |
| JSearch | yes (free) | Google for Jobs — **Malaysia** + Asia, worldwide |
| Adzuna | yes (free) | Onsite + remote, 18 countries (**no Malaysia**) |

The four keyless boards work with no setup, but they are remote-focused.

**For Malaysian / Asian listings, use JSearch.** It reads Google for Jobs, so it
surfaces JobStreet, LinkedIn and Indeed postings. Subscribe to the free JSearch tier
on [RapidAPI](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) and set
`JSEARCH_API_KEY` in `backend/.env`.

Adzuna covers 18 countries — Singapore yes, **Malaysia no**. Picking an unsupported
country reports that plainly rather than quietly returning another country's jobs.

These are official public APIs, not scraped pages — LinkedIn and Indeed block
automated access and their terms forbid it, so they are deliberately not included.
Postings are filtered for relevance to your keywords (title-weighted) before your
resume is scored against them.

## Using the app

1. Pick **Job seeker** or **Recruiter** mode
2. Add a **job** (file or paste), or use **Find jobs online**
3. Add **1–2 resumes** (file or paste per slot)
4. Click **Rank matches**
5. Click a result for **analysis**
6. Ask **follow-up questions** in the chat panel
7. **Export .md** to save the report
8. Reload past runs from **Saved sessions**

Ranking works without Ollama. Analysis falls back to a rule-based summary if Ollama is offline.

## Hybrid score

```
overall = 0.6 × semantic_similarity + 0.4 × keyword_blend
keyword_blend = 0.6 × skill_overlap + 0.4 × keyword_overlap
```

Tune in `backend/.env`.

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Status + model config |
| `POST /documents/upload` | Upload PDF/DOCX |
| `POST /documents/text` | Paste plain text |
| `PATCH /documents/{id}` | Edit extracted text |
| `GET /discover/sources` | List job boards + which are configured |
| `POST /discover/match` | Search boards by preferences, rank against a resume |
| `POST /match/rank` | Rank up to 2 resumes |
| `GET /match/sessions/{id}` | Load session |
| `GET /match/sessions/{id}/export` | Download markdown report |
| `GET /sessions` | List saved sessions |
| `GET /chat/{session_id}` | Chat history |
| `POST /chat` | Follow-up message |

## Project layout

```text
resume-matcher/
├── backend/
│   ├── app/           # FastAPI app
│   │   └── sources/   # Job board adapters (one module per board)
│   ├── fixtures/      # Sample job + resumes
│   ├── tests/
│   └── cli.py
├── frontend/          # Vite + React UI
└── scripts/           # start-dev.ps1, demo-cli.bat
```

## First-run note

The first match downloads the embedding model (`all-MiniLM-L6-v2`, ~90MB). After that, matching 1–2 resumes is fast on CPU.
