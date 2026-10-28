import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { LANGUAGES, POLARITY, aspectLabel } from "../lib/aspects";
import { VerdictPill } from "../components/Result";

const ORDER = ["negative", "neutral", "positive"];
const pct = (n, d) => (d ? Math.round((n / d) * 100) : 0);

function SplitBar({ counts, height = "h-3" }) {
  return (
    <div className={`flex ${height} overflow-hidden rounded-full bg-line`}>
      {ORDER.map((k) => counts[k] ? (
        <div key={k} className={POLARITY[k].bg} style={{ flexGrow: counts[k], flexBasis: 0 }} title={`${POLARITY[k].label}: ${counts[k]}`} />
      ) : null)}
    </div>
  );
}

function Legend() {
  return (
    <ul className="flex flex-wrap gap-5 text-sm text-muted">
      {ORDER.map((k) => (
        <li key={k} className="flex items-center gap-2"><span className={`h-2.5 w-2.5 rounded-full ${POLARITY[k].bg}`} aria-hidden />{POLARITY[k].label}</li>
      ))}
    </ul>
  );
}

function Summary({ data }) {
  const total = data.total_reviews;
  const neg = data.polarity_counts.negative || 0;
  const worst = [...data.aspect_breakdown].filter((a) => a.negative > 0).sort((a, b) => b.negative - a.negative)[0];
  // "happiest with" = more praise than complaints, and not the aspect we just called the worst
  const best = [...data.aspect_breakdown]
    .filter((a) => a.positive > a.negative && a.aspect !== worst?.aspect)
    .sort((a, b) => (b.positive - b.negative) - (a.positive - a.negative))[0];
  return (
    <p className="max-w-4xl font-serif text-3xl leading-snug sm:text-4xl">
      Out of {total} {total === 1 ? "review" : "reviews"}, {pct(neg, total)}% are negative.
      {worst && <> Customers complain most about <span className="mark mark-neg">{aspectLabel(worst.aspect).toLowerCase()}</span>.</>}
      {best && <> They're happiest with <span className="mark mark-pos">{aspectLabel(best.aspect).toLowerCase()}</span>.</>}
    </p>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [recent, setRecent] = useState([]);
  const [model, setModel] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.insights(), api.reviews({ pageSize: 5 }), api.models()])
      .then(([ins, rev, models]) => { setData(ins); setRecent(rev.items); setModel(models.find((m) => m.is_active)); })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <section className="wrap py-16"><p role="alert" className="rounded-xl bg-chilli-soft px-4 py-3 text-chilli-ink">{error}</p></section>;
  if (!data) return <section className="wrap py-16 text-muted">Loading your dashboard…</section>;

  const aspects = [...data.aspect_breakdown].sort((a, b) => b.negative - a.negative || (b.negative + b.neutral + b.positive) - (a.negative + a.neutral + a.positive));
  const maxMentions = Math.max(1, ...aspects.map((a) => a.negative + a.neutral + a.positive));

  return (
    <section className="wrap py-16">
      <p className="text-muted">Hi {user?.full_name || user?.username}, here's what your reviews say.</p>

      {data.total_reviews === 0 ? (
        <div className="mt-8 rounded-[2rem] border border-line bg-white p-10">
          <h1 className="text-4xl">No reviews yet.</h1>
          <p className="mt-3 text-muted">Reviews you analyse while signed in show up here. Only you can see them.</p>
          <Link to="/analyze" className="btn-primary mt-6">Analyse a review</Link>
        </div>
      ) : (
        <>
          <h1 className="sr-only">Dashboard</h1>
          <div className="mt-6"><Summary data={data} /></div>

          <div className="mt-16 grid gap-16 lg:grid-cols-[1.4fr_1fr]">
            <div>
              <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
                <h2 className="text-2xl">Where complaints come from</h2>
                <Legend />
              </div>
              {aspects.length === 0 ? (
                <p className="text-muted">None of the analysed reviews mention a specific part of the order yet.</p>
              ) : (
                <ul className="space-y-5">
                  {aspects.map((a) => {
                    const n = a.negative + a.neutral + a.positive;
                    return (
                      <li key={a.aspect}>
                        <div className="mb-1.5 flex justify-between text-sm">
                          <span className="font-medium">{aspectLabel(a.aspect)}</span>
                          <span className="text-muted tabular-nums">{n} {n === 1 ? "mention" : "mentions"}, {a.negative} negative</span>
                        </div>
                        <div style={{ width: `${(n / maxMentions) * 100}%` }}><SplitBar counts={a} /></div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <div className="space-y-12">
              <div>
                <h2 className="mb-4 text-2xl">Overall sentiment</h2>
                <SplitBar counts={data.polarity_counts} height="h-4" />
                <ul className="mt-3 flex flex-wrap gap-5 text-sm">
                  {ORDER.map((k) => (
                    <li key={k} className="flex items-center gap-2 text-muted">
                      <span className={`h-2.5 w-2.5 rounded-full ${POLARITY[k].bg}`} aria-hidden />
                      {POLARITY[k].label} <span className="tabular-nums text-ink">{data.polarity_counts[k] || 0}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h2 className="mb-4 text-2xl">Languages used</h2>
                <ul className="space-y-2">
                  {Object.entries(data.language_split).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                    <li key={k} className="flex items-center gap-3 text-sm">
                      <span className="w-44 text-muted">{LANGUAGES[k] ?? k}</span>
                      <div className="h-2 flex-1 rounded-full bg-line"><div className="h-2 rounded-full bg-indigo" style={{ width: `${Math.round(v * 100)}%` }} /></div>
                      <span className="w-10 text-right tabular-nums">{Math.round(v * 100)}%</span>
                    </li>
                  ))}
                </ul>
              </div>
              {model && (
                <p className="text-sm text-muted">
                  Reviews are read by <span className="text-ink">{model.name}</span>
                  {model.macro_f1 != null && <> (macro-F1 {model.macro_f1.toFixed(2)} on held-out reviews)</>}.
                </p>
              )}
            </div>
          </div>

          <div className="mt-20">
            <div className="mb-4 flex items-end justify-between">
              <h2 className="text-2xl">Latest reviews</h2>
              <Link to="/history" className="text-sm font-medium text-indigo underline underline-offset-4">See all</Link>
            </div>
            <ul className="divide-y divide-line border-y border-line">
              {recent.map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-6 py-4">
                  <span className="line-clamp-1 font-serif text-lg">{r.text}</span>
                  <VerdictPill polarity={r.polarity} size="sm" />
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </section>
  );
}
