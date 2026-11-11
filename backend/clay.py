"""Clay Public API client + demo fallback for the Digital Brooch demo.

Live path: when CLAY_API_KEY is set, we query Clay's Public API
(https://api.clay.com/public/v0, `clay-api-key` header) using its company
search, looked up by domain, and map the result into our card schema.

Fallback: with no key — or if the Clay call fails for any reason — we return
a clearly-labelled demo card (`demo: true`) built from the submitted
company/website. Demo data is never disguised as live data.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Optional

import httpx

CLAY_API_BASE = os.environ.get("CLAY_API_BASE", "https://api.clay.com/public/v0")
REQUEST_TIMEOUT_SECONDS = 20.0


# ---------------------------------------------------------------------------
# Card schema
# ---------------------------------------------------------------------------
# {
#   "demo": bool,
#   "note": str | None,          # set when we fell back after a failed live call
#   "person":  {"name": str},
#   "company": {
#       "name": str,
#       "domain": str | None,
#       "website": str | None,
#       "industry": str | None,
#       "employee_size": str | None,   # e.g. "201-500" or "1,001"
#       "location": str | None,        # e.g. "New York, NY, United States"
#       "description": str | None,
#       "linkedin_url": str | None,
#   }
# }
# ---------------------------------------------------------------------------


def normalize_domain(website: str) -> str:
    """Turn 'https://www.Acme.com/about' into 'acme.com'."""
    d = website.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    d = d.split("/")[0].split("?")[0].split("#")[0]
    return d.strip()


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---------------------------------------------------------------------------
# Live Clay path
# ---------------------------------------------------------------------------

async def _search_company_by_domain(domain: str, api_key: str) -> Any:
    """Call Clay's Public API company search for a domain.

    Clay's Public API runs people/company searches in query mode and returns
    results synchronously for a search call. We ask for a single best match.
    Any HTTP error raises, and the caller falls back to demo data.
    """
    headers = {
        "clay-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"domain": domain, "limit": 1}
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            f"{CLAY_API_BASE}/search/companies", headers=headers, json=payload
        )
        resp.raise_for_status()
        return resp.json()


def _first_record(payload: Any) -> Optional[dict]:
    """Pull the first company record out of whatever envelope Clay returns."""
    if payload is None:
        return None
    if isinstance(payload, list):
        return payload[0] if payload and isinstance(payload[0], dict) else None
    if isinstance(payload, dict):
        for key in ("results", "data", "companies", "items", "records"):
            value = payload.get(key)
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value[0]
            if isinstance(value, dict) and value:
                return value
        # No envelope matched: treat the payload itself as the record, but
        # only if it actually carries company-identifying fields.
        identifying = ("name", "company_name", "domain", "website_domain", "website", "url")
        if any(payload.get(k) for k in identifying):
            return payload
        return None
    return None


def _get(record: dict, *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _format_employee_size(record: dict) -> Optional[str]:
    ranged = _get(
        record,
        "employee_size",
        "employee_count_range",
        "employee_range",
        "size",
        "size_range",
        "headcount_range",
    )
    if isinstance(ranged, str):
        return ranged
    count = _get(record, "employee_count", "employees", "headcount", "number_of_employees")
    if isinstance(count, (int, float)):
        return f"{int(count):,}"
    if isinstance(count, str):
        return count
    return None


def _format_location(record: dict) -> Optional[str]:
    direct = _get(record, "location", "headquarters", "hq_location")
    if isinstance(direct, str):
        return direct
    if isinstance(direct, dict):
        parts = [
            direct.get("city"),
            direct.get("state"),
            direct.get("country"),
        ]
        parts = [p for p in parts if p]
        if parts:
            return ", ".join(parts)
    parts = [
        _get(record, "city", "hq_city", "headquarters_city"),
        _get(record, "state", "hq_state", "headquarters_state"),
        _get(record, "country", "hq_country", "headquarters_country"),
    ]
    parts = [p for p in parts if isinstance(p, str) and p]
    return ", ".join(parts) if parts else None


def map_clay_company(payload: Any, *, fallback_company: str, fallback_website: str) -> Optional[dict]:
    """Map a raw Clay company-search response into the card schema.

    Returns None when the payload contains nothing we can identify as a
    company, so the caller can fall back to demo data instead of rendering
    an empty 'live' card.
    """
    record = _first_record(payload)
    if not record:
        return None

    domain = _get(record, "domain", "website_domain", "primary_domain") or normalize_domain(
        fallback_website
    )
    website = _get(record, "website", "url", "homepage") or (f"https://{domain}" if domain else None)
    industry = _get(record, "industry")
    if industry is None:
        industries = record.get("industries")
        if isinstance(industries, list) and industries:
            industry = industries[0]

    company = {
        "name": _get(record, "name", "company_name", "companyName") or fallback_company,
        "domain": domain,
        "website": website,
        "industry": industry,
        "employee_size": _format_employee_size(record),
        "location": _format_location(record),
        "description": _get(record, "description", "about", "summary", "short_description"),
        "linkedin_url": _get(record, "linkedin_url", "linkedin", "linkedin_company_url"),
    }
    if not company["name"] and not company["domain"]:
        return None
    return company


async def enrich_with_clay(name: str, company: str, website: str, api_key: str) -> Optional[dict]:
    """Return a live card dict, or None if Clay gave us nothing usable."""
    domain = normalize_domain(website)
    payload = await _search_company_by_domain(domain, api_key)
    mapped = map_clay_company(payload, fallback_company=company, fallback_website=website)
    if mapped is None:
        return None
    return {"demo": False, "note": None, "person": {"name": name}, "company": mapped}


# ---------------------------------------------------------------------------
# Demo fallback
# ---------------------------------------------------------------------------

_INDUSTRY_KEYWORDS = [
    (("bank", "finance", "capital", "invest", "pay", "insur"), "Financial Services"),
    (("health", "med", "bio", "pharma", "care"), "Health Care"),
    (("food", "restaurant", "kitchen", "eat"), "Food & Beverage"),
    (("shop", "store", "retail", "mart"), "Retail"),
    (("travel", "hotel", "flight", "tour"), "Travel & Hospitality"),
    (("edu", "school", "learn", "university"), "Education"),
    (("legal", "law", "attorney"), "Legal Services"),
    (("real estate", "property", "realty", "homes"), "Real Estate"),
]

_SIZE_BUCKETS = ["11-50", "51-200", "201-500", "501-1,000", "1,001-5,000"]
_CITIES = [
    "San Francisco, CA, United States",
    "New York, NY, United States",
    "Austin, TX, United States",
    "Seattle, WA, United States",
    "Boston, MA, United States",
    "Denver, CO, United States",
    "Chicago, IL, United States",
    "Los Angeles, CA, United States",
]


def _guess_industry(company: str, domain: str) -> str:
    haystack = f"{company} {domain}".lower()
    for keywords, industry in _INDUSTRY_KEYWORDS:
        if any(k in haystack for k in keywords):
            return industry
    return "Software & Technology"


def demo_card(name: str, company: str, website: str, *, note: Optional[str] = None) -> dict:
    """Build a plausible, clearly-labelled demo card from the form inputs.

    Size/city are picked deterministically from the company name so the same
    input always shows the same card.
    """
    domain = normalize_domain(website)
    digest = int(hashlib.sha256(company.strip().lower().encode()).hexdigest(), 16)
    company_name = company.strip()
    card_company = {
        "name": company_name,
        "domain": domain,
        "website": f"https://{domain}" if domain else website,
        "industry": _guess_industry(company_name, domain),
        "employee_size": _SIZE_BUCKETS[digest % len(_SIZE_BUCKETS)],
        "location": _CITIES[(digest // 7) % len(_CITIES)],
        "description": (
            f"{company_name} is shown here with sample enrichment data so you can "
            "see the full card experience. Connect a Clay API key and this same "
            "card fills with live firmographics from Clay's company search."
        ),
        "linkedin_url": f"https://www.linkedin.com/company/{slugify(company_name)}",
    }
    return {"demo": True, "note": note, "person": {"name": name}, "company": card_company}


# ---------------------------------------------------------------------------
# Entry point used by the API
# ---------------------------------------------------------------------------

async def enrich(name: str, company: str, website: str) -> dict:
    api_key = os.environ.get("CLAY_API_KEY")
    if api_key:
        try:
            card = await enrich_with_clay(name, company, website, api_key)
            if card is not None:
                return card
            note = "Clay returned no match for that company — showing demo data instead."
        except Exception:
            note = "The live Clay lookup failed — showing demo data instead."
        return demo_card(name, company, website, note=note)
    return demo_card(name, company, website)
