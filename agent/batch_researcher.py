import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY is missing from .env")

BASE_DIR = Path(__file__).resolve().parent.parent

EVIDENCE_FILE = BASE_DIR / "outputs" / "evidence_raw.json"

FIRST_PASS_FILE = (
    BASE_DIR
    / "outputs"
    / "research_results_first_pass.json"
)

OUTPUT_FILE = (
    BASE_DIR
    / "outputs"
    / "research_results.json"
)

MODEL = "gemini-3.1-flash-lite"

# Smaller batches reduce 503/high-demand failures.
BATCH_SIZE = 6

# Retry temporary Gemini 503 errors.
MAX_RETRIES = 3


# ============================================================
# GEMINI
# ============================================================

client = genai.Client(
    api_key=GOOGLE_API_KEY
)


# ============================================================
# SCHEMA
# ============================================================

class ResearchResult(BaseModel):
    app: str
    category: str
    description: str
    auth_methods: list[str]
    self_serve: str
    gating: str
    api_type: list[str]
    api_breadth: str
    mcp: str
    buildability: str
    blocker: str
    docs_url: str
    evidence_urls: list[str]
    confidence: str
    notes: str


class BatchResults(BaseModel):
    results: list[ResearchResult]


# ============================================================
# PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an AI Product Operations research analyst.

You are analyzing multiple applications using ONLY the
provided evidence.

Do not perform additional web research.

Do not invent facts.

If evidence does not support a claim, use Unknown.

IMPORTANT:
Return exactly one ResearchResult for every application.

============================================================
FIELDS
============================================================

description:
One concise sentence describing the application.

auth_methods:
Use only methods explicitly supported by evidence.

Examples:
OAuth2
API Key
Bearer Token
Personal Access Token
Basic Auth
JWT
Other
Unknown

self_serve:
Use one of:

Free self-serve
Trial self-serve
Paid self-serve
Admin approval
Partner/contact-sales
Unknown

gating:
Explain the credential/access requirement.

api_type:
Use only documented API/interface types.

Examples:
REST
GraphQL
SOAP
gRPC
SDK
CLI
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

Only use Yes when evidence explicitly supports an existing
MCP server/integration/documentation.

buildability:
READY
READY_WITH_REVIEW
BLOCKED

READY:
Documented API + workable authentication + no major blocker.

READY_WITH_REVIEW:
Technically possible but has meaningful access, licensing,
authentication, or evidence caveats.

BLOCKED:
A major documented blocker prevents practical toolkit
development.

blocker:
State the main blocker, or None.

confidence:
High:
Multiple strong first-party sources support the conclusions.

Medium:
The main conclusions are supported but some fields require
interpretation.

Low:
Evidence is missing, contradictory, inaccessible, or weak.

Do not use Low merely because some fields are Unknown.

evidence_urls:
Include the URLs actually supporting the conclusions.

docs_url:
Use the strongest official developer documentation URL.

============================================================
CRITICAL ACCURACY RULE
============================================================

Do not infer an authentication method simply because an API
normally uses it.

Do not infer MCP merely because an application can theoretically
be used by an agent.

Do not infer paid access merely because the company sells paid
plans.

Distinguish:

- public documentation
- ability to obtain credentials
- actual API access
- admin/enterprise approval
- partnership/contact-sales requirements

Prefer first-party documentation.

Return ONLY the structured JSON.
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
# COMPACT EVIDENCE
# ============================================================

def compact_record(record):

    sources = []

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

        raw = content.get(
            "data",
            ""
        )

        # Keep enough evidence while limiting prompt size.
        raw_text = str(raw)[:5000]

        sources.append({

            "title": citation.get(
                "title",
                ""
            ),

            "url": citation.get(
                "url",
                ""
            ),

            "content": raw_text

        })

    return {

        "app": record.get(
            "app"
        ),

        "category": record.get(
            "category"
        ),

        "website": record.get(
            "website"
        ),

        "sources": sources

    }


# ============================================================
# CLASSIFY BATCH
# ============================================================

def classify_batch(records):

    evidence = [
        compact_record(r)
        for r in records
    ]

    prompt = (
        SYSTEM_PROMPT
        + "\n\nAPPLICATION EVIDENCE:\n"
        + json.dumps(
            evidence,
            indent=2,
            ensure_ascii=False
        )
    )

    response = client.models.generate_content(

        model=MODEL,

        contents=prompt,

        config=types.GenerateContentConfig(

            response_mime_type="application/json",

            response_schema=BatchResults

        )

    )

    parsed = response.parsed

    if isinstance(
        parsed,
        BatchResults
    ):

        return [
            r.model_dump()
            for r in parsed.results
        ]

    return json.loads(
        response.text
    )["results"]


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(results):

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


# ============================================================
# MAIN
# ============================================================

async def main():

    evidence = load_evidence()

    print()
    print("=" * 70)
    print("BATCH AI PRODUCT OPS CLASSIFIER")
    print("=" * 70)

    print(
        f"Total evidence records: {len(evidence)}"
    )

    # --------------------------------------------------------
    # RESUME FROM EXISTING RESULTS
    # --------------------------------------------------------

    existing_results = []

    if OUTPUT_FILE.exists():

        try:

            with open(
                OUTPUT_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                existing_results = json.load(f)

            if not isinstance(
                existing_results,
                list
            ):

                existing_results = []

        except Exception:

            existing_results = []

    completed_apps = {
        r.get("app")
        for r in existing_results
        if r.get("app")
    }

    remaining = [
        r
        for r in evidence
        if r.get("app") not in completed_apps
    ]

    results = existing_results

    print(
        f"Already completed: {len(completed_apps)}"
    )

    print(
        f"Remaining apps: {len(remaining)}"
    )

    if not remaining:

        print()
        print("All 100 applications are already classified.")
        print(
            f"Output: {OUTPUT_FILE}"
        )
        return

    total_batches = (
        (len(remaining) + BATCH_SIZE - 1)
        // BATCH_SIZE
    )

    print(
        f"Batch size: {BATCH_SIZE}"
    )

    print(
        f"Gemini requests required: {total_batches}"
    )

    # --------------------------------------------------------
    # BATCH PROCESSING
    # --------------------------------------------------------

    for start in range(
        0,
        len(remaining),
        BATCH_SIZE
    ):

        batch = remaining[
            start:start + BATCH_SIZE
        ]

        batch_number = (
            start // BATCH_SIZE
        ) + 1

        print()
        print(
            f"[Batch {batch_number}/{total_batches}] "
            f"{batch[0]['app']} → "
            f"{batch[-1]['app']}"
        )

        batch_results = None

        # ----------------------------------------------------
        # RETRY TEMPORARY 503 ERRORS
        # ----------------------------------------------------

        for attempt in range(
            1,
            MAX_RETRIES + 1
        ):

            try:

                batch_results = classify_batch(
                    batch
                )

                break

            except Exception as e:

                error_text = str(e)

                is_temporary = (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                )

                if (
                    is_temporary
                    and attempt < MAX_RETRIES
                ):

                    wait_seconds = 20 * attempt

                    print(
                        f"      Gemini temporarily unavailable "
                        f"(attempt {attempt}/{MAX_RETRIES})."
                    )

                    print(
                        f"      Retrying in "
                        f"{wait_seconds}s..."
                    )

                    time.sleep(
                        wait_seconds
                    )

                else:

                    print(
                        f"      ✗ Batch failed: {e}"
                    )

                    print()
                    print(
                        "Stopping safely."
                    )

                    print(
                        f"Completed results preserved: "
                        f"{len(results)}/100"
                    )

                    save_results(
                        results
                    )

                    return

        # ----------------------------------------------------
        # VALIDATE BATCH
        # ----------------------------------------------------

        if not batch_results:

            print(
                "      ✗ No results returned."
            )

            save_results(
                results
            )

            return

        expected_names = {
            r["app"]
            for r in batch
        }

        returned_names = {
            r.get("app")
            for r in batch_results
        }

        missing = (
            expected_names
            - returned_names
        )

        unexpected = (
            returned_names
            - expected_names
        )

        if missing:

            print(
                "      WARNING: Missing results:",
                sorted(missing)
            )

            print(
                "      Batch will NOT be committed "
                "because results are incomplete."
            )

            save_results(
                results
            )

            return

        if unexpected:

            print(
                "      WARNING: Unexpected apps:",
                sorted(unexpected)
            )

        # ----------------------------------------------------
        # SAVE BATCH
        # ----------------------------------------------------

        results.extend(
            batch_results
        )

        save_results(
            results
        )

        print(
            f"      ✓ Received "
            f"{len(batch_results)} results"
        )

        print(
            f"      ✓ Saved progress: "
            f"{len(results)}/100"
        )

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("BATCH CLASSIFICATION COMPLETE")
    print("=" * 70)

    print(
        f"Results produced: {len(results)}/100"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )