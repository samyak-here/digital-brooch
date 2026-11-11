# Get Clayed — a Digital Brooch built with Clay

A one-page demo app built **with Clay's Public API**. Samyak Jain built it
as a portfolio piece to show Clay's engineers what he can ship with their
platform: a working enrichment flow, end to end — form in, live firmographics
out.

The concept is a "Digital Brooch": a small, showable thing that does the
most Clay thing possible — **enrichment**. Enter your name, a company, and
its website, and you get back an enriched company card (firmographics, size,
location, description, LinkedIn) — the digital brooch you'd pin on and show.

Built by **Samyak Jain** — CS + Data Science, UW–Madison (May 2027).

## Stack

- **Frontend:** Next.js (App Router) + TypeScript — one page, no auth, no DB.
- **Backend:** FastAPI (Python) — one endpoint, `POST /enrich`.
- **Enrichment:** Clay's Public API (`https://api.clay.com/public/v0`,
  `clay-api-key` header), company search by domain.

## How it works

```
Browser (Next.js, :3000)
   │  POST /enrich {name, company, website}
   ▼
FastAPI backend (:8000)
   ├─ CLAY_API_KEY set → Clay Public API company search → map to card schema
   └─ no key / call fails → clearly-labelled demo card (demo: true)
```

### Demo fallback (important)

This demo never fakes live data. If `CLAY_API_KEY` is not set — or the Clay
call errors, times out, or returns no match — the backend returns a sample
card with `"demo": true`, and the UI shows a banner:

> **Demo data** — add a Clay API key for live enrichment.

Demo fields are generated deterministically from the company you entered
(industry guessed from the name/domain, a stable size/location pick, a
LinkedIn company URL from the name slug), so the full card experience is
visible before any key exists.

## Setup

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# optional: live enrichment via Clay
export CLAY_API_KEY=<your key>   # create one in Clay: API and CLI → API keys

uvicorn main:app --reload --port 8000
```

Check it: `curl http://localhost:8000/health` →
`{"status":"ok","clay_configured":false}` (true once a key is set).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

The frontend calls `http://localhost:8000` by default. To point it elsewhere,
set `NEXT_PUBLIC_API_URL` (see `frontend/.env.local.example`).

### 3. Try it

Open http://localhost:3000, enter a name, company, and website, and hit
**Enrich it**. Without a key you get the demo card (banner included); with a
key the same card fills with live Clay data.

## Tests

```bash
cd backend
.venv/bin/python -m pytest
```

The suite covers demo mode over HTTP, the Clay response mapper against a
representative company-search payload, the live path with the Clay call
stubbed out, and the failure fallback (stub raises → labelled demo card).

## API contract

`POST /enrich`

```json
// request
{"name": "Samyak Jain", "company": "Clay", "website": "https://www.clay.com"}

// response
{
  "demo": true,
  "note": null,
  "person": {"name": "Samyak Jain"},
  "company": {
    "name": "Clay",
    "domain": "clay.com",
    "website": "https://clay.com",
    "industry": "Software & Technology",
    "employee_size": "201-500",
    "location": "New York, NY, United States",
    "description": "…",
    "linkedin_url": "https://www.linkedin.com/company/clay"
  }
}
```

`note` is set only when a live lookup was attempted and fell back
(e.g. "The live Clay lookup failed — showing demo data instead.").

## Notes on the Clay integration

- The client lives in `backend/clay.py`. The request shape (company search
  by domain) and the response mapper are isolated there on purpose: the
  mapper tolerates the envelope/field-name variants Clay-style firmographic
  payloads come in, and anything unparseable falls back to demo data instead
  of rendering an empty "live" card.
- Clay's Public API is GA since Sep 15, 2026 and available on all plans,
  including Free (search volume is capped per plan). Webhook-into-table
  flows need Growth/Enterprise, which is why this demo uses the Public API
  search route.

## Project layout

```
clay-brooch/
├── README.md
├── backend/
│   ├── main.py            # FastAPI app: /health, /enrich
│   ├── clay.py            # Clay client, response mapper, demo fallback
│   ├── test_main.py       # pytest suite (demo, mapper, stubbed live, fallback)
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── app/
    │   ├── page.tsx       # the one page: form + enriched card
    │   ├── layout.tsx
    │   └── globals.css    # dark theme, orange accent
    ├── package.json
    └── .env.local.example
```
