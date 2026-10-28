# Deploying Sentio.io for free

```
 Browser ──► Vercel (React frontend) ──► Render (FastAPI backend) ──► ngrok ──► your laptop (model, port 8001)
                                              │
                                              └──► Neon (PostgreSQL)
```

Everything is on a free plan. The model (1.1 GB) is too big for free cloud servers,
so it keeps running on your laptop and ngrok gives it a fixed public address.
**The public site only gets model predictions while your laptop is on and the model service + ngrok are running.**

You create the accounts yourself (GitHub, Neon, ngrok, Render, Vercel). Keep every
password, token and connection string out of git — they only go in the dashboards / `.env`.

---

## 1. GitHub
Push the project to a **private** repository (the datasets contain real users' review text).
In VS Code: Source Control → **Publish to GitHub** → choose **private**.

## 2. Database — Neon
1. Sign up at neon.com → **Create project** (region: Singapore / Asia is closest).
2. Copy the **connection string** (`postgresql://...neon.tech/neondb?sslmode=require`).
   Paste it as-is later — the backend converts it automatically.
Tables are created automatically the first time the backend starts.

## 3. Model — your laptop + ngrok
1. Sign up at ngrok.com. In the dashboard open **Domains** and note your free domain
   (looks like `something-something.ngrok-free.app`).
2. Install ngrok (dashboard → Setup & Installation → Windows), then once:
   `ngrok config add-authtoken <your token>`
3. In VS Code start **Sentio model service (port 8001)**.
4. In a terminal: `ngrok http 8001 --url=https://YOUR-DOMAIN.ngrok-free.app`
5. Check: open `https://YOUR-DOMAIN.ngrok-free.app/health` — it should say
   "Bad or missing X-Sentio-Token". That is correct: the model only answers your backend.
   (VS Code starts the model service with a secret `ML_SERVICE_TOKEN`; the value is in
   `.vscode/ML_SERVICE_TOKEN.txt`, which is never committed.)

## 4. Backend — Render
1. Sign up at render.com with GitHub → **New → Blueprint** → pick the repo.
   It reads `render.yaml` and creates `sentio-api` on the free plan.
2. Fill in when asked:
   - `DATABASE_URL` = Neon connection string
   - `ML_SERVICE_URL` = `https://YOUR-DOMAIN.ngrok-free.app`
   - `ML_SERVICE_TOKEN` = the value in `.vscode/ML_SERVICE_TOKEN.txt`
   - `FRONTEND_ORIGINS` = leave `http://localhost:5173` for now (update in step 5)
3. Wait for the deploy, then open `https://sentio-api.onrender.com/docs` (your exact URL is
   shown in the dashboard). `/health` should say `"fake_model": false`.

## 5. Frontend — Vercel
1. Sign up at vercel.com with GitHub → **Add New → Project** → pick the repo.
2. **Root Directory:** `frontend` (Vercel detects Vite automatically).
3. **Environment Variable:** `VITE_API_URL = https://sentio-api.onrender.com` (your Render URL) → Deploy.
4. Copy the Vercel URL (e.g. `https://sentio.vercel.app`) and add it on Render:
   `FRONTEND_ORIGINS = http://localhost:5173,https://sentio.vercel.app` → Save (Render redeploys).

`frontend/vercel.json` is already there, so refreshing /dashboard or /history works.

---

## Before every demo
1. Laptop on and online.
2. VS Code → start **Sentio model service (port 8001)**.
3. Terminal → `ngrok http 8001 --url=https://YOUR-DOMAIN.ngrok-free.app`
4. Open the Render `/health` URL once and wait — **free Render servers sleep after
   15 minutes without traffic and take about a minute to wake up.**
5. Open the Vercel site.

If the laptop is off, analysing returns "model service unavailable". To keep the
site working without the laptop, set `USE_FAKE_MODEL=True` on Render (keyword placeholder).

## Free-plan limits worth knowing
- Render free: 512 MB RAM, sleeps after 15 min idle, 750 hours/month.
- ngrok free: 20,000 requests and 1 GB data per month — plenty for a project demo.
- The model service only answers requests carrying `ML_SERVICE_TOKEN`, so the ngrok
  address alone is useless to strangers. Still, stop ngrok when you're not presenting.
