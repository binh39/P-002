import { Link } from "wouter";

export default function NotFound() {
  return (
    <main className="not-found">
      <span className="eyebrow">404</span>
      <h1>Page not found</h1>
      <p>The page may have moved, or the URL may be incorrect.</p>
      <Link href="/dashboard">Return to dashboard</Link>
    </main>
  );
}
