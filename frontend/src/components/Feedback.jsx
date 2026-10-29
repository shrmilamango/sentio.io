import { useState } from "react";
import { api } from "../lib/api";
import { POLARITY } from "../lib/aspects";

/** "Was this right?" — wrong answers are saved and become training data. */
export function Feedback({ analysisId }) {
  const [step, setStep] = useState("ask");          // ask | fix | done
  const [choice, setChoice] = useState(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function send(body) {
    setBusy(true); setError("");
    try { await api.feedback(analysisId, body); setStep("done"); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  if (step === "done") {
    return <p className="text-sm text-leaf-ink" role="status">Thanks, saved. Answers like this help train the next version of the model.</p>;
  }

  return (
    <div className="rounded-2xl border border-line bg-white p-5">
      {step === "ask" && (
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-medium">Was this right?</span>
          <button type="button" className="btn-quiet py-1.5" disabled={busy}
            onClick={() => send({ is_correct: true })}>👍 Yes</button>
          <button type="button" className="btn-quiet py-1.5" disabled={busy}
            onClick={() => setStep("fix")}>👎 No</button>
        </div>
      )}

      {step === "fix" && (
        <form onSubmit={(e) => { e.preventDefault(); send({ is_correct: false, correct_polarity: choice, note: note.trim() || null }); }}>
          <fieldset>
            <legend className="font-medium">What is the review really saying?</legend>
            <div className="mt-3 flex flex-wrap gap-2">
              {["negative", "neutral", "positive"].map((p) => (
                <button key={p} type="button" aria-pressed={choice === p} onClick={() => setChoice(p)}
                  className={`rounded-full border px-4 py-1.5 text-sm font-medium ${choice === p ? `${POLARITY[p].soft} ${POLARITY[p].text} border-transparent` : "border-line bg-white text-muted hover:border-ink"}`}>
                  {POLARITY[p].label}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="mt-4 block">
            <span className="mb-1.5 block text-sm text-muted">Anything else? (optional, e.g. "sarcastic")</span>
            <input className="field" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
          </label>
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="submit" className="btn-primary py-1.5" disabled={busy || (!choice && !note.trim())}>
              {busy ? "Sending…" : "Send correction"}
            </button>
            <button type="button" className="btn-quiet py-1.5" onClick={() => setStep("ask")}>Cancel</button>
          </div>
        </form>
      )}

      {error && <p role="alert" className="mt-3 text-sm text-chilli-ink">{error}</p>}
    </div>
  );
}
