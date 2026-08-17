from typing import List, Literal
from pydantic import BaseModel, Field


class ResearchResult(BaseModel):
    app: str
    category: str
    description: str

    auth_methods: List[str] = Field(default_factory=list)
    self_serve: str
    gating: str

    api_type: List[str] = Field(default_factory=list)
    api_breadth: str

    mcp: str

    buildability: Literal[
        "READY",
        "READY_WITH_REVIEW",
        "BLOCKED"
    ]

    blocker: str

    docs_url: str
    evidence_urls: List[str] = Field(default_factory=list)

    confidence: Literal[
        "High",
        "Medium",
        "Low"
    ]

    notes: str