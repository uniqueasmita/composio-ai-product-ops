import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY is missing from .env"
    )

BASE_DIR = Path(__file__).resolve().parent.parent

EVIDENCE_FILE = (
    BASE_DIR /
    "outputs" /
    "evidence_raw.json"
)

OUTPUT_FILE = (
    BASE_DIR /
    "outputs" /
    "research_results.json"
)


# ============================================================
# GEMINI
# ============================================================

client = genai.Client(
    api_key=GOOGLE_API_KEY
)


# ============================================================
# STRUCTURED RESULT
# ============================================================

class ResearchResult(BaseModel):

    app: str

    category: str

    description: str = Field(
        description=(
            "One concise sentence explaining what "
            "the product does."
        )
    )

    auth_methods: list[str]

    self_serve: str = Field(
        description=(
            "Free self-serve, Trial self-serve, "
            "Paid self-serve, Admin approval, "
            "Partner/contact-sales, or Unknown."
        )
    )

    gating: str

    api_type: list[str]

    api_breadth: str = Field(
        description=(
            "Narrow, Moderate, Broad, or Unknown."
        )
    )

    mcp: str = Field(
        description="Yes, No, or Unknown."
    )

    buildability: str = Field(
        description=(
            "READY, READY_WITH_REVIEW, or BLOCKED."
        )
    )

    blocker: str

    docs_url: str

    evidence_urls: list[str]

    confidence: str = Field(
        description="High, Medium, or Low."
    )

    notes: str


# ============================================================
# SYSTEM INSTRUCTIONS
# ============================================================

SYSTEM_PROMPT = """
You are an AI Product Operations research analyst.

You are given evidence collected from public web research.

Your job is to turn that evidence into an accurate structured
research record for an AI-agent toolkit feasibility study.

IMPORTANT:

Do NOT perform additional web research.

Use ONLY the evidence provided.

Do NOT invent facts.

If the evidence does not establish a fact, use Unknown.

============================================================
FIELDS
============================================================

description:
One sentence explaining what the product does.

auth_methods:
Only authentication methods explicitly supported by evidence.

Possible examples:

OAuth2
API Key
Bearer Token
Personal Access Token
Basic Auth
JWT
Other
Unknown

self_serve:

Free self-serve
Trial self-serve
Paid self-serve
Admin approval
Partner/contact-sales
Unknown

gating:
Explain why the credential/access path is self-serve or gated.

api_type:

REST
GraphQL
SDK
CLI
SOAP
Other
Unknown

api_breadth:

Narrow
Moderate
Broad
Unknown

mcp:

Yes
No
Unknown

Only mark Yes if evidence supports an existing MCP server,
integration, or official MCP documentation.

buildability:

READY:
A documented API exists, authentication is practical,
and there is no major access blocker.

READY_WITH_REVIEW:
Technically possible but there is a meaningful caveat.

BLOCKED:
A major blocker prevents practical toolkit development.

blocker:
State the main blocker, or "None".

confidence:

confidence:

High:
Multiple first-party sources directly support the important
claims.

Medium:
At least one reliable first-party source supports the main
claims, but some fields require reasonable interpretation.

Low:
Evidence is missing, contradictory, inaccessible, or mostly
secondary.

Do NOT use Low merely because the research is incomplete.
Use Low only when the available evidence genuinely cannot
support the conclusion.

============================================================
EVIDENCE RULE
============================================================

Every important conclusion should be traceable to one or more
provided URLs.

Prefer official first-party documentation.

Never treat a marketing statement as proof of API capability
when technical documentation is available.

If sources conflict or evidence is incomplete, explain that
in notes.

Before producing the structured result, internally check:

- Is authentication explicitly documented?
- Is an API explicitly documented?
- Is there evidence about credential acquisition?
- Is MCP explicitly documented?
- Which URLs support each important conclusion?

Do not expose this reasoning in the final response.
Use the URLs in evidence_urls to preserve traceability.

Return ONLY the structured result.
"""


# ============================================================
# LOAD EVIDENCE
# ============================================================

def load_evidence():

    with open(
        EVIDENCE_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# PREPARE EVIDENCE
# ============================================================

def prepare_evidence(record):

    evidence = {

        "app": record["app"],

        "category": record["category"],

        "website": record["website"],

        "search_queries": record["queries"],

        "sources": []

    }

    for page in record.get(
        "fetched_pages",
        []
    ):

        citation = page.get(
            "citation",
            {}
        )

        content = page.get(
            "content",
            {}
        )

        evidence["sources"].append({

            "title": citation.get(
                "title",
                ""
            ),

            "url": citation.get(
                "url",
                ""
            ),

            "author": citation.get(
                "author",
                ""
            ),

           "content": str(
    content.get(
        "data",
        ""
    )
)[:12000]

        })

    return evidence


# ============================================================
# RESEARCH ONE APP
# ============================================================

async def research_app(record):

    evidence = prepare_evidence(
        record
    )

    prompt = f"""
Analyze this evidence.

APPLICATION:
{record['app']}

CATEGORY:
{record['category']}

EVIDENCE:
{json.dumps(
    evidence,
    indent=2,
    ensure_ascii=False,
    default=str
)}
"""

    try:

        response = client.models.generate_content(

            model="gemini-3.1-flash-lite",

            contents=(
                SYSTEM_PROMPT +
                "\n\n" +
                prompt
            ),

            config=types.GenerateContentConfig(

                response_mime_type="application/json",

                response_schema=ResearchResult

            )
        )

        result = response.parsed

        if isinstance(
            result,
            ResearchResult
        ):

            return result.model_dump()

        return json.loads(
            response.text
        )

    except Exception as e:

        return {

            "app": record["app"],

            "category": record["category"],

            "description": "Classification failed.",

            "auth_methods": ["Unknown"],

            "self_serve": "Unknown",

            "gating": "Unknown",

            "api_type": ["Unknown"],

            "api_breadth": "Unknown",

            "mcp": "Unknown",

            "buildability": "READY_WITH_REVIEW",

            "blocker": "Classification error",

            "docs_url": record["website"],

            "evidence_urls": [],

            "confidence": "Low",

            "notes": str(e)

        }


# ============================================================
# MAIN
# ============================================================

async def main():

    records = load_evidence()[:1]

    print()
    print("=" * 70)
    print("AI PRODUCT OPS RESEARCH AGENT")
    print("=" * 70)

    print(
        f"Evidence records: {len(records)}"
    )

    results = []

    for index, record in enumerate(
        records,
        start=1
    ):

        print()

        print(
            f"[{index}/{len(records)}] "
            f"Classifying {record['app']}..."
        )

        result = await research_app(
            record
        )

        results.append(
            result
        )

        print(
            f"      ✓ {result['app']} | "
            f"{result['buildability']} | "
            f"{result['confidence']}"
        )

        # Incremental save.

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                results,
                f,
                indent=2,
                ensure_ascii=False
            )

    print()
    print("=" * 70)
    print("CLASSIFICATION COMPLETE")
    print("=" * 70)

    print(
        f"Results: {OUTPUT_FILE}"
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
