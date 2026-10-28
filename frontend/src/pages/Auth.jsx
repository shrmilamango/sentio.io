import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

// Only follow ?next= to a page on this site (blocks "//evil.com" and "/\\evil.com").
function safeNext(next) {
  return next && /^\/(?![\/\\])/.test(next) ? next : "/dashboard";
}

function Shell({ title, intro, children, footer }) {
  return (
    <section className="wrap flex justify-center py-20">
      <div className="w-full max-w-md">
        <h1 className="text-4xl">{title}</h1>
        <p className="mt-3 text-muted">{intro}</p>
        <div className="mt-8">{children}</div>
        <p className="mt-8 text-muted">{footer}</p>
      </div>
    </section>
  );
}

function Field({ label, hint, ...props }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium">{label}</span>
      <input className="field" {...props} />
      {hint && <span className="mt-1 block text-sm text-muted">{hint}</span>}
    </label>
  );
}

export function Login() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await signIn(form.username.trim(), form.password);
      navigate(safeNext(params.get("next")), { replace: true });
    } catch (err) {
      setError(err.message);
    } finally { setBusy(false); }
  }

  return (
    <Shell title="Sign in" intro="See your dashboard and every review you've analysed."
      footer={<>New here? <Link to="/register" className="text-indigo underline underline-offset-4">Create an account</Link></>}>
      <form onSubmit={submit} className="space-y-5">
        <Field label="Username" autoComplete="username" required value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })} />
        <Field label="Password" type="password" autoComplete="current-password" required value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })} />
        {error && <p role="alert" className="rounded-xl bg-chilli-soft px-4 py-3 text-chilli-ink">{error}</p>}
        <button className="btn-primary w-full" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </Shell>
  );
}

export function Register() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ full_name: "", username: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await api.register(form.username.trim(), form.password, form.full_name.trim());
      await signIn(form.username.trim(), form.password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally { setBusy(false); }
  }

  return (
    <Shell title="Create an account" intro="Free. You'll get a dashboard of every review you analyse."
      footer={<>Already have an account? <Link to="/login" className="text-indigo underline underline-offset-4">Sign in</Link></>}>
      <form onSubmit={submit} className="space-y-5">
        <Field label="Your name" autoComplete="name" value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        <Field label="Username" autoComplete="username" required minLength={3} maxLength={30} pattern="[A-Za-z0-9_]+"
          hint="3–30 letters, numbers or underscores." value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })} />
        <Field label="Password" type="password" autoComplete="new-password" required minLength={8} maxLength={72}
          hint="At least 8 characters." value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })} />
        {error && <p role="alert" className="rounded-xl bg-chilli-soft px-4 py-3 text-chilli-ink">{error}</p>}
        <button className="btn-primary w-full" disabled={busy}>{busy ? "Creating account…" : "Create account"}</button>
      </form>
    </Shell>
  );
}
