import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { ASPECTS, POLARITY, aspectLabel } from "../lib/aspects";
import { reviewsFromCsv, toCsv } from "../lib/csv";
import { Result, UNSURE_BELOW, VerdictPill } from "../components/Result";

const MAX = 50;
const ORDER = ["negative", "neutral", "positive"];
const SAMPLE = [
  "Khana bahut tasty tha par delivery boy rude tha",
  "Refund 10 din se nahi aaya, support bekar hai",
  "order late aaya aur khana thanda tha",
  "packaging achhi thi aur delivery fast thi",
  "app bar bar crash hota hai, payment fail",
  "price thoda zyada hai lekin taste mast hai",
].join("\n");

const pct = (n, d) => (d ? Math.round((n / d) * 100) : 0);
const isUnsure = (r) => r.confidence < UNSURE_BELOW;

function Verdict({ r }) {
  if (isUnsure(r)) {
    return <span className="inline-flex items-center gap-1.5 rounded-full bg-haldi-soft px-2.5 py-0.5 text-sm font-medium text-ink">? Not sure</span>;
  }
  return <VerdictPill polarity={r.polarity} size="sm" />;
}

function Summary({ results }) {
  const n = results.length;
  const counts = Object.fromEntries(ORDER.map((p) => [p, results.filter((r) => r.polarity === p).length]));
  const unsure = results.filter(isUnsure).length;
  const byAspect = {};
  for (const r of results) for (const a of r.aspects) {
    byAspect[a.aspect] ??= { negative: 0, neutral: 0, positive: 0 };
    byAspect[a.aspect][a.polarity] += 1;
  }
  const aspects = Object.entries(byAspect).sort((a, b) => b[1].negative - a[1].negative);
  const max = Math.max(1, ...aspects.map(([, c]) => c.negative + c.neutral + c.positive));
  const worst = aspects.find(([, c]) => c.negative > 0);

  return (
    <div className="space-y-10">
      <p className="max-w-3xl font-serif text-2xl leading-snug sm:text-3xl">
        {n} {n === 1 ? "review" : "reviews"}: {pct(counts.negative, n)}% negative, {pct(counts.neutral, n)}% neutral, {pct(counts.positive, n)}% positive.
        {worst && <> Most complaints are about <span className="mark mark-neg">{aspectLabel(worst[0]).toLowerCase()}</span>.</>}
      </p>
      {unsure > 0 && (
        <p className="text-muted">{unsure} of them {unsure === 1 ? "is" : "are"} marked “Not sure” and may be sarcastic or indirect.</p>
      )}
      {aspects.length > 0 && (
        <div>
          <h2 className="mb-4 text-2xl">What they talk about</h2>
          <ul className="space-y-4">
            {aspects.map(([key, c]) => {
              const total = c.negative + c.neutral + c.positive;
              return (
                <li key={key}>
                  <div className="mb-1.5 flex justify-between gap-4 text-sm">
                    <span className="font-medium">{aspectLabel(key)}</span>
                    <span className="text-muted">{total} {total === 1 ? "mention" : "mentions"}, {c.negative} negative</span>
                  </div>
                  <div className="flex h-3 overflow-hidden rounded-full bg-line" style={{ width: `${(total / max) * 100}%` }}>
                    {ORDER.map((p) => c[p] ? <div key={p} className={POLARITY[p].bg} style={{ flexGrow: c[p], flexBasis: 0 }} /> : null)}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

function Row({ r, n }) {
  const [open, setOpen] = useState(false);
  return (
    <li>
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open}
        className="flex w-full items-start gap-3 py-4 text-left hover:bg-white/60 sm:items-center sm:gap-4">
        <span className="w-6 shrink-0 pt-0.5 text-sm tabular-nums text-muted sm:pt-0">{n}</span>
        <span className="flex-1">
          <span className="line-clamp-2 font-serif text-lg sm:line-clamp-1">{r.text}</span>
          {r.aspects.length > 0 && (
            <span className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm">
              {r.aspects.map((a) => (
                <span key={a.aspect} className={POLARITY[a.polarity]?.text ?? "text-muted"}>
                  {aspectLabel(a.aspect)}: {a.polarity}
                </span>
              ))}
            </span>
          )}
        </span>
        <Verdict r={r} />
      </button>
      {open && (
        <div className="mb-6 rounded-2xl border border-line bg-white p-5 sm:p-8">
          <Result result={r} />
        </div>
      )}
    </li>
  );
}

function download(results) {
  const keys = Object.keys(ASPECTS);
  const rows = [["review", "overall", "confidence", "not_sure", ...keys.map(aspectLabel)]];
  for (const r of results) {
    const by = Object.fromEntries(r.aspects.map((a) => [a.aspect, a.polarity]));
    rows.push([r.text, r.polarity, r.confidence, isUnsure(r) ? "yes" : "no", ...keys.map((k) => by[k] || "")]);
  }
  const url = URL.createObjectURL(new Blob([toCsv(rows)], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url; a.download = "sentio-results.csv"; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function Bulk() {
  const { user } = useAuth();
  const [text, setText] = useState("");
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);

  const reviews = useMemo(() => text.split(/\r?\n/).map((t) => t.trim()).filter(Boolean), [text]);
  const tooMany = reviews.length > MAX;
  const tooLong = reviews.findIndex((t) => t.length > 2000);

  async function onFile(e) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    if (f.size > 2_000_000) { setError("That file is too big. Use a CSV or text file under 2 MB."); return; }
    const content = await f.text();
    const list = /\.csv$/i.test(f.name) ? reviewsFromCsv(content) : content.split(/\r?\n/).map((t) => t.trim()).filter(Boolean);
    // one review per line in the box, so line breaks inside a review become spaces
    const clean = list.map((t) => t.replace(/\s*[\r\n]+\s*/g, " "));
    if (!clean.length) { setError("No reviews found in that file."); return; }
    setError("");
    setInfo(clean.length > MAX ? `Found ${clean.length} reviews; kept the first ${MAX}.` : `Loaded ${clean.length} reviews from ${f.name}.`);
    setText(clean.slice(0, MAX).join("\n"));
  }

  async function run() {
    if (!reviews.length) { setError("Add at least one review, one per line."); return; }
    if (tooMany) { setError(`You can analyse up to ${MAX} reviews at once. Remove ${reviews.length - MAX}.`); return; }
    if (tooLong >= 0) { setError(`Review ${tooLong + 1} is longer than 2,000 characters.`); return; }
    setBusy(true); setError(""); setInfo("");
    try { setResults((await api.analyzeBatch(reviews)).results); }
    catch (e) { setError(e.message); setResults(null); }
    finally { setBusy(false); }
  }

  return (
    <section className="wrap max-w-4xl py-16">
      <h1 className="text-4xl sm:text-5xl">Analyse many reviews</h1>
      <p className="mt-4 max-w-prose text-muted">
        Paste up to {MAX} reviews, one per line, or upload a CSV file. You'll get a summary of what customers
        complain about and a verdict for every review.
      </p>

      <form className="mt-10" onSubmit={(e) => { e.preventDefault(); run(); }}>
        <label htmlFor="reviews" className="sr-only">Reviews, one per line</label>
        <textarea id="reviews" rows={8} className="field font-serif text-lg leading-relaxed"
          placeholder={"One review per line, for example:\nkhana thanda tha\ndelivery fast thi par packaging leak ho gaya"}
          value={text} onChange={(e) => setText(e.target.value)} />
        <div className="mt-2 flex flex-wrap justify-between gap-2 text-sm">
          <span className={tooMany ? "font-medium text-chilli-ink" : "text-muted"}>
            {reviews.length} {reviews.length === 1 ? "review" : "reviews"} (up to {MAX})
          </span>
          {info && <span className="text-muted" role="status">{info}</span>}
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? `Reading ${reviews.length} reviews…` : `Analyse ${reviews.length || ""} ${reviews.length === 1 ? "review" : "reviews"}`.replace("  ", " ")}
          </button>
          <button type="button" className="btn-quiet" onClick={() => fileRef.current?.click()} disabled={busy}>Upload CSV or text file</button>
          <input ref={fileRef} type="file" accept=".csv,.txt,text/csv,text/plain" className="hidden" onChange={onFile} />
          <button type="button" className="text-sm font-medium text-indigo underline underline-offset-4" onClick={() => setText(SAMPLE)} disabled={busy}>
            Use sample reviews
          </button>
        </div>
        <p className="mt-3 text-sm text-muted">
          CSV files: the column named <code>review</code>, <code>review_text</code> or <code>text</code> is used, otherwise the first column.
        </p>
      </form>

      {error && <p role="alert" className="mt-6 rounded-xl bg-chilli-soft px-4 py-3 text-chilli-ink">{error}</p>}

      {results && (
        <div className="mt-12 border-t border-line pt-12" aria-live="polite">
          <Summary results={results} />

          <div className="mt-14 flex flex-wrap items-end justify-between gap-3">
            <h2 className="text-2xl">Every review</h2>
            <button type="button" className="btn-quiet py-1.5" onClick={() => download(results)}>Download results (CSV)</button>
          </div>
          <ul className="mt-4 divide-y divide-line border-y border-line">
            {results.map((r, i) => <Row key={r.id} r={r} n={i + 1} />)}
          </ul>
          {user ? (
            <p className="mt-6 text-sm text-muted">Saved to your <Link to="/dashboard" className="font-medium text-indigo underline underline-offset-4">dashboard</Link> and history.</p>
          ) : (
            <p className="mt-6 text-sm text-muted">
              <Link to="/login" className="font-medium text-indigo underline underline-offset-4">Sign in</Link> to keep these reviews in your own dashboard.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
