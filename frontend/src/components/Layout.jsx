import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

export function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5" aria-label="Sentio.io home">
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden>
        <rect width="32" height="32" rx="8" fill="#1F2A5C" />
        <path d="M7 21h7" stroke="#2F7D4F" strokeWidth="3" strokeLinecap="round" />
        <path d="M17 21h8" stroke="#C8412E" strokeWidth="3" strokeLinecap="round" />
        <path d="M8 13c2-3 5-3 7 0s5 3 9 0" stroke="#F2B632" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      </svg>
      <span className="font-serif text-2xl leading-none">sentio<span className="text-muted">.io</span></span>
    </Link>
  );
}

function Nav() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const links = [["/analyze", "Analyse"], ["/bulk", "Bulk"], ["/dashboard", "Dashboard"], ["/history", "History"]];
  const desktop = ({ isActive }) => (isActive ? "text-ink" : "text-muted hover:text-ink");
  const out = () => { signOut(); setOpen(false); navigate("/"); };
  return (
    <header className="sticky top-0 z-20 border-b border-line/70 bg-paper/90 backdrop-blur">
      <nav className="wrap flex h-16 items-center justify-between gap-6" aria-label="Main">
        <Logo />
        <div className="hidden items-center gap-7 sm:flex">
          {links.map(([to, label]) => <NavLink key={to} to={to} className={desktop}>{label}</NavLink>)}
          {user
            ? <button className="btn-quiet py-1.5" onClick={out}>Sign out</button>
            : <Link to="/login" className="btn-quiet py-1.5">Sign in</Link>}
        </div>
        <button type="button" className="btn-quiet py-1.5 sm:hidden" aria-expanded={open} aria-controls="mobile-menu"
          onClick={() => setOpen((o) => !o)}>
          {open ? "Close" : "Menu"}
        </button>
      </nav>
      {open && (
        <div id="mobile-menu" className="border-t border-line bg-paper sm:hidden">
          <ul className="wrap divide-y divide-line py-2">
            {links.map(([to, label]) => (
              <li key={to}><NavLink to={to} onClick={() => setOpen(false)} className="block py-3 text-lg">{label}</NavLink></li>
            ))}
            <li>
              {user
                ? <button className="block w-full py-3 text-left text-lg" onClick={out}>Sign out</button>
                : <Link to="/login" onClick={() => setOpen(false)} className="block py-3 text-lg">Sign in</Link>}
            </li>
          </ul>
        </div>
      )}
    </header>
  );
}

function Footer() {
  return (
    <footer className="mt-24 border-t border-line">
      <div className="wrap flex flex-col gap-6 py-10 text-sm text-muted sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <Logo />
          <p className="max-w-sm">Aspect-based sentiment analysis of code-mixed Hinglish food delivery reviews.</p>
        </div>
      </div>
    </footer>
  );
}

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-30 focus:rounded focus:bg-white focus:px-3 focus:py-2">Skip to content</a>
      <Nav />
      <main id="main" className="flex-1"><Outlet /></main>
      <Footer />
    </div>
  );
}
