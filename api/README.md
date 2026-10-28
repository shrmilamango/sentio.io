# Sentio.io — Backend API

FastAPI + PostgreSQL backend for aspect-based sentiment analysis of code-mixed
Hinglish food delivery reviews. See the main [README](../README.md) for the whole project.

## Setup

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      (put your Postgres password in .env)
```

Create the database once (pgAdmin or psql): `CREATE DATABASE sentio;`
Tables and the seven aspect rows are created automatically on first start.

## Run

```
python -m uvicorn app.main:app --reload
```

Interactive docs: http://localhost:8000/docs

- `USE_FAKE_MODEL=False` (default in `.env.example`): predictions come from the trained
  model service, `ML/serve.py` on port 8001 — start that first.
- `USE_FAKE_MODEL=True`: a keyword placeholder (`app/fake_model.py`), no model needed.

## Endpoints

| Method | Path | Login | Purpose |
|---|---|---|---|
| GET  | `/health` | no | Service check |
| POST | `/v1/auth/register` | no | Create an account (bcrypt-hashed password) |
| POST | `/v1/auth/login` | no | Returns a JWT (60 min) |
| GET  | `/v1/auth/me` | yes | Current user |
| POST | `/v1/analyze` | no | Analyse one review |
| GET  | `/v1/reviews` | yes | Paginated history |
| GET  | `/v1/reviews/{id}` | yes | One full analysis |
| GET  | `/v1/insights/summary` | yes | Dashboard aggregates |
| GET  | `/v1/models` | no | Model versions and their test scores |

Protected routes need the header `Authorization: Bearer <token>`.
In `/docs`: log in, copy `access_token`, click **Authorize**, paste it.

## Layout

```
app/
├── config.py      settings, read from .env
├── database.py    engine + session
├── models.py      SQLAlchemy tables (users, reviews, analyses, aspects, aspect_results, model_versions)
├── schemas.py     request/response shapes — the API contract
├── auth.py        password hashing, JWT, route protection
├── ml_client.py   calls the model service
├── fake_model.py  keyword placeholder
└── main.py        routes
seed.py            loads 12 sample reviews
```
