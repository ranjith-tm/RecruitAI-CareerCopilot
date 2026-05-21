# RecruitAI — Your Career Copilot

**Multi-agent AI career assistant powered by LangGraph — analyze resumes, predict interviews, rewrite bullets, close skill gaps, and generate cover letters in one API call.**

Built with a production-grade FastAPI backend and a zero-dependency vanilla JS frontend. Supports OpenAI and Groq providers interchangeably.

---

## What It Does

Upload a resume (PDF or plain text), provide a job description, and RecruitAI runs a coordinated pipeline of 8 specialized AI agents that each contribute a slice of the analysis. The result is a comprehensive JSON payload covering every dimension of career readiness.

| Agent | Output |
|---|---|
| `resume_parser` | Candidate profile: name, email, location, years of experience, education |
| `skills_extractor` | Classified skills: technical, soft, domain expertise |
| `ats_scorer` | ATS score (0–100), keyword density, readability, missing keywords |
| `interview_predictor` | Interview probability, breakdown by dimension, strengths & weaknesses |
| `resume_rewriter` | Bullet-by-bullet rewrites with improvement notes |
| `skill_gap_analyzer` | Critical vs nice-to-have gaps, learning recommendations |
| `cover_letter_generator` | Role-tailored cover letter |
| `job_matcher` | Ranked job matches with per-role skill alignment scores |

---

## Architecture

```
POST /api/analyze
        │
        ▼
  FastAPI router
        │
        ▼
  ThreadPoolExecutor  ──►  LangGraph StateGraph
                                    │
                              ┌─────▼──────┐
                              │resume_parser│
                              └─────┬───────┘
                                    │
                           ┌────────▼────────┐
                           │skills_extractor  │
                           └────────┬─────────┘
                                    │ conditional
                          ┌─────────┴──────────┐
                          │                    │
                    ┌─────▼──────┐      ┌──────▼─────┐
                    │ ats_scorer │      │job_matcher  │
                    └─────┬──────┘      └──────┬──────┘
                          │ conditional         │
                   ┌──────▼──────┐             │
                   │  job_matcher│◄────────────┘
                   └──────┬──────┘
                          │ conditional
                  ┌────────▼────────────────────────────┐
                  │interview_predictor                   │
                  │   → resume_rewriter                  │
                  │     → skill_gap_analyzer             │
                  │       → cover_letter_generator → END │
                  └──────────────────────────────────────┘
```

The graph has three conditional branches:
- **Resume only** → parse + extract skills → END
- **Resume + multiple JDs** → parse → extract → rank jobs → END
- **Resume + primary JD** → full 8-node pipeline → END (job matching inserted inline if additional JDs are present)

The LangGraph `StateGraph` passes a single `RecruitAIState` TypedDict through every node. Pipeline metadata fields (`completed_steps`, `errors`, `log`) use `Annotated[List, operator.add]` reducers so nodes append rather than overwrite.

---

## Project Structure

```
RecruitAI/
├── main.py                          # FastAPI app, mounts static frontend
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── app/
│   ├── config/settings.py           # Pydantic BaseSettings, env-driven config
│   ├── routers/
│   │   ├── analysis.py              # POST /api/analyze (multipart form)
│   │   └── health.py                # GET /health
│   ├── schemas/models.py            # Full Pydantic request/response models
│   ├── services/analysis_service.py # Async bridge → ThreadPoolExecutor → LangGraph
│   └── utils/pdf_utils.py           # pdfplumber PDF text extraction
│
├── recruitai/                       # Core LangGraph package
│   ├── graph.py                     # StateGraph builder + conditional routing
│   ├── state.py                     # RecruitAIState TypedDict
│   ├── config.py                    # LLM factory (OpenAI / Groq)
│   └── agents/
│       ├── resume_parser.py
│       ├── skills_extractor.py
│       ├── ats_scorer.py
│       ├── interview_predictor.py
│       ├── resume_rewriter.py
│       ├── skill_gap.py
│       ├── cover_letter.py
│       └── job_matcher.py
│
└── frontend/
    ├── index.html                   # SPA — dark glassmorphism UI
    └── static/
        ├── style.css
        └── app.js                   # Vanilla JS: fetch API, drag-and-drop, tabs
```

---

## API Reference

### `POST /api/analyze`

Accepts `multipart/form-data`.

| Field | Type | Required | Description |
|---|---|---|---|
| `resume_file` | File (PDF) | * one of these | Resume as PDF upload |
| `resume_text` | string | * one of these | Resume as plain text |
| `job_description` | string | No | Primary JD — triggers full analysis pipeline |
| `job_descriptions` | JSON string (array) | No | Additional JDs for multi-job ranking |
| `target_role` | string | No | Overrides inferred role for cover letter |
| `provider` | `openai` \| `groq` | No | Default: `groq` |
| `model` | string | No | Overrides default model for chosen provider |
| `api_key` | string | No | Overrides server-side env var |

**Response `200`**
```json
{
  "success": true,
  "message": "Analysis complete",
  "data": {
    "profile": {
      "name": "Jane Doe",
      "years_of_experience": 4.5,
      "technical_skills": ["Python", "FastAPI", "Docker"]
    },
    "ats": {
      "score": 82.5,
      "missing_keywords": ["Kubernetes", "CI/CD"],
      "keyword_density": 0.034,
      "readability_score": 91.0
    },
    "interview": {
      "probability": 0.71,
      "strengths": ["Strong Python fundamentals", "Relevant domain experience"],
      "weaknesses": ["No cloud certifications mentioned"]
    },
    "resume_bullets": [
      {
        "original": "Worked on backend services",
        "rewritten": "Designed and shipped 3 microservices handling 50K req/day using FastAPI and PostgreSQL",
        "improvement_note": "Added metrics, ownership, and impact"
      }
    ],
    "skill_gaps": {
      "critical": ["Kubernetes", "Terraform"],
      "nice_to_have": ["GraphQL"],
      "learning_recommendations": [{ "skill": "Kubernetes", "resource": "CKA course on Linux Foundation" }]
    },
    "cover_letter": "Dear Hiring Manager...",
    "job_rankings": [
      { "rank": 1, "title": "Senior Backend Engineer", "match_score": 0.88, "matched_skills": ["Python", "FastAPI"] }
    ],
    "completed_steps": ["resume_parser", "skills_extractor", "ats_scorer", "interview_predictor",
                        "resume_rewriter", "skill_gap_analyzer", "cover_letter_generator"]
  }
}
```

### `GET /health`
```json
{ "status": "ok", "version": "2.0.0", "providers": ["openai", "groq"] }
```

Interactive docs: `/docs` (Swagger UI) · `/redoc` (ReDoc)

---

## LLM Providers

| Provider | Default Model | Env Var | Alternatives |
|---|---|---|---|
| `openai` | `gpt-4o-mini` | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4-turbo` |
| `groq` | `llama-3.3-70b-versatile` | `GROQ_API_KEY` | `llama-3.1-8b-instant`, `mixtral-8x7b-32768` |

Provider and model are overridable per-request via form fields — no server restart needed.

---

## Local Development

**Prerequisites:** Python 3.11+, `uv` (or pip)

```bash
# 1. Clone
git clone https://github.com/your-username/RecruitAI.git
cd RecruitAI

# 2. Install
uv pip install -r requirements.txt
# or: pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env — add OPENAI_API_KEY or GROQ_API_KEY

# 4. Run
uv run uvicorn main:app --reload
# or: python main.py
```

App: `http://localhost:8000`  
API docs: `http://localhost:8000/docs`

---

## Docker

```bash
# Start (builds image on first run)
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

The container exposes port `8000`, auto-restarts on failure (`restart: unless-stopped`), and includes a built-in health check polling `GET /health` every 30 seconds.

---

## Deploy to AWS EC2

**1. Launch instance** — Ubuntu 24.04, t3.small minimum. Open port `8000` inbound in the security group.

**2. Install Docker**
```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu && exit   # re-login after
```

**3. Clone and configure**
```bash
git clone https://github.com/your-username/RecruitAI.git
cd RecruitAI
nano .env    # add OPENAI_API_KEY or GROQ_API_KEY
```

**4. Run**
```bash
docker-compose up --build -d
```

**5. Access** — `http://<ec2-public-ip>:8000`

> For HTTPS on port 443, put Nginx + Certbot in front and proxy to `localhost:8000`.

---

## Environment Variables

```env
# At least one LLM provider key is required
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...

# Optional — these all have defaults
DEFAULT_PROVIDER=groq
DEFAULT_MODEL=llama-3.3-70b-versatile
DEBUG=false
MAX_PDF_SIZE_MB=10
CORS_ORIGINS=["*"]
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph 1.2+ (StateGraph, conditional edges, append reducers) |
| LLM abstraction | LangChain Core, `langchain-openai`, `langchain-groq` |
| API server | FastAPI 0.110+ + Uvicorn |
| Data validation | Pydantic v2 + pydantic-settings |
| PDF parsing | pdfplumber |
| Frontend | Vanilla HTML/CSS/JS — zero runtime dependencies |
| Containerization | Docker + Docker Compose |
| Python | 3.11+ |

---

## License

MIT
