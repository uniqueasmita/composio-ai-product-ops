import csv
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from composio import Composio
from composio_gemini import GeminiProvider


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")

if not COMPOSIO_API_KEY:
    raise RuntimeError("COMPOSIO_API_KEY is missing from .env")


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "apps.csv"
OUTPUT_DIR = BASE_DIR / "outputs"

OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# COMPOSIO
# ============================================================

print("Initializing Composio...")

composio = Composio(
    api_key=COMPOSIO_API_KEY,
    provider=GeminiProvider(),
)

session = composio.create(
    user_id="product-ops-research-agent"
)

print(
    f"Composio session: {session.session_id}"
)


# ============================================================
# LOAD APPS
# ============================================================

def load_apps():

    with open(
        DATA_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        return list(csv.DictReader(f))


# ============================================================
# OFFICIAL DOMAIN CHECK
# ============================================================

def is_likely_official(url, app_name):

    try:
        host = urlparse(url).netloc.lower()

        host = host.replace(
            "www.",
            ""
        )

        app_words = (
            app_name.lower()
            .replace(
                " ",
                ""
            )
            .replace(
                ".",
                ""
            )
        )

        # Common official developer domains.
        official_indicators = [
            "developer",
            "developers",
            "docs",
            "api",
            "github.com",
        ]

        # Domain itself contains the product name.
        compact_host = (
            host
            .replace(
                ".com",
                ""
            )
            .replace(
                ".io",
                ""
            )
            .replace(
                ".ai",
                ""
            )
            .replace(
                ".dev",
                ""
            )
        )

        if app_words and app_words in compact_host:
            return True

        if any(
            word in host
            for word in official_indicators
        ):
            return True

        return False

    except Exception:

        return False


# ============================================================
# SEARCH
# ============================================================

def web_search(query):

    return session.execute(
        "COMPOSIO_SEARCH_WEB",
        arguments={
            "query": query
        }
    )


# ============================================================
# EXTRACT CITATIONS
# ============================================================

def extract_citations(response):

    citations = []

    data = getattr(
        response,
        "data",
        None
    )

    if not isinstance(
        data,
        dict
    ):
        return citations

    raw_citations = data.get(
        "citations",
        []
    )

    if not isinstance(
        raw_citations,
        list
    ):
        return citations

    seen = set()

    for citation in raw_citations:

        if not isinstance(
            citation,
            dict
        ):
            continue

        url = citation.get(
            "url"
        )

        if not url:
            continue

        if url in seen:
            continue

        seen.add(url)

        citations.append({

            "title": citation.get(
                "title",
                ""
            ),

            "url": url,

            "author": citation.get(
                "author",
                ""
            ),

            "published_date": citation.get(
                "publishedDate",
                ""
            ),

        })

    return citations


# ============================================================
# FETCH URL CONTENT
# ============================================================

def fetch_url(url):

    try:

        response = session.execute(
            "COMPOSIO_SEARCH_FETCH_URL_CONTENT",
            arguments={
                "url": url
            }
        )

        data = getattr(
            response,
            "data",
            None
        )

        return {
            "url": url,
            "success": True,
            "data": data,
        }

    except Exception as e:

        return {
            "url": url,
            "success": False,
            "error": str(e),
        }


# ============================================================
# MAIN
# ============================================================

def main():

    apps = load_apps()

    # --------------------------------------------------------
    # START WITH ONE APP
    # --------------------------------------------------------

    selected = apps

    all_results = []

    for index, app in enumerate(
        selected,
        start=1
    ):

        print()
        print("=" * 70)
        print(
            f"[{index}/{len(selected)}] "
            f"Researching {app['app']}"
        )
        print("=" * 70)

        queries = [

            (
                f"{app['app']} official API documentation "
                f"authentication OAuth API key"
            ),

            (
                f"{app['app']} official developer API "
                f"REST GraphQL documentation"
            ),

            (
                f"{app['app']} official MCP server "
                f"MCP documentation"
            ),

            (
                f"{app['app']} developer pricing "
                f"API access credentials"
            ),

        ]

        all_citations = []

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        for query in queries:

            print()
            print(
                "Search:",
                query
            )

            try:

                response = web_search(
                    query
                )

                citations = extract_citations(
                    response
                )

                print(
                    f"      Found {len(citations)} citations"
                )

                all_citations.extend(
                    citations
                )

            except Exception as e:

                print(
                    "      Search failed:",
                    e
                )


        # ----------------------------------------------------
        # DEDUPLICATE
        # ----------------------------------------------------

        unique = {}

        for citation in all_citations:

            unique[
                citation["url"]
            ] = citation


        citations = list(
            unique.values()
        )

        # ----------------------------------------------------
        # PRIORITIZE OFFICIAL SOURCES
        # ----------------------------------------------------

        official = []

        other = []

        for citation in citations:

            if is_likely_official(
                citation["url"],
                app["app"]
            ):

                official.append(
                    citation
                )

            else:

                other.append(
                    citation
                )

        ordered = (
            official +
            other
        )

        # ----------------------------------------------------
        # FETCH TOP DOCUMENTATION
        # ----------------------------------------------------

        # Limit initially to 6 pages.
        selected_urls = ordered[:6]

        fetched_pages = []

        print()
        print(
            f"Fetching {len(selected_urls)} "
            "candidate documentation pages..."
        )

        for citation in selected_urls:

            print(
                "      Fetch:",
                citation["url"]
            )

            fetched = fetch_url(
                citation["url"]
            )

            fetched_pages.append(
                {
                    "citation": citation,
                    "content": fetched,
                }
            )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        record = {

            "app": app["app"],

            "category": app["category"],

            "website": app["website"],

            "queries": queries,

            "citations": ordered,

            "fetched_pages": fetched_pages,

        }

        all_results.append(
            record
        )

        output_file = (
            OUTPUT_DIR /
            "evidence_raw.json"
        )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                all_results,
                f,
                indent=2,
                ensure_ascii=False,
                default=str
            )

        print()
        print(
            f"      ✓ Saved evidence for {app['app']}"
        )


    print()
    print("=" * 70)
    print("EVIDENCE COLLECTION COMPLETE")
    print("=" * 70)

    print(
        f"Apps researched: {len(all_results)}"
    )

    print(
        f"Output: {OUTPUT_DIR / 'evidence_raw.json'}"
    )


if __name__ == "__main__":
    main()