import { Link } from "react-router-dom";
import { AnalyzeBox } from "../components/AnalyzeBox";

export default function Analyze() {
  return (
    <section className="wrap max-w-4xl py-16">
      <h1 className="text-4xl sm:text-5xl">Analyse a review</h1>
      <p className="mt-4 max-w-prose text-muted">
        Paste a customer review. You'll get the overall sentiment and a verdict for each part of the order it mentions.
      </p>
      <p className="mt-2 text-sm text-muted">
        Have a lot of reviews? <Link to="/bulk" className="font-medium text-indigo underline underline-offset-4">Analyse up to 50 at once</Link>.
      </p>
      <div className="mt-10"><AnalyzeBox autoFocus /></div>
    </section>
  );
}
