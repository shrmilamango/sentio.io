# Sentio.io — Frontend

React + Vite + Tailwind. Pages: landing (with a live analyser), analyse, sign in / register,
dashboard and history.

## Run locally

```
npm install
npm run dev          (http://localhost:5173)
```
The backend must be running on http://localhost:8000 — the dev server forwards `/v1/...` calls
to it, so no extra setup is needed. For a deployed backend, set `VITE_API_URL` (see `.env.example`).

## Build / deploy

`npm run build` writes the site to `dist/`. On Vercel: root directory `frontend`, framework
Vite, environment variable `VITE_API_URL` = your backend URL. `vercel.json` makes page
refreshes on /dashboard etc. work.

## Design

| Token | Value | Used for |
|---|---|---|
| paper | `#FBFAF7` | page background |
| ink | `#1C1A17` | text |
| indigo | `#1F2A5C` | dark bands, links, logo |
| haldi | `#F2B632` | primary buttons |
| leaf / chilli / slate | `#2F7D4F` / `#C8412E` / `#8A8F98` | positive / negative / neutral only |

Fonts: Tiro Devanagari Hindi (headlines, reviews) and Mukta (interface) — both cover Latin
and Devanagari, so Hinglish in either script renders properly. Bundled via @fontsource.
