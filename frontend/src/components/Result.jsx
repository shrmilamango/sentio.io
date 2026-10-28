import { useState } from "react";
import { AnnotatedText, segmentsFromResult } from "./Annotated";
import { ASPECTS, LANGUAGES, POLARITY, aspectLabel } from "../lib/aspects";

const pct = (x) => `${Math.round(x * 100)}%`;

export function VerdictPill({ polarity, size = "md" }) {
  const p = POLARITY[polarity] ?? POLARITY.neutral;
  const s = size === "sm" ? "px-2.5 py-0.5 text-sm" : "px-3.5 py-1 text-base";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium ${p.soft} ${p.text} ${s}`}>
      <span className={`h-2 w-2 rounded-full ${p.bg}`} aria-hidden />
      {p.label}
    </span>
  );
}

function ConfidenceBar({ value, polarity }) {
  const p = POLARITY[polarity] ?? POLARITY.neutral;
  return (
    <div className="flex items-center gap-3">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-line" role="presentation">
        <div className={`h-full ${p.bg}`} style={{ width: pct(value) }} />
      </div>
      <span className="w-10 text-sm tabular-nums text-muted">{pct(value)}</span>
    </div>
  );
}

function LanguageMix({ dist }) {
  const entries = Object.entries(dist).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  const tones = { en: "bg-indigo", hi_roman: "bg-haldi", hi_deva: "bg-haldi-deep", emoji: "bg-chilli/60", other: "bg-slate" };
  if (!entries.length) return null;
  return (
    <div>
      <div className="flex h-2.5 overflow-hidden rounded-full">
        {entries.map(([k, v]) => <div key={k} className={tones[k] ?? "bg-slate"} style={{ width: pct(v) }} />)}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted">
        {entries.map(([k, v]) => (
          <li key={k} className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${tones[k] ?? "bg-slate"}`} aria-hidden />
            {LANGUAGES[k] ?? k} <span className="tabular-nums text-ink">{pct(v)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function WordImportance({ tokens }) {
  return (
    <p className="font-serif text-xl leading-loose">
      {tokens.map((t, i) => {
        const w = Math.min(1, Math.abs(t.weight));
        return (
          <span key={i}>
            <span className="rounded px-0.5" style={{ backgroundColor: `rgba(31, 42, 92, ${0.08 + w * 0.5})`, color: w > 0.6 ? "#fff" : undefined }}>
              {t.text}
            </span>{" "}
          </span>
        );
      })}
    </p>
  );
}

export function Result({ result }) {
  const [showWords, setShowWords] = useState(false);
  const segments = segmentsFromResult(result);
  const unplaced = result.aspects.filter((a) => !a.span);
  const unsure = result.confidence < 0.5;

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <VerdictPill polarity={result.polarity} />
        <span className="text-muted">
          overall, {pct(result.confidence)} confident
          {unsure && " — this review mixes opinions, so the overall call is close"}
        </span>
      </div>

      <AnnotatedText segments={segments} size="lg" labels={false} />

      <section>
        <h3 className="mb-3 font-sans text-sm font-semibold text-muted">What it talks about (underlined above)</h3>
        {result.aspects.length === 0 ? (
          <p className="text-muted">No specific part of the order is mentioned — this review only gives an overall opinion.</p>
        ) : (
          <ul className="divide-y divide-line border-y border-line">
            {result.aspects.map((a) => (
              <li key={a.aspect} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <span className="font-medium">{aspectLabel(a.aspect)}</span>
                <span className="flex items-center gap-4">
                  <VerdictPill polarity={a.polarity} size="sm" />
                  <ConfidenceBar value={a.confidence} polarity={a.polarity} />
                </span>
              </li>
            ))}
          </ul>
        )}
        {unplaced.length > 0 && (
          <p className="mt-2 text-sm text-muted">
            {unplaced.map((a) => aspectLabel(a.aspect)).join(", ")}: found in the review as a whole, not one phrase.
          </p>
        )}
      </section>

      <section>
        <h3 className="mb-3 font-sans text-sm font-semibold text-muted">Language mix</h3>
        <LanguageMix dist={result.language_distribution} />
      </section>

      <section>
        <button type="button" className="text-sm font-medium text-indigo underline underline-offset-4" onClick={() => setShowWords((s) => !s)} aria-expanded={showWords}>
          {showWords ? "Hide which words mattered" : "Show which words mattered"}
        </button>
        {showWords && (
          <div className="mt-4 space-y-2">
            <WordImportance tokens={result.tokens} />
            <p className="text-sm text-muted">Darker words had more influence on the model's decision.</p>
          </div>
        )}
      </section>

      <p className="text-sm text-muted">
        Model {result.model_version}, answered in {result.latency_ms} ms
      </p>
    </div>
  );
}

export { ASPECTS };
