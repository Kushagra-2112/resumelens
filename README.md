# AI-Driven Resume Screening System for Recruitment

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B)](https://streamlit.io/)
[![Supabase](https://img.shields.io/badge/Auth%20%26%20DB-Supabase-3FCF8E)](https://supabase.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

An AI-powered resume screening platform that replaces rigid ATS keyword matching with semantic similarity, explicit skill validation, and a transparent, decomposed scoring engine.

Instead of returning a single opaque match percentage, the system scores every resume out of 100 across five interpretable components (formatting, keyword relevance, content quality, skill validation, ATS compatibility) that sum arithmetically to the final score, and pairs it with severity-ranked, actionable feedback.

---

## Table of Contents

- [Why This Project](#why-this-project)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running the App](#running-the-app)
- [API Overview](#api-overview)
- [Scoring Methodology](#scoring-methodology)
- [Results](#results)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Authors](#authors)
- [License](#license)

---

## Why This Project

Conventional Applicant Tracking Systems filter resumes by exact keyword overlap. This causes two well-documented failure modes:

- **False negatives** — a resume that says "developed REST APIs" gets rejected against a job description asking for "building backend web services," even though they describe the same skill.
- **False positives** — a candidate who lists a technology once in a skills section, with no supporting project or experience, matches just as strongly as someone who has used it for years.

This system addresses both by scoring meaning instead of words, and by verifying that every claimed skill is backed by evidence elsewhere in the resume.

## Features

- **Multi-format parsing** — PDF, DOC, DOCX, validated by magic-byte inspection rather than file extension.
- **LLM-based structured extraction** — contact info, summary, skills, education, projects, and experience parsed via an LLM (Groq / Llama 3), with JSON-schema validation and automatic retry on malformed output.
- **Semantic matching** — Sentence-BERT (`all-mpnet-base-v2`) embeddings and spaCy NER, compared via cosine similarity instead of keyword overlap.
- **Skill validation engine** — every claimed skill is checked against project/experience text (fast substring check first, semantic similarity fallback) to catch keyword stuffing.
- **Transparent, additive scoring (out of 100)** — five weighted components sum directly to the final score, so results are independently verifiable.
- **AI-generated feedback** — severity-ranked, actionable suggestions across ten issue categories, each with a rewritten example.
- **Bulk / recruiter mode** — upload multiple resumes against one job description; concurrency-capped, per-file fault-isolated batch scoring with a ranked shortlist.
- **Authentication and persistence** — Supabase Auth (JWT) with PostgreSQL storage of past analyses.
- **Downloadable reports** — HTML-to-PDF report generation via Jinja2 and WeasyPrint.

## Architecture

```
                     ┌─────────────────────────┐
   Resume + JD ────▶ │   Streamlit Frontend     │
                     │ (login, upload, results) │
                     └────────────┬────────────┘
                                  │ JWT
                     ┌────────────▼────────────┐
                     │      Supabase Auth       │
                     └────────────┬────────────┘
                                  │
                     ┌────────────▼────────────┐
                     │      FastAPI Backend      │
                     └──┬─────────┬─────────┬───┘
                        │         │         │
              ┌─────────▼──┐ ┌────▼─────┐ ┌─▼───────────────┐
              │   Text     │ │   LLM    │ │  NLP Embeddings  │
              │ Extraction │ │ Parsing  │ │ (spaCy + SBERT)  │
              │(pdfplumber)│ │ (Groq)   │ │                  │
              └─────────┬──┘ └────┬─────┘ └─┬────────────────┘
                        └─────────┼──────────┘
                             ┌────▼─────┐
                             │  Scoring  │
                             │  Engine   │
                             │ (ATS/100) │
                             └──┬─────┬──┘
                     ┌──────────▼──┐ ┌▼───────────────┐
                     │ Supabase DB │ │ PDF Generation  │
                     │ (persist)   │ │  (WeasyPrint)   │
                     └──────────┬──┘ └┬────────────────┘
                                └──┬──┘
                          ┌────────▼────────┐
                          │ Results shown in │
                          │    frontend      │
                          └──────────────────┘
```

### Nine-Stage Processing Pipeline

1. Upload resume and job description
2. Extract raw text (`pdfplumber` / `python-docx`)
3. Validate file type and integrity — reject with HTTP 422/400 if invalid
4. LLM-based structured parsing (Groq API)
5. Entity detection (spaCy NER + Sentence-BERT embeddings)
6. Skill validation (keyword and semantic match vs. job description)
7. Weighted scoring engine — produces ATS score out of 100
8. LLM feedback generation (prioritized, actionable suggestions)
9. Persist to database and return response (JSON or downloadable PDF)

### Bulk Screening Flow

The same single-resume pipeline is reused as a subroutine, so no logic is duplicated:

```
Recruiter uploads N resumes + 1 job description
        |
        v
Create batch job record
        |
        v
Concurrency-capped dispatch (semaphore, 3 at a time)
        |
        v
Each resume scored independently; failures isolated
        |
        v
Aggregate results, rank by score, persist, return shortlist
```

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| Frontend | Streamlit | Upload UI, results dashboard, auth forms |
| Backend | FastAPI, Uvicorn, Pydantic | REST API, request/response validation |
| Document Parsing | pdfplumber, PyPDF2, python-docx, python-magic | Text extraction and true file-type detection |
| NLP and Matching | spaCy (`en_core_web_md`), Sentence Transformers, RapidFuzz | Entity recognition, semantic embeddings, fuzzy matching |
| Language Model | Groq API (Llama 3) | Structured parsing and feedback generation |
| Auth | Supabase Auth, PyJWT | Token issuance and stateless verification |
| Database | Supabase (PostgreSQL), httpx | Persistent storage of analyses and batch results |
| Reporting | Jinja2, WeasyPrint | HTML templating and PDF report generation |

## Project Structure

Adjust to match your actual repository layout — this reflects the architecture above.

```
resume-screening-system/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entrypoint
│   │   ├── api/                    # Route definitions (analyze, batch, auth)
│   │   ├── core/                   # Config, settings, security
│   │   ├── parsing/                # pdfplumber / python-docx extraction
│   │   ├── llm/                    # Groq API client, prompt templates
│   │   ├── nlp/                    # spaCy NER + Sentence-BERT embeddings
│   │   ├── scoring/                # Weighted scoring engine
│   │   ├── feedback/               # Issue detection & suggestion generation
│   │   ├── batch/                  # Bulk screening / concurrency dispatch
│   │   ├── reports/                # Jinja2 templates + WeasyPrint PDF export
│   │   └── db/                     # Supabase/Postgres models & queries
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── streamlit_app.py            # Streamlit entrypoint
│   └── pages/                      # Upload, results, batch dashboard
├── docs/
│   └── thesis/                     # Project thesis & diagrams
├── .env.example
├── LICENSE
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+
- A [Supabase](https://supabase.com/) project (Auth + PostgreSQL)
- A [Groq API](https://console.groq.com/) key (LLM parsing and feedback)
- `pip` and a virtual environment tool (`venv`, `conda`, etc.)

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/resume-screening-system.git
cd resume-screening-system

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_md

# Frontend setup
cd ../frontend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in `backend/` (see `.env.example`):

```env
# Groq (LLM parsing & feedback generation)
GROQ_API_KEY=your_groq_api_key

# Supabase (auth + database)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# JWT
JWT_SECRET=your_jwt_secret

# App config
MAX_UPLOAD_SIZE_MB=10
BULK_CONCURRENCY_LIMIT=3
```

### Running the App

```bash
# Terminal 1 — backend (from /backend)
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend (from /frontend)
streamlit run streamlit_app.py
```

| Service | URL |
|---|---|
| Streamlit UI | `http://localhost:8501` |
| FastAPI Swagger docs | `http://localhost:8000/docs` |

## API Overview

| Endpoint | Method | Description |
|---|---|---|
| `/auth/login` | POST | Authenticate and issue a JWT |
| `/analyze` | POST | Upload a single resume (+ optional JD) and get a scored analysis |
| `/analyze/{id}/report` | GET | Download the PDF report for a past analysis |
| `/batch/analyze` | POST | Upload multiple resumes + one JD for bulk screening |
| `/batch/{batch_id}` | GET | Retrieve ranked results for a batch job |
| `/history` | GET | List a user's past analyses |

Exact routes depend on your implementation — see the auto-generated Swagger docs at `/docs` once the backend is running.

## Scoring Methodology

The overall score (0–100) is the direct sum of five weighted components, plus small bonuses and penalties, so the headline figure is fully reproducible from its parts.

| Component | Max | What It Measures |
|---|---|---|
| Formatting | 20 | Section structure, bullet usage, summary length |
| Keyword Relevance | 25 | Semantic (not lexical) coverage of job-description terms |
| Content Quality | 25 | Action verbs, quantified achievements |
| Skill Validation | 15 | Percentage of claimed skills substantiated in projects/experience |
| ATS Compatibility | 15 | Parseability, absence of layout constructs that defeat parsers |

Bonuses: 80% or higher skill validation rate; zero detected grammar errors.
Penalty: graduated deduction when a large share of job-description keywords are missing from the resume.

Score bands: below 50 = Poor, 50–69 = Fair, 70–89 = Good, 90 and above = Excellent.

## Results

Validated on a cleaned dataset of 284 resume-to-job-description pairs:

- A correlation of 0.827 between computed Sentence-BERT similarity and human-assigned match labels.
- Clear separation across tiers — mean similarity: High 0.809, Medium 0.636, Low 0.511.
- Baseline embedding model MAE of 0.19 on held-out test data; raw similarity was found to systematically over-estimate weak matches, confirming the need for the multi-component design rather than a single similarity score.
- On a representative real resume: strong surface scores (formatting 19/20, keywords 23/25, ATS 15/15) but only 5/15 on skill validation — just 13 of 41 claimed skills were substantiated. Final score: 81/100 — a false positive that a keyword-only ATS would have missed.

## Limitations

- English-language, text-extractable resumes only (no OCR for scanned documents yet).
- No active demographic bias auditing or mitigation is implemented.
- Validation dataset (284 pairs) supports relationship analysis, not model training.
- Embedding model is used pre-trained; fine-tuning was attempted but not completed.

## Roadmap

- Fine-tune the sentence embedding model on domain-specific resume-to-job-description pairs.
- Bias-auditing dashboard, starting with name/pronoun redaction for name-blind scoring.
- OCR support for scanned or image-based resumes.
- Multilingual resume and job-description support.
- Domain-specific skill ontology for equivalent-skill recognition.
- Public API for third-party ATS/HRMS integration and a mobile-friendly recruiter interface.

## Contributing

Contributions, issues, and feature requests are welcome.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push to the branch and open a pull request

## License

This project is licensed under the MIT License — see the [LICENSE](./LICENSE) file for the full text.
