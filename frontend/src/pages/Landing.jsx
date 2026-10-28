import { useState } from "react";
import { Link } from "react-router-dom";
import { AnnotatedText } from "../components/Annotated";
import { AnalyzeBox } from "../components/AnalyzeBox";
import { ASPECTS } from "../lib/aspects";

const HERO_EXAMPLES = [
  [
    { text: "Khana bahut tasty tha", aspect: "food_quality", polarity: "positive" },
    { text: " par " },
    { text: "delivery boy rude tha.", aspect: "delivery_partner", polarity: "negative" },
  ],
  [
    { text: "Jaldi mil jata hai saman", aspect: "delivery_time", polarity: "positive" },
    { text: " lekin " },
    { text: "bahut costly padta hai.", aspect: "price_offers", polarity: "negative" },
  ],
  [
    { text: "Refund ke liye 10 din se wait", aspect: "refund_support", polarity: "negative" },
    { text: " kar raha hu, koi response nahi." },
  ],
];

// Scores on the same frozen test set of 277 reviews (ML/results/RESULTS.md)
const MODELS = [
  { name: "HingRoBERTa (ours, deployed)", score: 0.817, best: true },
  { name: "TF-IDF + logistic regression", score: 0.67 },
  { name: "mBERT", score: 0.635 },
  { name: "XLM-RoBERTa", score: 0.598 },
  { name: "Always guessing “negative”", score: 0.304 },
];

const FAQ = [
  ["What is Hinglish, and why does it need its own model?",
   "Hinglish mixes Hindi and English in one sentence, usually typed in English letters: “khana thanda tha but delivery fast thi”. English-only models miss the Hindi words, and Hindi models miss the English ones. Sentio.io is trained on 2,291 real reviews written exactly like this."],
  ["Why not just use the star rating?",
   "A 4-star review can still contain a serious complaint about price or packaging, and a 1-star review can praise the food. Stars give one number per review. Sentio.io tells you which part of the order each opinion is about."],
  ["How accurate is it?",
   "On 277 reviews it never saw during training, it scores 0.82 macro-F1 for overall sentiment and 0.71 F1 for spotting which aspects a review mentions. It is weakest on packaging, which appears in few reviews. Full numbers are in the project's results report."],
  ["Does it read Devanagari?",
   "It works best on Hindi typed in English letters, which is how almost all app reviews are written. Devanagari is recognised but was rare in the training data."],
  ["Is my review stored?",
   "If you are signed in, it is saved to your own history and dashboard, and only you can see it. Without signing in, it is stored with no name attached and is not shown to anyone."],
];

const STEPS = [
  ["Collect", "Over 240,000 Play Store and Google Maps reviews for a dozen food and grocery apps, filtered down to genuinely code-mixed Hinglish."],
  ["Label", "Every review was labelled by hand: overall sentiment plus seven aspects. Three annotators agreed with κ = 0.83 on a shared set of 200."],
  ["Train", "We fine-tuned five models on the same split and kept the best, HingRoBERTa, which reads Hinglish natively."],
  ["Read", "Paste any review: the model returns the overall sentiment and a verdict for each part of the order it mentions."],
];

function Hero() {
  const [i, setI] = useState(0);
  return (
    <section className="wrap pb-20 pt-16 sm:pt-24">
      <h1 className="max-w-3xl text-[2.6rem] sm:text-6xl">
        Read every food review the way the customer meant it.
      </h1>
      <p className="mt-6 max-w-prose text-lg text-muted sm:text-xl">
        Sentio.io reads Hinglish delivery-app reviews and splits each one into the parts of the order it talks about,
        so “tasty but late” stops counting as one mixed star.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <a href="#try" className="btn-primary">Try a review</a>
        <Link to="/dashboard" className="btn-quiet">See the dashboard</Link>
      </div>

      <div className="mt-16 rounded-[2rem] border border-line bg-white px-6 py-10 sm:px-12 sm:py-14">
        <div key={i}>
          <AnnotatedText segments={HERO_EXAMPLES[i]} size="xl" animate />
        </div>
        <div className="mt-8 flex items-center justify-between gap-4 border-t border-line pt-5 text-sm text-muted">
          <span>Real reviews from our dataset.</span>
          <button type="button" className="font-medium text-indigo underline underline-offset-4"
            onClick={() => setI((i + 1) % HERO_EXAMPLES.length)}>
            Next example
          </button>
        </div>
      </div>
    </section>
  );
}

function TryIt() {
  return (
    <section id="try" className="wrap scroll-mt-20 py-20">
      <h2 className="text-4xl sm:text-5xl">Try one yourself.</h2>
      <p className="mt-4 max-w-prose text-muted">Paste any review, in Hinglish, English or Hindi. Nothing to sign up for.</p>
      <div className="mt-10"><AnalyzeBox /></div>
    </section>
  );
}

function StarsVsAspects() {
  return (
    <section className="bg-indigo text-paper">
      <div className="wrap grid gap-14 py-24 lg:grid-cols-2 lg:gap-20">
        <div>
          <h2 className="text-4xl sm:text-5xl">A star rating hides the story.</h2>
          <p className="mt-6 max-w-prose text-lg text-paper/75">
            This customer gave four stars. Averaged into an app rating, it just looks happy.
            Read part by part, it is a clear warning about price.
          </p>
        </div>
        <div className="space-y-8">
          <div className="rounded-2xl border border-paper/15 p-6">
            <p className="font-serif text-2xl leading-snug">“jaldi mil jata hai saman lekin bahut costly padta hai”</p>
            <p className="mt-4 text-haldi" aria-label="4 out of 5 stars">★★★★<span className="text-paper/25">★</span></p>
          </div>
          <ul className="divide-y divide-paper/15 border-y border-paper/15">
            <li className="flex items-center justify-between py-4">
              <span>Delivery time</span>
              <span className="rounded-full bg-leaf px-3 py-0.5 text-sm font-medium text-paper">Positive</span>
            </li>
            <li className="flex items-center justify-between py-4">
              <span>Price &amp; offers</span>
              <span className="rounded-full bg-chilli px-3 py-0.5 text-sm font-medium text-paper">Negative</span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
}

function Aspects() {
  return (
    <section className="wrap py-24">
      <h2 className="text-4xl sm:text-5xl">Seven things customers talk about.</h2>
      <p className="mt-4 max-w-prose text-muted">
        We picked these by reading thousands of reviews. Almost every complaint or compliment fits one of them.
      </p>
      <dl className="mt-12 grid gap-x-12 sm:grid-cols-2">
        {Object.entries(ASPECTS).map(([key, a]) => (
          <div key={key} className="flex flex-col gap-1 border-b border-line py-5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-6">
            <dt className="font-medium">{a.label}</dt>
            <dd className="font-serif text-lg text-muted sm:text-right">“{a.example}”</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function Proof() {
  return (
    <section className="wrap py-24">
      <div className="grid gap-14 lg:grid-cols-[1fr_1.3fr] lg:gap-20">
        <div>
          <h2 className="text-4xl sm:text-5xl">Built on our own data.</h2>
          <p className="mt-6 max-w-prose text-muted">
            No public dataset covers Hinglish food-delivery reviews by aspect, so we made one:
            2,291 reviews, each labelled by hand. Every model below was trained on the same reviews
            and scored on the same 277 reviews it had never seen.
          </p>
        </div>
        <figure>
          <figcaption className="mb-6 text-sm text-muted">Overall sentiment, macro-F1 (higher is better, 1.0 is perfect)</figcaption>
          <ul className="space-y-5">
            {MODELS.map((m) => (
              <li key={m.name}>
                <div className="mb-1.5 flex justify-between text-sm">
                  <span className={m.best ? "font-semibold" : "text-muted"}>{m.name}</span>
                  <span className="tabular-nums">{m.score.toFixed(2)}</span>
                </div>
                <div className="h-3 rounded-full bg-line/70">
                  <div className={`h-3 rounded-full ${m.best ? "bg-indigo" : "bg-slate/60"}`} style={{ width: `${m.score * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </figure>
      </div>
    </section>
  );
}

function HowItWorks() {
  return (
    <section className="border-y border-line bg-white">
      <div className="wrap py-24">
        <h2 className="text-4xl sm:text-5xl">How we built it.</h2>
        <ol className="mt-12 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(([title, body], n) => (
            <li key={title}>
              <span className="font-serif text-5xl text-haldi-deep">{n + 1}</span>
              <h3 className="mt-3 font-sans text-lg font-semibold">{title}</h3>
              <p className="mt-2 text-muted">{body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function Faq() {
  return (
    <section className="wrap py-24">
      <h2 className="text-4xl sm:text-5xl">Questions people ask.</h2>
      <div className="mt-10 max-w-3xl divide-y divide-line border-y border-line">
        {FAQ.map(([q, a]) => (
          <details key={q} className="group py-5">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-6 text-lg font-medium">
              {q}
              <span className="text-2xl text-muted transition-transform group-open:rotate-45" aria-hidden>+</span>
            </summary>
            <p className="mt-3 max-w-prose text-muted">{a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

function ClosingCta() {
  return (
    <section className="wrap">
      <div className="rounded-[2rem] bg-haldi-soft px-6 py-16 text-center sm:px-12">
        <h2 className="mx-auto max-w-2xl text-4xl sm:text-5xl">See what your customers are really complaining about.</h2>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link to="/analyze" className="btn-primary">Analyse a review</Link>
          <Link to="/register" className="btn-quiet border-ink/30">Create an account</Link>
        </div>
      </div>
    </section>
  );
}

export default function Landing() {
  return (
    <>
      <Hero />
      <TryIt />
      <StarsVsAspects />
      <Aspects />
      <Proof />
      <HowItWorks />
      <Faq />
      <ClosingCta />
    </>
  );
}
