import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="wrap py-28">
      <h1 className="text-5xl">This page doesn't exist.</h1>
      <p className="mt-4 text-muted">The link may be wrong or the page has moved.</p>
      <Link to="/" className="btn-primary mt-8">Go to the home page</Link>
    </section>
  );
}
