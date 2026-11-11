"""Tests for the Digital Brooch backend.

Covers three paths:
1. Demo mode (no CLAY_API_KEY) via the real HTTP endpoint.
2. The Clay response mapper, fed a representative company-search payload.
3. The full live path with the Clay HTTP call stubbed out, plus the
   failure fallback (stub raises -> labelled demo card).
"""

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

import clay
from main import app

client = TestClient(app)

PAYLOAD = {"name": "Samyak Jain", "company": "Acme Robotics", "website": "https://www.acmerobotics.com/about"}

# Representative Clay company-search response shape (results envelope,
# firmographic fields). The mapper is intentionally tolerant of variants;
# this is the shape it must handle without crashing.
STUB_CLAY_RESPONSE = {
    "results": [
        {
            "name": "Acme Robotics",
            "domain": "acmerobotics.com",
            "website": "https://acmerobotics.com",
            "industry": "Industrial Automation",
            "employee_count_range": "51-200",
            "city": "Pittsburgh",
            "state": "PA",
            "country": "United States",
            "description": "Acme Robotics builds warehouse automation systems.",
            "linkedin_url": "https://www.linkedin.com/company/acme-robotics",
        }
    ]
}


@pytest.fixture(autouse=True)
def no_clay_key(monkeypatch):
    monkeypatch.delenv("CLAY_API_KEY", raising=False)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["clay_configured"] is False


def test_enrich_demo_mode():
    resp = client.post("/enrich", json=PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["demo"] is True
    assert body["person"]["name"] == "Samyak Jain"
    company = body["company"]
    assert company["name"] == "Acme Robotics"
    # Domain is normalized: scheme, www. and path stripped.
    assert company["domain"] == "acmerobotics.com"
    for field in ("website", "industry", "employee_size", "location", "description", "linkedin_url"):
        assert company[field], f"demo card missing {field}"


def test_mapper_handles_stub_response():
    card = clay.map_clay_company(
        STUB_CLAY_RESPONSE,
        fallback_company="Acme Robotics",
        fallback_website="https://acmerobotics.com",
    )
    assert card is not None
    assert card["name"] == "Acme Robotics"
    assert card["domain"] == "acmerobotics.com"
    assert card["industry"] == "Industrial Automation"
    assert card["employee_size"] == "51-200"
    assert card["location"] == "Pittsburgh, PA, United States"
    assert card["linkedin_url"].endswith("/acme-robotics")


def test_mapper_returns_none_for_empty_payload():
    assert clay.map_clay_company({"results": []}, fallback_company="X", fallback_website="x.com") is None
    assert clay.map_clay_company([], fallback_company="X", fallback_website="x.com") is None
    assert clay.map_clay_company(None, fallback_company="X", fallback_website="x.com") is None


def test_live_path_with_stubbed_clay(monkeypatch):
    async def fake_search(domain, api_key):
        assert domain == "acmerobotics.com"
        assert api_key == "test-key"
        return STUB_CLAY_RESPONSE

    monkeypatch.setattr(clay, "_search_company_by_domain", fake_search)
    monkeypatch.setenv("CLAY_API_KEY", "test-key")
    body = asyncio.run(clay.enrich(**PAYLOAD))
    assert body["demo"] is False
    assert body["company"]["industry"] == "Industrial Automation"
    assert body["company"]["employee_size"] == "51-200"


def test_live_failure_falls_back_to_demo(monkeypatch):
    async def boom(domain, api_key):
        raise RuntimeError("Clay is down")

    monkeypatch.setattr(clay, "_search_company_by_domain", boom)
    monkeypatch.setenv("CLAY_API_KEY", "test-key")
    body = asyncio.run(clay.enrich(**PAYLOAD))
    assert body["demo"] is True
    assert body["note"] and "failed" in body["note"]
    assert body["company"]["name"] == "Acme Robotics"


def test_domain_normalization():
    assert clay.normalize_domain("https://www.Example.com/path?q=1") == "example.com"
    assert clay.normalize_domain("example.com") == "example.com"
    assert clay.normalize_domain("http://sub.example.co.uk") == "sub.example.co.uk"
