"use client";

import { FormEvent, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface CompanyCard {
  name: string;
  domain: string | null;
  website: string | null;
  industry: string | null;
  employee_size: string | null;
  location: string | null;
  description: string | null;
  linkedin_url: string | null;
}

interface EnrichResponse {
  demo: boolean;
  note: string | null;
  person: { name: string };
  company: CompanyCard;
}

type Status = "idle" | "loading" | "error" | "done";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w.charAt(0).toUpperCase())
    .join("");
}

function Fact({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div className="fact">
      <span className="fact-label">{label}</span>
      <span className="fact-value">{value}</span>
    </div>
  );
}

export default function Home() {
  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [website, setWebsite] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<EnrichResponse | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus("loading");
    try {
      const res = await fetch(`${API_URL}/enrich`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, company, website }),
      });
      if (!res.ok) throw new Error(`Backend returned ${res.status}`);
      const data: EnrichResponse = await res.json();
      setResult(data);
      setStatus("done");
    } catch {
      setStatus("error");
    }
  }

  const card = result?.company;

  return (
    <main className="page">
      <div className="glow" aria-hidden="true" />

      <header className="hero">
        <p className="eyebrow">Digital Brooch · Built with Clay&rsquo;s Public API</p>
        <h1>
          Get <span className="accent">Clayed.</span>
        </h1>
        <p className="sub">
          Enter a company and watch it get enriched — firmographics, size,
          location and more, pulled through Clay&rsquo;s API and pinned to a
          card you could wear.
        </p>
      </header>

      <section className="panel">
        <form onSubmit={onSubmit} className="form">
          <label className="field">
            <span>Your name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Samyak Jain"
              required
              autoComplete="name"
            />
          </label>
          <label className="field">
            <span>Company</span>
            <input
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Clay"
              required
              autoComplete="organization"
            />
          </label>
          <label className="field">
            <span>Company website</span>
            <input
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="clay.com"
              required
              inputMode="url"
            />
          </label>
          <button type="submit" className="submit" disabled={status === "loading"}>
            {status === "loading" ? "Enriching…" : "Enrich it →"}
          </button>
        </form>

        {status === "error" && (
          <p className="error">
            Couldn&rsquo;t reach the enrichment API. Is the backend running on{" "}
            <code>localhost:8000</code>?
          </p>
        )}
      </section>

      {status === "done" && result && card && (
        <section className="card" aria-live="polite">
          {result.demo && (
            <div className="demo-banner" role="note">
              <strong>Demo data</strong> — add a Clay API key for live enrichment.
              {result.note ? ` ${result.note}` : ""}
            </div>
          )}

          <div className="card-head">
            <div className="monogram" aria-hidden="true">
              {initials(card.name)}
            </div>
            <div>
              <h2>{card.name}</h2>
              {card.domain && <p className="domain">{card.domain}</p>}
            </div>
          </div>

          {card.description && <p className="description">{card.description}</p>}

          <div className="facts">
            <Fact label="Industry" value={card.industry} />
            <Fact label="Company size" value={card.employee_size} />
            <Fact label="Headquarters" value={card.location} />
          </div>

          <div className="card-actions">
            {card.website && (
              <a href={card.website} target="_blank" rel="noreferrer" className="btn">
                Website ↗
              </a>
            )}
            {card.linkedin_url && (
              <a href={card.linkedin_url} target="_blank" rel="noreferrer" className="btn btn-ghost">
                LinkedIn ↗
              </a>
            )}
          </div>

          <p className="card-foot">
            Enriched for {result.person.name} ·{" "}
            {result.demo ? "Source: built-in demo fallback" : "Source: Clay Public API"}
          </p>
        </section>
      )}

      <footer className="footer">
        Built by Samyak Jain with Clay&rsquo;s Public API — Next.js + FastAPI,
        enrichment by Clay.
      </footer>
    </main>
  );
}
