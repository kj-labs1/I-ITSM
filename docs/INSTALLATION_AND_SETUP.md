# Installation & Environment Configuration Guide

This guide covers complete setup instructions for local development, testing, and production container builds.

---

## 1. System Requirements

- **Operating System:** macOS, Linux, or Windows WSL2
- **Python:** 3.12 or higher (tested on Python 3.12 and Python 3.14)
- **Node.js:** v18.0.0 or higher
- **PostgreSQL:** Version 16 or higher
- **Docker & Docker Compose:** (Optional, recommended for database orchestration)

---

## 2. Environment Variables Specification

The backend reads configuration from environment variables or a local `.env` file located in `backend/.env`.

| Variable | Type | Default | Description |
|---|---|---|---|
| `APP_NAME` | string | `I-ITSM` | Application name. |
| `APP_VERSION` | string | `0.1.0` | Application version. |
| `APP_ENV` | string | `development` | Runtime environment (`development`, `production`, `testing`). |
| `DEBUG` | boolean | `true` | Enables FastAPI debug logs and verbose exceptions. |
| `DATABASE_URL` | string | `postgresql+psycopg://postgres:postgres@localhost:5432/iitsm` | Async SQLAlchemy database connection URL. |
| `DATABASE_ECHO` | boolean | `false` | Echo raw SQL queries to stdout. |
| `JWT_SECRET_KEY` | string | `insecure-dev-secret-change-in-production-min-32-chars` | Secret key for signing JWTs. |
| `JWT_ALGORITHM` | string | `HS256` | JWT signing algorithm. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | integer | `60` | JWT expiration duration in minutes. |
| `CORS_ORIGINS` | list | `["http://localhost:3000", "http://127.0.0.1:3000"]` | Allowed frontend origins. |
| `LLM_PROVIDER` | string | `mock` | Recommendation provider: `mock` (offline) or `openai_compatible`. |
| `LLM_API_KEY` | string | `""` | API key for external LLM provider. |
| `LLM_BASE_URL` | string | `https://api.openai.com/v1` | Base URL for OpenAI-compatible endpoint. |
| `LLM_MODEL` | string | `gpt-4o-mini` | LLM model identifier. |

---

## 3. Step-by-Step Local Setup

### 3.1 Clone the Repository
```bash
git clone https://github.com/kj-labs1/I-ITSM.git
cd I-ITSM
```

### 3.2 Database Initialization
You can run a local PostgreSQL server or launch one via Docker Compose:
```bash
docker compose up -d db
```

### 3.3 Backend Setup & Migrations
```bash
cd backend

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies in editable mode
pip install --upgrade pip
pip install -e ".[dev]"

# Create local environment file
cp .env.example .env

# Run Alembic migrations to create tables up to revision 006
alembic upgrade head

# Start Uvicorn development server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- Swagger UI available at [http://localhost:8000/docs](http://localhost:8000/docs).
- Health check available at [http://localhost:8000/health](http://localhost:8000/health).

### 3.4 Frontend Setup
In a separate terminal:
```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev -- --port 3000
```
- Access the web application at [http://localhost:3000](http://localhost:3000).

---

## 4. Docker Compose Production Build

To run the entire multi-container stack:
```bash
docker compose up --build -d
```
Starts:
- `db`: PostgreSQL 16 container on port 5432.
- `backend`: FastAPI Uvicorn container on port 8000.
