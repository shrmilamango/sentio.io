import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { EXAMPLES } from "../lib/aspects";
import { Result } from "./Result";

export function AnalyzeBox({ autoFocus = false }) {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { user } = useAuth();

  async function run(value = text) {
    const t = value.trim();
    if (!t) { setError("Type a review first, or pick an example."); return; }
    setBusy(true); setError("");
    try {
      setResult(await api.analyze(t));
    } catch (e) {
      setError(e.message); setResult(null);
    } finally {
      setBusy(false);
    }
  }

  function useExample(ex) { setText(ex); run(ex); }

  return (
    <div>
      <form onSubmit={(e) => { e.preventDefault(); run(); }}>
        <label htmlFor="review" className="sr-only">Review text</label>
        <textarea
          id="review"
          rows={3}
          maxLength={2000}
          autoFocus={autoFocus}
          className="field resize-none font-serif text-xl leading-relaxed"
          placeholder="Paste a review… e.g. order late aaya par khana garam tha"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run(); }}
        />
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Reading…" : "Analyse review"}
          </button>
          <span className="text-sm text-muted">or try:</span>
          {EXAMPLES.map((ex) => (
            <button key={ex} type="button" onClick={() => useExample(ex)} disabled={busy}
              className="rounded-full border border-line bg-white px-3 py-1 text-sm text-muted transition-colors hover:border-ink hover:text-ink">
              {ex.length > 34 ? ex.slice(0, 32) + "…" : ex}
            </button>
          ))}
        </div>
      </form>

      {error && <p role="alert" className="mt-5 rounded-xl bg-chilli-soft px-4 py-3 text-chilli-ink">{error}</p>}

      {result && (
        <div className="mt-10 border-t border-line pt-10" aria-live="polite">
          <Result result={result} />
          {!user && (
            <p className="mt-8 text-sm text-muted">
              <Link to="/login" className="font-medium text-indigo underline underline-offset-4">Sign in</Link> to keep your reviews in your own dashboard.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
