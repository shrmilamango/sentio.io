// Talks to the FastAPI backend.
// Local dev: leave VITE_API_URL unset - Vite forwards /v1 to http://localhost:8000.
// Deployed: set VITE_API_URL to the backend URL (e.g. the Render URL).
export const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

const TOKEN_KEY = "sentio_token";

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function setToken(token) {
  try { token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY); } catch { /* storage blocked */ }
}

export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

function messageFor(status, detail) {
  if (status === 0) return "Can't reach the server. Check that the backend is running.";
  if (status === 429) return "Too many tries in a short time. Please wait a few minutes and try again.";
  if (status === 502) return "The model gave an unexpected answer. Try again in a moment.";
  if (status === 503) return "Analysis is offline right now — the model service isn't running. Try again in a minute.";
  if (status === 401) return typeof detail === "string" && detail !== "Not authenticated" ? detail : "Please sign in to see this.";
  if (status === 422 && Array.isArray(detail)) {
    const d = detail[0];
    if (d?.loc?.includes("texts")) return (d.msg || "Some reviews aren't valid.").replace(/^Value error, /, "").replace(/^./, (c) => c.toUpperCase()) + ".";
    if (d?.loc?.includes("text")) return "Type a review first (up to 2,000 characters).";
    if (d?.loc?.includes("username")) return "Username must be 3–30 letters, numbers or underscores.";
    if (d?.loc?.includes("password")) return "Password must be at least 8 characters.";
    return d?.msg || "Some details aren't valid.";
  }
  return typeof detail === "string" ? detail : "Something went wrong. Try again.";
}

async function request(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const t = getToken();
    if (t) headers.Authorization = `Bearer ${t}`;
  }
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw new ApiError(0, messageFor(0));
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && auth) setToken(null);
    throw new ApiError(res.status, messageFor(res.status, data?.detail));
  }
  return data;
}

export const api = {
  // sends the token when signed in, so the review is saved to that user's history
  analyzeBatch: (texts) => request("/v1/analyze/batch", { method: "POST", body: { texts }, auth: true }),
  analyze: (text) => request("/v1/analyze", { method: "POST", body: { text }, auth: true }),
  register: (username, password, full_name) =>
    request("/v1/auth/register", { method: "POST", body: { username, password, full_name: full_name || null } }),
  login: (username, password) => request("/v1/auth/login", { method: "POST", body: { username, password } }),
  me: () => request("/v1/auth/me", { auth: true }),
  reviews: ({ page = 1, pageSize = 20, polarity } = {}) =>
    request(`/v1/reviews?page=${page}&page_size=${pageSize}${polarity ? `&polarity=${polarity}` : ""}`, { auth: true }),
  review: (id) => request(`/v1/reviews/${id}`, { auth: true }),
  insights: () => request("/v1/insights/summary", { auth: true }),
  models: () => request("/v1/models"),
  feedback: (analysisId, body) => request(`/v1/analyses/${analysisId}/feedback`, { method: "POST", body, auth: true }),
};
