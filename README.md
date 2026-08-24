<h1 align="center">Resume Matcher</h1>

<p align="center">
  Find the jobs that actually fit your CV — searched, scored and explained on your own machine.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white">
  <img alt="React" src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white">
  <img alt="Ollama" src="https://img.shields.io/badge/Ollama-local%20LLM-black">
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white">
</p>

![The Resume Matcher workspace: setup on the left, ranked jobs in the middle, analysis and chat on the right](docs/workspace.png)

Add your resume, say what you are looking for, and one button searches public job
boards, scores every posting against your CV, and explains the fit. Your resume and
every match stay in a SQLite file on your machine, and the analysis is written by an
LLM running locally.

|  |  |
|---|---|
| **Hybrid scoring** | Semantic embeddings blended with keyword and skill overlap |
| **Online discovery** | Live postings from six public job board APIs, four needing no key |
| **Local LLM analysis** | Ollama writes the strengths and gaps, then answers follow-ups |
| **Local-first** | Nothing leaves the machine except the search terms you type |

<img align="right" width="330" alt="The analysis panel: an LLM breakdown of strengths and gaps, with a follow-up conversation below it" src="docs/analysis.png">

### Why it is not just keyword search

A keyword filter cannot tell you that six years of FastAPI answers a posting asking
for "strong backend focus". Two signals are blended instead: the cosine distance
between embeddings of your resume and the posting, and the overlap of concrete
skills and keywords. Each result shows both, so a high score with weak keyword
overlap reads differently from the reverse.

Click any result and a local model explains the match — what lines up, what is
missing, and what to change. Ask follow-ups in the panel and it answers with the
job description and your resume already in context.

<br clear="right">

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python, FastAPI, SQLite |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`, local CPU) |
| LLM | Ollama (`llama3.1:8b`) |
| Frontend | Vite, React, TypeScript, TanStack Query |
| Parsing | PyMuPDF (PDF), python-docx (DOCX), plain-text paste |

## Quick start

### Prerequisites

- **Python 3.11+** and **Node.js 18+**
- **Ollama** running locally (optional — ranking works without it, analysis falls back
  to a rule-based summary):

  ```bash
  ollama pull llama3.1:8b
  ollama serve
  ```

### Setup

From the repository root:

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

```bash
cd frontend
npm install
```

### Run

On Windows, `scripts/start-dev.ps1` launches both servers. Otherwise use two terminals:

```bash
cd backend && .venv/Scripts/activate && python -m uvicorn app.main:app --reload --port 8010
```

```bash
cd frontend && npm run dev
```

| URL | What |
|-----|------|
| http://localhost:5273 | Web app |
| http://localhost:8010/docs | Interactive API docs |
| http://localhost:8010/health | Status and model config |

> On Windows the `--reload` watcher can miss changes. If an edit does not seem to
> take effect, restart the backend.

## Using it

1. Add your **resume** — upload a PDF/DOCX or paste the text
2. Set what you want: role, experience level, city, country, remote-only, how many
   postings to pull, and a minimum match score
3. Click **Find & rank jobs online**

That is the only ranking action. It searches the boards, scores every result against
your resume, writes an analysis for the top few, and links straight to each posting.

Then click any result for its **analysis**, ask **follow-up questions** in the chat
panel, or **Export .md** to save the report.

**One resume at a time.** Adding another replaces it, clears the rankings the previous
one produced, and deletes the old copy — except where a saved session still refers to it.

**The job library** holds postings you add by hand plus everything past searches pulled
in. Hand-added jobs are ranked alongside every search, so a posting you found yourself
is scored too. Previously discovered jobs stay for their apply links but are not
re-ranked, so each search returns fresh results rather than resurfacing stale ones.

**Saved sessions** keep the 5 most recent runs; older ones are deleted along with their
results and chat history.

> Screenshots use a made-up resume and invented postings, not real data.

## Job sources

| Source | API key | Covers |
|--------|---------|--------|
| Remotive | no | Remote roles |
| RemoteOK | no | Remote roles |
| Arbeitnow | no | EU roles, including onsite |
| Jobicy | no | Remote roles |
| JSearch | free tier | Google for Jobs — **Malaysia**, Asia, worldwide |
| Adzuna | free tier | Onsite and remote across 18 countries (**not Malaysia**) |

The four keyless boards work with no setup but are remote-focused.

**For Malaysian or Asian listings, use JSearch.** It reads Google for Jobs, so it
surfaces JobStreet, LinkedIn and Indeed postings. Subscribe to the free tier on
[RapidAPI](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) and set
`JSEARCH_API_KEY` in `backend/.env`.

Adzuna serves 18 countries — Singapore yes, Malaysia no. Choosing a country it does
not cover says so plainly rather than quietly returning another country's jobs.

These are official public APIs, not scraped pages. LinkedIn and Indeed block automated
access and their terms forbid it, so they are not scraped directly. A failing board is
skipped rather than failing the whole search.

Postings are filtered for relevance to your keywords — weighted toward the job title,
since boards match free text loosely — before your resume is scored against them.

## How scoring works

```
overall        = 0.6 x semantic_similarity + 0.4 x keyword_blend
keyword_blend  = 0.6 x skill_overlap + 0.4 x keyword_overlap
```

Semantic similarity is the cosine distance between embeddings of the resume and the
posting. Scores are on a 0–100 scale. Weights are configurable in `backend/.env`.

## Configuration

All settings live in `backend/.env` (see `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `llama3.1:8b` | Model used for analysis and chat |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `EMBEDDING_DEVICE` | `cpu` | Set `cuda` if you have a supported GPU |
| `SEMANTIC_WEIGHT` / `KEYWORD_WEIGHT` | `0.6` / `0.4` | Score blend, must sum to 1.0 |
| `DATABASE_PATH` | `./data/resume_matcher.db` | SQLite file |
| `UPLOAD_DIR` | `./data/uploads` | Stored uploads |
| `JSEARCH_API_KEY` | empty | Enables the JSearch source |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | empty | Enables the Adzuna source |

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Status and model config |
| `POST /documents/upload` | Upload a PDF/DOCX resume or job |
| `POST /documents/text` | Add a resume or job as plain text |
| `GET /documents/jobs?origin=` | List jobs — `manual`, `discovered` or `all` |
| `DELETE /documents/{id}` | Remove a document |
| `GET /discover/sources` | Which boards exist and which are configured |
| `POST /discover/match` | Search boards and rank against a resume |
| `POST /discover/match/stream` | Same, streamed with progress (used by the UI) |
| `GET /sessions` | List saved runs |
| `GET /sessions/{id}` | Reload a run |
| `GET /sessions/{id}/export` | Download the run as markdown |
| `GET /chat/{session_id}` | Chat history |
| `POST /chat` | Ask a follow-up about a match |

## Project layout

```text
resume-matcher/
├── backend/
│   ├── app/
│   │   ├── main.py         # App setup, /health
│   │   ├── config.py       # Settings from .env
│   │   ├── db.py           # SQLite schema, migrations, queries
│   │   ├── schemas.py      # Shared request/response models
│   │   ├── routes/         # documents, discover, sessions, chat
│   │   ├── sources/        # One module per job board, behind a shared adapter
│   │   ├── matching/       # Embeddings, keyword overlap, hybrid score
│   │   ├── explain/        # Ollama prompts + offline fallback
│   │   ├── parsers/        # PDF/DOCX text extraction and skill parsing
│   │   └── services/       # Markdown export
│   ├── fixtures/           # Sample resume and job used by tests
│   └── tests/
├── frontend/
│   └── src/
│       ├── App.tsx         # Layout, health pill, saved sessions
│       ├── components/     # Resume input, search panel, library, results, chat
│       ├── lib/api.ts      # Typed API client, including the SSE reader
│       └── types/api.ts    # Response types mirroring the backend schemas
└── scripts/                # start-dev.ps1
```

## Development

```bash
cd backend && .venv/Scripts/activate && pytest -q     # 29 tests
cd frontend && npm run lint && npx tsc --noEmit       # lint + typecheck
cd frontend && npm run build                          # production build
```

Adding a job board means writing one module in `backend/app/sources/` exposing
`NAME`, `LABEL`, `REQUIRES_KEY`, `is_available()` and `fetch(client, query)`, then
listing it in `registry.MODULES`. Relevance filtering, deduplication, error handling
and concurrency are handled for you.

## Notes

The first search downloads the embedding model (~90MB) and is slower than the rest.
After that, scoring a batch of postings takes a few seconds on CPU; the analysis step
is usually what you are waiting for.
