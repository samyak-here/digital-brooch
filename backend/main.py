"""Digital Brooch — FastAPI backend.

One endpoint does the work: POST /enrich takes {name, company, website} and
returns an enriched company card. With CLAY_API_KEY set it comes from Clay's
Public API; otherwise (or if that call fails) it is a clearly-labelled demo
card. See clay.py for the details.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from clay import enrich

app = FastAPI(title="Digital Brooch API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class EnrichRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    company: str = Field(min_length=1, max_length=160)
    website: str = Field(min_length=1, max_length=300)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "clay_configured": bool(os.environ.get("CLAY_API_KEY"))}


@app.post("/enrich")
async def enrich_endpoint(req: EnrichRequest) -> dict:
    return await enrich(req.name.strip(), req.company.strip(), req.website.strip())
