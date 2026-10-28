import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { POLARITY } from "../lib/aspects";
import { Result, VerdictPill } from "../components/Result";

const FILTERS = [["", "All"], ["negative", "Negative"], ["neutral", "Neutral"], ["positive", "Positive"]];
const PAGE_SIZE = 15;

function when(iso) {
  return new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}

function Row({ item }) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");

  function toggle() {
    setOpen((o) => !o);
    if (!detail) api.review(item.id).then(setDetail).catch((e) => setError(e.message));
  }

  return (
    <li>
      <button type="button" onClick={toggle} aria-expanded={open}
        className="flex w-full items-center gap-4 py-4 text-left hover:bg-white/60">
        <span className="line-clamp-1 flex-1 font-serif text-lg">{item.text}</span>
        <span className="hidden text-sm text-muted sm:inline">{when(item.created_at)}</span>
        <VerdictPill polarity={item.polarity} size="sm" />
      </button>
      {open && (
        <div className="mb-6 rounded-2xl border border-line bg-white p-6 sm:p-8">
          {error ? <p className="text-chilli-ink">{error}</p> : detail ? <Result result={detail} /> : <p className="text-muted">Loading…</p>}
        </div>
      )}
    </li>
  );
}

export default function History() {
  const [polarity, setPolarity] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setData(null);
    api.reviews({ page, pageSize: PAGE_SIZE, polarity: polarity || undefined })
      .then(setData).catch((e) => setError(e.message));
  }, [page, polarity]);

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <section className="wrap max-w-5xl py-16">
      <h1 className="text-4xl sm:text-5xl">History</h1>
      <p className="mt-3 text-muted">Every review that has been analysed. Open one to see the full breakdown.</p>

      <div className="mt-8 inline-flex rounded-full border border-line bg-white p-1" role="group" aria-label="Filter by sentiment">
        {FILTERS.map(([value, label]) => (
          <button key={label} type="button" aria-pressed={polarity === value}
            onClick={() => { setPolarity(value); setPage(1); }}
            className={`rounded-full px-4 py-1.5 text-sm font-medium ${polarity === value ? (value ? `${POLARITY[value].soft} ${POLARITY[value].text}` : "bg-ink text-paper") : "text-muted hover:text-ink"}`}>
            {label}
          </button>
        ))}
      </div>

      {error && <p role="alert" className="mt-6 rounded-xl bg-chilli-soft px-4 py-3 text-chilli-ink">{error}</p>}
      {!data && !error && <p className="mt-8 text-muted">Loading…</p>}

      {data && data.items.length === 0 && (
        <div className="mt-10">
          <p className="text-muted">{polarity ? `No ${polarity} reviews yet.` : "No reviews yet."}</p>
          <Link to="/analyze" className="btn-primary mt-5">Analyse a review</Link>
        </div>
      )}

      {data && data.items.length > 0 && (
        <>
          <ul className="mt-8 divide-y divide-line border-y border-line">
            {data.items.map((item) => <Row key={item.id} item={item} />)}
          </ul>
          <div className="mt-6 flex items-center justify-between text-sm">
            <span className="text-muted">{data.total} reviews</span>
            <div className="flex items-center gap-3">
              <button className="btn-quiet py-1.5" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
              <span className="tabular-nums text-muted">Page {page} of {pages}</span>
              <button className="btn-quiet py-1.5" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
