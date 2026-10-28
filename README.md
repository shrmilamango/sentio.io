# Sentio.io

**Aspect-based sentiment analysis for code-mixed Hinglish food delivery reviews.**

Paste a review like *"Khana bahut tasty tha par delivery boy rude tha"* and Sentio.io returns
the overall sentiment **and** a separate verdict for each part of the order it mentions:

| Aspect | Verdict |
|---|---|
| Food quality | positive |
| Delivery partner | negative |

A star rating gives one number per review. Sentio.io shows *what* customers are happy or
unhappy about.

---

## Contents

1. [Features](#features)
2. [How it works](#how-it-works)
3. [Results](#results)
4. [Tech stack](#tech-stack)
5. [Project structure](#project-structure)
6. [Run it locally](#run-it-locally)
7. [API](#api)
8. [Testing](#testing)
9. [Security](#security)
10. [Deployment](#deployment)
11. [Authors](#authors)

---

## Features

- **Seven aspects:** delivery time, food quality, packaging, delivery partner, app experience,
  price & offers, refund & support — each rated positive, negative or neutral.
- **Reads Hinglish natively:** Hindi in English letters, English, Devanagari and emoji in one sentence.
- **Explainable:** underlines the phrase behind each aspect and shows which words influenced the model.
- **Accounts:** sign up, keep a private history, and see a dashboard of what your reviews complain about.
- **Language mix:** shows how much of each review is English, Romanised Hindi or Devanagari.

## How it works

```
Browser (React)  ──►  Backend API (FastAPI)  ──►  Model service (FastAPI + PyTorch)
                           │                         HingRoBERTa, 8 output heads
                           ▼
                      PostgreSQL
                (users, reviews, results)
```

1. **Collect** — 240,000+ Play Store and Google Maps reviews of food and grocery apps,
   filtered down to genuinely code-mixed Hinglish.
2. **Label** — 2,291 reviews labelled by hand (overall sentiment + 7 aspects).
   Inter-annotator agreement: **Cohen's κ = 0.83** on a shared set of 200.
3. **Train** — five models fine-tuned and compared on the same frozen test split.
4. **Serve** — the best model (HingRoBERTa) runs as its own service; the backend stores every
   result and builds the dashboard.

## Results

Frozen test set of 277 reviews the models never saw during training:

| Model | Overall macro-F1 | Accuracy |
|---|---|---|
| Always "negative" (baseline) | 0.304 | 0.838 |
| TF-IDF + Logistic Regression | 0.670 | 0.859 |
| mBERT | 0.635 | — |
| XLM-RoBERTa | 0.598 | — |
| **HingRoBERTa (deployed)** | **0.817** | **0.921** |

HingRoBERTa also scores **0.71 F1** for detecting which aspects a review mentions and
**0.69 F1** for the sentiment of each aspect. With only 45 positive and neutral reviews in the
test set, the 95 % bootstrap interval for macro-F1 is 0.73–0.88.

Full comparison, per-aspect scores and notes: [ML/results/RESULTS.md](ML/results/RESULTS.md)

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | React 18, Vite 6, Tailwind CSS, React Router 7 |
| Backend | FastAPI, SQLAlchemy 2, PostgreSQL, JWT (PyJWT), bcrypt |
| Model | PyTorch, Hugging Face Transformers, `l3cube-pune/hing-roberta` |
| Data & evaluation | pandas, scikit-learn, google-play-scraper |
| Hosting (free) | Vercel (site), Render (API), Neon (database), ngrok (model) |

## Project structure

```
sentio.io/
├── frontend/                 React website
│   └── src/
│       ├── pages/            Landing, Analyse, Sign in / Register, Dashboard, History
│       ├── components/       Result view, annotated review text, layout
│       └── lib/              API client, login state, aspect names and colours
│
├── api/                      FastAPI backend
│   ├── app/
│   │   ├── main.py           routes
│   │   ├── auth.py           password hashing, login tokens, route protection
│   │   ├── models.py         database tables
│   │   ├── schemas.py        request / response shapes
│   │   ├── ml_client.py      calls the model service
│   │   ├── ratelimit.py      limits on logins, sign-ups and analyses
│   │   ├── config.py         settings from .env
│   │   ├── database.py       database connection
│   │   └── fake_model.py     keyword placeholder (runs without the model)
│   ├── tests/                58 automated tests
│   └── seed.py               loads sample reviews
│
├── ML/                       Training, evaluation and the model service
│   ├── split_dataset.py      v1 → train / val / test (70 / 15 / 15, test frozen)
│   ├── build_v2.py           v2 = v1 + new reviews, same frozen test set
│   ├── baseline.py           TF-IDF + Logistic Regression
│   ├── train.py              fine-tunes any transformer (overall + 7 aspect heads)
│   ├── compare_results.py    builds the comparison table
│   ├── serve.py              model service (port 8001)
│   ├── colab/                notebook used for Google Colab GPU runs
│   └── results/              scores, predictions, RESULTS.md
│
├── Dataset/
│   ├── sentio_dataset_v1.csv 1,844 labelled reviews
│   ├── sentio_dataset_v2.csv 2,291 labelled reviews (final)
│   ├── annotation/           annotation sheets, κ round and report, excluded rows
│   └── *.py                  scraping, filtering and agreement scripts
│
├── render.yaml               backend deployment settings (Render)
└── DEPLOY.md                 step-by-step free deployment guide
```

Not in the repository (see `.gitignore`): `.env` files, trained model weights
(`ML/models/`, 1.1 GB), raw scraped data, virtual environments and `node_modules`.

## Run it locally

**Requirements:** Python 3.12, Node.js 20+, PostgreSQL. An NVIDIA GPU is optional.

### 1. Database
Create a PostgreSQL database named `sentio`. Tables are created automatically on first start.

### 2. Backend
```bash
cd api
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # then set your PostgreSQL password and a JWT_SECRET
```

### 3. Model service
```bash
cd ML
python setup_ml_env.py           # creates ML\venv and installs PyTorch for your GPU or CPU
```
The trained model belongs in `ML/models/hingroberta_local_v2/`. To recreate it:
```bash
python train.py --model l3cube-pune/hing-roberta --tag hingroberta_local_v2 --splits splits_v2
```
No model? Set `USE_FAKE_MODEL=True` in `api/.env` to use a keyword placeholder.

### 4. Frontend
```bash
cd frontend
npm install
```

### 5. Start
In VS Code → **Run and Debug**, start these in order:

1. **Sentio model service (port 8001)**
2. **Sentio API (uvicorn)** — API docs at http://localhost:8000/docs
3. **Sentio frontend (port 5173)** — open **http://localhost:5173**

Or from terminals:
```bash
cd ML  && venv\Scripts\python serve.py --tag hingroberta_local_v2
cd api && venv\Scripts\python -m uvicorn app.main:app --reload
cd frontend && npm run dev
```

## API

| Method | Path | Login | Purpose |
|---|---|---|---|
| GET | `/health` | no | Service check |
| POST | `/v1/auth/register` | no | Create an account |
| POST | `/v1/auth/login` | no | Get a login token (valid 60 min) |
| GET | `/v1/auth/me` | yes | Current user |
| POST | `/v1/analyze` | no | Analyse one review (saved to your history when signed in) |
| GET | `/v1/reviews` | yes | Your reviews, paginated, filter by sentiment |
| GET | `/v1/reviews/{id}` | yes | One full result |
| GET | `/v1/insights/summary` | yes | Dashboard totals |
| GET | `/v1/models` | no | Model versions and test scores |

Protected routes need `Authorization: Bearer <token>`. Interactive docs: `/docs`.

## Testing

```bash
cd api
venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest -q
```
58 tests covering login, analysis, history, dashboard, input validation, error handling and
the security protections below. They use a temporary database, so your data is never touched.

## Security

- Passwords stored only as bcrypt hashes; login tokens are signed and expire after 60 minutes.
- Each user can see only their own reviews, history and dashboard.
- Rate limits on failed logins, sign-ups and analyses.
- The model service only answers requests carrying a shared secret (`ML_SERVICE_TOKEN`).
- Security headers on the API and the site, strict CORS, input length limits.
- Secrets live only in `.env` files and hosting dashboards — never in the repository.
- Dependencies checked with `pip-audit` and `npm audit`.

## Deployment

Everything runs on free plans. Step-by-step guide: **[DEPLOY.md](DEPLOY.md)**.

## Authors

Shyam Sundar Prajapati · Shreya Singh · Shivman Vadwan
