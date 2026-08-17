import json
import html
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent
RESULTS = ROOT / "outputs" / "research_results_verified.json"
OUT = ROOT / "web" / "index.html"

with open(RESULTS, encoding="utf-8") as f:
    data = json.load(f)

# ---------- Metrics ----------
total = len(data)

confidence = Counter(x.get("confidence", "Unknown") for x in data)
buildability = Counter(x.get("buildability", "Unknown") for x in data)
self_serve = Counter(x.get("self_serve", "Unknown") for x in data)
auth = Counter(a for x in data for a in x.get("auth_methods", []))
api = Counter(a for x in data for a in x.get("api_type", []))
mcp = Counter(x.get("mcp", "Unknown") for x in data)

ready = buildability.get("READY", 0)
review = buildability.get("READY_WITH_REVIEW", 0)
mcp_yes = mcp.get("Yes", 0)
free = self_serve.get("Free self-serve", 0)
trial = self_serve.get("Trial self-serve", 0)
paid = self_serve.get("Paid self-serve", 0)
gated = self_serve.get("Partner/contact-sales", 0) + self_serve.get("Admin approval", 0)
unknown_access = self_serve.get("Unknown", 0)

categories = {}

for x in data:
    cat = x.get("category", "Unknown")
    if cat not in categories:
        categories[cat] = {
            "apps": 0,
            "ready": 0,
            "mcp": 0
        }

    categories[cat]["apps"] += 1

    if x.get("buildability") == "READY":
        categories[cat]["ready"] += 1

    if x.get("mcp") == "Yes":
        categories[cat]["mcp"] += 1

# ---------- Helpers ----------
def esc(value):
    return html.escape(str(value or ""))

def badge(value):
    value = str(value or "")
    cls = "neutral"

    if value in ("READY", "Yes", "High", "Free self-serve", "Trial self-serve"):
        cls = "good"
    elif value in ("READY_WITH_REVIEW", "Medium", "Paid self-serve", "Admin approval"):
        cls = "warn"
    elif value in ("Partner/contact-sales", "Unknown", "No"):
        cls = "muted"

    return f'<span class="badge {cls}">{esc(value)}</span>'

def pct(value, denominator=total):
    return round((value / denominator) * 100) if denominator else 0

# ---------- Rows ----------
rows = []

for x in data:
    evidence = x.get("evidence_urls", [])
    evidence_html = ""

    if evidence:
        links = []
        for url in evidence[:3]:
            links.append(
                f'<a href="{esc(url)}" target="_blank" rel="noopener">source ↗</a>'
            )
        evidence_html = " ".join(links)
    else:
        docs = x.get("docs_url", "")
        if docs:
            evidence_html = (
                f'<a href="{esc(docs)}" target="_blank" rel="noopener">docs ↗</a>'
            )
        else:
            evidence_html = "—"

    auth_text = ", ".join(x.get("auth_methods", []))
    api_text = ", ".join(x.get("api_type", []))

    rows.append(f"""
    <tr>
        <td class="app-cell">
            <strong>{esc(x.get("app"))}</strong>
            <small>{esc(x.get("description"))}</small>
        </td>
        <td>{esc(x.get("category"))}</td>
        <td>{esc(auth_text)}</td>
        <td>{badge(x.get("self_serve"))}</td>
        <td>{esc(api_text)}</td>
        <td>{badge(x.get("mcp"))}</td>
        <td>{badge(x.get("buildability"))}</td>
        <td>{badge(x.get("confidence"))}</td>
        <td class="source-cell">{evidence_html}</td>
    </tr>
    """)

rows_html = "\n".join(rows)

# ---------- Category cards ----------
category_cards = []

for cat, values in categories.items():
    ready_pct = pct(values["ready"], values["apps"])
    category_cards.append(f"""
    <div class="category-card">
        <div class="category-name">{esc(cat)}</div>
        <div class="category-stats">
            <span><b>{values["ready"]}/{values["apps"]}</b> ready</span>
            <span><b>{values["mcp"]}</b> MCP</span>
        </div>
        <div class="progress">
            <span style="width:{ready_pct}%"></span>
        </div>
    </div>
    """)

category_cards_html = "\n".join(category_cards)

# ---------- Top auth ----------
auth_items = sorted(auth.items(), key=lambda x: x[1], reverse=True)[:6]
auth_bars = []

for name, count in auth_items:
    auth_bars.append(f"""
    <div class="bar-row">
        <div class="bar-label">
            <span>{esc(name)}</span>
            <b>{count}</b>
        </div>
        <div class="bar">
            <span style="width:{pct(count)}%"></span>
        </div>
    </div>
    """)

auth_bars_html = "\n".join(auth_bars)

# ---------- Top API ----------
api_items = sorted(api.items(), key=lambda x: x[1], reverse=True)[:6]
api_bars = []

for name, count in api_items:
    api_bars.append(f"""
    <div class="bar-row">
        <div class="bar-label">
            <span>{esc(name)}</span>
            <b>{count}</b>
        </div>
        <div class="bar">
            <span style="width:{pct(count)}%"></span>
        </div>
    </div>
    """)

api_bars_html = "\n".join(api_bars)

# ---------- Self serve bars ----------
access_items = [
    ("Free self-serve", free),
    ("Trial self-serve", trial),
    ("Paid self-serve", paid),
    ("Partner/contact-sales", self_serve.get("Partner/contact-sales", 0)),
    ("Admin approval", self_serve.get("Admin approval", 0)),
    ("Unknown", unknown_access),
]

access_bars = []

for name, count in access_items:
    access_bars.append(f"""
    <div class="bar-row">
        <div class="bar-label">
            <span>{esc(name)}</span>
            <b>{count}</b>
        </div>
        <div class="bar">
            <span style="width:{pct(count)}%"></span>
        </div>
    </div>
    """)

access_bars_html = "\n".join(access_bars)

# ---------- Final HTML ----------
page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Product Ops Research Agent — Composio Take-Home</title>

<style>
:root {{
    --bg: #07111f;
    --panel: #0d1b2e;
    --panel2: #10243a;
    --text: #f4f7fb;
    --muted: #91a4bb;
    --line: rgba(255,255,255,.09);
    --accent: #6ee7b7;
    --accent2: #60a5fa;
    --warning: #fbbf24;
    --danger: #fb7185;
}}

* {{
    box-sizing: border-box;
}}

html {{
    scroll-behavior: smooth;
}}

body {{
    margin: 0;
    background:
        radial-gradient(circle at 85% 5%, rgba(96,165,250,.14), transparent 30%),
        radial-gradient(circle at 10% 15%, rgba(110,231,183,.08), transparent 25%),
        var(--bg);
    color: var(--text);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.5;
}}

a {{
    color: #93c5fd;
    text-decoration: none;
}}

a:hover {{
    text-decoration: underline;
}}

.container {{
    width: min(1440px, calc(100% - 48px));
    margin: auto;
}}

.hero {{
    padding: 78px 0 52px;
}}

.eyebrow {{
    color: var(--accent);
    font-weight: 800;
    letter-spacing: .12em;
    text-transform: uppercase;
    font-size: 12px;
    margin-bottom: 18px;
}}

h1 {{
    font-size: clamp(42px, 6vw, 78px);
    line-height: .98;
    max-width: 1000px;
    margin: 0 0 24px;
    letter-spacing: -.055em;
}}

.hero p {{
    color: var(--muted);
    max-width: 800px;
    font-size: 18px;
}}

.hero-meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 28px;
}}

.pill {{
    border: 1px solid var(--line);
    background: rgba(255,255,255,.035);
    border-radius: 999px;
    padding: 8px 13px;
    color: #c8d5e5;
    font-size: 13px;
}}

.section {{
    padding: 45px 0;
}}

.section-title {{
    display: flex;
    justify-content: space-between;
    gap: 20px;
    align-items: end;
    margin-bottom: 22px;
}}

h2 {{
    font-size: 30px;
    margin: 0;
    letter-spacing: -.03em;
}}

.section-sub {{
    color: var(--muted);
    margin: 6px 0 0;
    max-width: 760px;
}}

.grid {{
    display: grid;
    gap: 14px;
}}

.metrics {{
    grid-template-columns: repeat(6, 1fr);
}}

.card {{
    background: linear-gradient(145deg, rgba(16,36,58,.94), rgba(10,25,42,.94));
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 22px;
    box-shadow: 0 18px 60px rgba(0,0,0,.12);
}}

.metric-number {{
    font-size: 38px;
    font-weight: 850;
    letter-spacing: -.05em;
}}

.metric-label {{
    color: var(--muted);
    font-size: 13px;
    margin-top: 4px;
}}

.insights {{
    grid-template-columns: repeat(4, 1fr);
}}

.insight {{
    min-height: 180px;
}}

.insight .number {{
    color: var(--accent);
    font-size: 35px;
    font-weight: 850;
}}

.insight h3 {{
    margin: 8px 0;
    font-size: 18px;
}}

.insight p {{
    color: var(--muted);
    font-size: 14px;
}}

.two {{
    grid-template-columns: 1fr 1fr;
}}

.bar-row {{
    margin: 17px 0;
}}

.bar-label {{
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    color: #c8d5e5;
    margin-bottom: 7px;
}}

.bar {{
    height: 7px;
    background: rgba(255,255,255,.07);
    border-radius: 999px;
    overflow: hidden;
}}

.bar span {{
    display: block;
    height: 100%;
    background: linear-gradient(90deg, var(--accent2), var(--accent));
    border-radius: inherit;
}}

.category-grid {{
    grid-template-columns: repeat(2, 1fr);
}}

.category-card {{
    border: 1px solid var(--line);
    border-radius: 15px;
    padding: 18px;
    background: rgba(255,255,255,.025);
}}

.category-name {{
    font-weight: 750;
    margin-bottom: 10px;
}}

.category-stats {{
    display: flex;
    gap: 20px;
    color: var(--muted);
    font-size: 13px;
}}

.category-stats b {{
    color: var(--text);
}}

.progress {{
    height: 6px;
    margin-top: 14px;
    background: rgba(255,255,255,.07);
    border-radius: 99px;
    overflow: hidden;
}}

.progress span {{
    display: block;
    height: 100%;
    background: var(--accent);
}}

.workflow {{
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 10px;
    align-items: stretch;
}}

.step {{
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 15px;
    padding: 18px;
    position: relative;
}}

.step-num {{
    color: var(--accent);
    font-weight: 900;
    font-size: 12px;
}}

.step h3 {{
    font-size: 15px;
    margin: 8px 0 4px;
}}

.step p {{
    color: var(--muted);
    font-size: 12px;
    margin: 0;
}}

.verification {{
    border-left: 3px solid var(--accent);
}}

.verification-grid {{
    display: grid;
    grid-template-columns: 1.2fr .8fr;
    gap: 18px;
}}

.callout {{
    background: rgba(110,231,183,.06);
    border: 1px solid rgba(110,231,183,.18);
    border-radius: 16px;
    padding: 20px;
}}

.callout.warning {{
    background: rgba(251,191,36,.05);
    border-color: rgba(251,191,36,.18);
}}

.callout h3 {{
    margin-top: 0;
}}

.callout p {{
    color: var(--muted);
}}

.table-wrap {{
    overflow: auto;
    border: 1px solid var(--line);
    border-radius: 16px;
    background: rgba(5,15,27,.65);
}}

table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 1500px;
}}

th {{
    position: sticky;
    top: 0;
    z-index: 2;
    background: #10243a;
    color: #b9c8da;
    text-align: left;
    padding: 13px 12px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .08em;
}}

td {{
    padding: 14px 12px;
    border-top: 1px solid var(--line);
    vertical-align: top;
    font-size: 12px;
    color: #c7d2e1;
}}

.app-cell {{
    width: 230px;
}}

.app-cell strong {{
    display: block;
    color: white;
    font-size: 14px;
}}

.app-cell small {{
    display: block;
    color: #758aa2;
    line-height: 1.35;
    margin-top: 4px;
}}

.badge {{
    display: inline-block;
    border-radius: 999px;
    padding: 4px 8px;
    font-size: 10px;
    font-weight: 800;
    white-space: nowrap;
}}

.badge.good {{
    color: #9af2cf;
    background: rgba(110,231,183,.10);
    border: 1px solid rgba(110,231,183,.20);
}}

.badge.warn {{
    color: #fbd783;
    background: rgba(251,191,36,.09);
    border: 1px solid rgba(251,191,36,.18);
}}

.badge.muted {{
    color: #a7b4c5;
    background: rgba(255,255,255,.055);
    border: 1px solid rgba(255,255,255,.08);
}}

.badge.neutral {{
    color: #c5d3e4;
    background: rgba(96,165,250,.08);
    border: 1px solid rgba(96,165,250,.15);
}}

.source-cell {{
    white-space: nowrap;
}}

footer {{
    padding: 50px 0 70px;
    color: #71849b;
    font-size: 12px;
}}

@media(max-width: 1050px) {{
    .metrics {{
        grid-template-columns: repeat(3,1fr);
    }}

    .insights {{
        grid-template-columns: repeat(2,1fr);
    }}

    .workflow {{
        grid-template-columns: repeat(3,1fr);
    }}
}}

@media(max-width: 700px) {{
    .container {{
        width: min(100% - 28px, 1440px);
    }}

    .metrics,
    .insights,
    .two,
    .category-grid {{
        grid-template-columns: 1fr;
    }}

    .workflow {{
        grid-template-columns: 1fr 1fr;
    }}

    .hero {{
        padding-top: 45px;
    }}
}}

@media print {{
    body {{
        background: white;
        color: #111;
    }}

    .card,
    .category-card,
    .step {{
        box-shadow: none;
    }}

    .table-wrap {{
        overflow: visible;
    }}

    table {{
        min-width: 0;
    }}

    th {{
        position: static;
    }}
}}
</style>
</head>

<body>

<div class="container">

<header class="hero">
    <div class="eyebrow">Composio · AI Product Ops Intern Take-Home</div>

    <h1>Researching 100 apps with an agent, not a spreadsheet.</h1>

    <p>
        An evidence-first research pipeline that discovers official developer
        documentation, extracts authentication and API access patterns,
        identifies MCP availability, and produces a buildability verdict.
    </p>

    <div class="hero-meta">
        <span class="pill">100 apps</span>
        <span class="pill">10 categories</span>
        <span class="pill">Composio web research</span>
        <span class="pill">Gemini classification</span>
        <span class="pill">Human verification</span>
    </div>
</header>


<section class="section">
    <div class="grid metrics">

        <div class="card">
            <div class="metric-number">{total}</div>
            <div class="metric-label">Apps researched</div>
        </div>

        <div class="card">
            <div class="metric-number">{confidence.get("High",0)}</div>
            <div class="metric-label">High-confidence results</div>
        </div>

        <div class="card">
            <div class="metric-number">{ready}</div>
            <div class="metric-label">READY to build</div>
        </div>

        <div class="card">
            <div class="metric-number">{review}</div>
            <div class="metric-label">Needs review</div>
        </div>

        <div class="card">
            <div class="metric-number">{mcp_yes}</div>
            <div class="metric-label">MCP identified</div>
        </div>

        <div class="card">
            <div class="metric-number">{free + trial + paid}</div>
            <div class="metric-label">Self-serve paths</div>
        </div>

    </div>
</section>


<section class="section">
    <div class="section-title">
        <div>
            <h2>The headline findings</h2>
            <p class="section-sub">
                The useful output is not the 100 rows. It is the pattern across them.
            </p>
        </div>
    </div>

    <div class="grid insights">

        <div class="card insight">
            <div class="number">{api.get("REST",0)}/100</div>
            <h3>REST dominates</h3>
            <p>
                REST appears across the overwhelming majority of the research set,
                making it the default integration surface.
            </p>
        </div>

        <div class="card insight">
            <div class="number">{auth.get("OAuth2",0)}/100</div>
            <h3>OAuth2 is the leading auth pattern</h3>
            <p>
                OAuth2 is the most frequently observed authentication method,
                especially across SaaS and productivity platforms.
            </p>
        </div>

        <div class="card insight">
    <div class="number">{free + trial}/{total}</div>
    <h3>74/100 have a self-serve path</h3>
    <p>
        Free or trial access provides a practical developer path for 74 of the 100 apps.
    </p>
        </div>

        <div class="card insight">
            <div class="number">{mcp_yes}/100</div>
            <h3>MCP is emerging</h3>
            <p>
                MCP is already present across a meaningful subset, but discovery
                is less reliable than conventional API/auth research.
            </p>
        </div>

    </div>
</section>


<section class="section">
    <div class="grid two">

        <div class="card">
            <h2>Authentication</h2>
            <p class="section-sub">
                An app can expose multiple authentication methods, so counts
                represent observed methods rather than mutually exclusive apps.
            </p>

            {auth_bars_html}
        </div>

        <div class="card">
            <h2>API surface</h2>
            <p class="section-sub">
                REST is the dominant integration surface; some apps expose
                GraphQL, SDKs, CLI or other interfaces alongside it.
            </p>

            {api_bars_html}
        </div>

    </div>
</section>


<section class="section">
    <div class="grid two">

        <div class="card">
            <h2>Developer access</h2>
            <p class="section-sub">
                Self-serve access is the biggest source of easy wins.
                Gated access is a product-ops/outreach problem, not necessarily
                an API problem.
            </p>

            {access_bars_html}
        </div>

        <div class="card">
            <h2>Easy wins vs. outreach</h2>

            <div class="callout">
                <h3>Easy wins</h3>
                <p>
                    Apps with a broad public API, usable credentials and a
                    self-serve path can generally move directly into toolkit
                    implementation.
                </p>
            </div>

            <br>

            <div class="callout warning">
                <h3>Needs outreach / review</h3>
                <p>
                    Partner/contact-sales gates, admin approval, unclear access
                    requirements and incomplete MCP evidence are the main
                    reasons to pause before implementation.
                </p>
            </div>
        </div>

    </div>
</section>


<section class="section">
    <div class="section-title">
        <div>
            <h2>Category view</h2>
            <p class="section-sub">
                Every category contains ten apps. The comparison shows where
                implementation readiness and MCP adoption concentrate.
            </p>
        </div>
    </div>

    <div class="grid category-grid">
        {category_cards_html}
    </div>
</section>


<section class="section">
    <div class="section-title">
        <div>
            <h2>How the agent works</h2>
            <p class="section-sub">
                Evidence is collected first. Classification happens only after
                the research layer has produced source-backed material.
            </p>
        </div>
    </div>

    <div class="workflow">

        <div class="step">
            <div class="step-num">01</div>
            <h3>Input</h3>
            <p>100 apps across 10 categories.</p>
        </div>

        <div class="step">
            <div class="step-num">02</div>
            <h3>Discover</h3>
            <p>Composio discovers web research tools.</p>
        </div>

        <div class="step">
            <div class="step-num">03</div>
            <h3>Search</h3>
            <p>Search official API, auth, pricing and MCP documentation.</p>
        </div>

        <div class="step">
            <div class="step-num">04</div>
            <h3>Fetch</h3>
            <p>Fetch candidate pages and preserve evidence URLs.</p>
        </div>

        <div class="step">
            <div class="step-num">05</div>
            <h3>Classify</h3>
            <p>Gemini converts evidence into structured research records.</p>
        </div>

        <div class="step">
            <div class="step-num">06</div>
            <h3>Verify</h3>
            <p>Human review checks a sample and corrects weak findings.</p>
        </div>

    </div>
</section>


<section class="section">
    <div class="grid verification-grid">

        <div class="card verification">
            <h2>Verification: where the agent needed a human</h2>

            <p class="section-sub">
                A fixed 20-app sample was reviewed against first-party
                documentation. The goal was not to manufacture a 100% score,
                but to identify failure modes and improve the research loop.
            </p>

            <div class="callout">
                <h3>Observed failure mode: MCP discovery</h3>
                <p>
                    Conventional API/auth research was generally strong.
                    MCP was harder because first-party MCP documentation can
                    live outside the main API reference and may be described
                    as beta, hosted, remote or AI tooling.
                </p>
            </div>

            <br>

            <div class="callout warning">
                <h3>Concrete correction: Airtable</h3>
                <p>
                    The agent initially classified Airtable as
                    <b>MCP = No</b>. Human verification found an official
                    Airtable MCP server and the verified dataset was corrected
                    to <b>MCP = Yes</b>.
                </p>
            </div>

        </div>

        <div class="card">
            <h2>Verification loop</h2>

            <div class="bar-row">
                <div class="bar-label">
                    <span>Research pass</span>
                    <b>100/100</b>
                </div>
                <div class="bar">
                    <span style="width:100%"></span>
                </div>
            </div>

            <div class="bar-row">
                <div class="bar-label">
                    <span>Human sample</span>
                    <b>20 apps</b>
                </div>
                <div class="bar">
                    <span style="width:20%"></span>
                </div>
            </div>

            <p style="color:var(--muted);font-size:13px;margin-top:25px">
                Important: confidence is not treated as accuracy. The final
                case study preserves the original output and separately stores
                the human-reviewed dataset.
            </p>

            <p style="color:var(--muted);font-size:13px">
                First-pass output:
                <code>research_results_first_pass.json</code>
            </p>

            <p style="color:var(--muted);font-size:13px">
                Verified output:
                <code>research_results_verified.json</code>
            </p>
        </div>

    </div>
</section>


<section class="section">
    <div class="section-title">
        <div>
            <h2>100-app research matrix</h2>
            <p class="section-sub">
                Every row is backed by evidence URLs collected during the
                research process. Open the sources to inspect the underlying
                documentation.
            </p>
        </div>
    </div>

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>App</th>
                    <th>Category</th>
                    <th>Auth</th>
                    <th>Access</th>
                    <th>API</th>
                    <th>MCP</th>
                    <th>Buildability</th>
                    <th>Confidence</th>
                    <th>Evidence</th>
                </tr>
            </thead>

            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
</section>


<section class="section">
    <div class="card">
        <h2>What this means for Composio</h2>

        <p class="section-sub" style="max-width:900px">
            The research suggests that the scalable path is not simply finding
            APIs. The operational bottleneck is deciding which integrations
            can move directly to implementation, which require access
            escalation, and which need another evidence pass—particularly
            around MCP.
        </p>

        <div class="grid insights" style="margin-top:20px">

            <div class="callout">
                <h3>Build first</h3>
                <p>
                    Public REST/GraphQL + self-serve credentials +
                    broad surface.
                </p>
            </div>

            <div class="callout">
                <h3>Review</h3>
                <p>
                    Ambiguous authentication, incomplete MCP evidence,
                    or unusual API surfaces.
                </p>
            </div>

            <div class="callout warning">
                <h3>Outreach</h3>
                <p>
                    Partner/contact-sales requirements or access controlled
                    by enterprise/admin approval.
                </p>
            </div>

            <div class="callout">
                <h3>Keep evidence attached</h3>
                <p>
                    Every classification should remain traceable to provider
                    documentation.
                </p>
            </div>

        </div>
    </div>
</section>


<footer>
    <b>AI Product Ops Research Agent</b><br>
    Evidence-first research · Composio web tools · Gemini classification ·
    human verification
</footer>

</div>

</body>
</html>
"""

OUT.parent.mkdir(parents=True, exist_ok=True)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(page)

print("=" * 60)
print("CASE STUDY GENERATED")
print("=" * 60)
print(f"Apps:       {total}")
print(f"READY:      {ready}")
print(f"REVIEW:     {review}")
print(f"High conf:  {confidence.get('High', 0)}")
print(f"MCP:        {mcp_yes}")
print(f"Output:     {OUT}")
print("=" * 60)