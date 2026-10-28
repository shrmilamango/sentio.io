import { AnalyzeBox } from "../components/AnalyzeBox";

export default function Analyze() {
  return (
    <section className="wrap max-w-4xl py-16">
      <h1 className="text-4xl sm:text-5xl">Analyse a review</h1>
      <p className="mt-4 max-w-prose text-muted">
        Paste a customer review. You'll get the overall sentiment and a verdict for each part of the order it mentions.
      </p>
      <div className="mt-10"><AnalyzeBox autoFocus /></div>
    </section>
  );
}
