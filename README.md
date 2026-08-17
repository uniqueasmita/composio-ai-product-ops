# AI Product Ops Research Agent

An evidence-first research agent for checking whether software applications have usable APIs, authentication options, MCP support, and a realistic path to integration.

The project researches a list of applications, collects supporting documentation from the public web using Composio, and then uses Gemini to turn that evidence into a structured buildability assessment.

The final run covers 100 applications across 10 categories.

## What I wanted to solve

Looking up API information for 100 applications manually gets repetitive very quickly. It is also easy to end up with incomplete information or rely on search snippets without checking the actual documentation.

I wanted to build a research pipeline that could:

- find relevant developer documentation
- collect evidence instead of relying only on search results
- identify authentication methods
- identify available API surfaces
- check for MCP support
- understand how developers can get access
- produce a simple `READY`, `READY_WITH_REVIEW`, or `BLOCKED` decision
- keep the original evidence so the results can be reviewed later

## How it works

The pipeline is split into a few separate steps:

```text
apps.csv
   |
   v
Composio web research
   |
   v
Official documentation + citations
   |
   v
Evidence collection
   |
   v
Gemini classification
   |
   v
Structured research results
   |
   +----> Analytics
   |
   +----> Verification sample
   |
   +----> Web dashboard
```

### 1. Research

For every application, the collector runs focused searches around:

- API authentication
- REST / GraphQL / other API documentation
- MCP support
- pricing and API access

The search results are then used to identify candidate documentation pages.

### 2. Evidence collection

The candidate pages are fetched and stored along with their URLs and content status.

This gives the classifier actual documentation to work with instead of only search-result snippets.

The main evidence file is:

```text
outputs/evidence_raw.json
```

### 3. Classification

Gemini processes the collected evidence and produces a structured result for each application.

The classification includes:

- category
- description
- authentication methods
- self-serve/access model
- API type
- API breadth
- MCP availability
- buildability
- blocker
- documentation URL
- evidence URLs
- confidence
- notes

The final results are stored in:

```text
outputs/research_results.json
```

### 4. Batch processing

Since the dataset contains 100 applications, the classifier processes them in batches instead of sending all records in one request.

Completed batches are saved as the process runs, so a temporary model/API failure does not require starting the entire classification again.

The batch classifier is:

```text
agent/batch_researcher.py
```

## Final results

The final run contains:

- 100 applications
- 10 categories
- 96 high-confidence results
- 4 medium-confidence results
- 88 READY
- 12 READY_WITH_REVIEW
- 0 BLOCKED

Some of the main patterns found were:

| Finding | Result |
|---|---:|
| Applications researched | 100 |
| High confidence | 96 |
| Medium confidence | 4 |
| READY | 88 |
| READY_WITH_REVIEW | 12 |
| REST API observed | 95 |
| OAuth2 observed | 69 |
| MCP: Yes | 27 |
| MCP: No | 66 |
| MCP: Unknown | 7 |

Authentication and API counts are based on observed methods, so one application can appear in more than one authentication or API category.

## Project structure

```text
composio-ai-product-ops/
│
├── agent/
│   ├── analyzer.py
│   ├── batch_researcher.py
│   ├── collector.py
│   ├── researcher.py
│   ├── schema.py
│   ├── verifier.py
│   └── __init__.py
│
├── data/
│   └── apps.csv
│
├── outputs/
│   ├── evidence_raw.json
│   ├── research_results.json
│   ├── research_results_verified.json
│   ├── verification_sample.json
│   └── verification_sheet.csv
│
├── web/
│   └── index.html
│
├── build_case_study.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Tech used

- Python
- Composio
- Composio Search tools
- Gemini API
- Google GenAI SDK
- JSON / CSV
- HTML / CSS / JavaScript

## Running the project

### 1. Clone the repository

```bash
git clone https://github.com/uniqueasmita/composio-ai-product-ops.git
cd composio-ai-product-ops
```

### 2. Create a virtual environment

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Add API keys

Create a `.env` file in the project root:

```text
COMPOSIO_API_KEY=your_composio_api_key
GOOGLE_API_KEY=your_google_api_key
```

The `.env` file is ignored by Git and should not be committed.

### 5. Run evidence collection

```powershell
python agent\collector.py
```

This creates:

```text
outputs/evidence_raw.json
```

### 6. Run classification

For the full dataset, use the batch classifier:

```powershell
python agent\batch_researcher.py
```

This writes the classified results to:

```text
outputs/research_results.json
```

For testing a single research/classification pass:

```powershell
python agent\researcher.py
```

## Dashboard

The project includes a small static dashboard in:

```text
web/index.html
```

It presents the research results in a more readable form, including:

- overall research statistics
- confidence distribution
- buildability
- authentication patterns
- API surfaces
- MCP availability
- category-level results
- individual application results
- links to supporting sources

The dashboard can be opened directly in a browser:

```text
web/index.html
```

## Verification

I did not treat the model output as automatically correct.

A sample of 20 applications was created for verification:

```text
outputs/verification_sample.json
```

The project also contains:

```text
outputs/verification_sheet.csv
```

The purpose of this step is to make it easier to review whether the structured classifications are supported by the collected documentation and identify cases that need another evidence pass.

## Buildability decisions

The classifier uses three possible buildability outcomes.

### READY

The available evidence gives a reasonably clear path for integration.

### READY_WITH_REVIEW

There is useful evidence, but something still needs to be checked manually. Examples include unclear access requirements, incomplete MCP information, or documentation that needs another pass.

### BLOCKED

The available evidence does not show a practical integration path.

In the final run there were no BLOCKED applications.

## A note about MCP

MCP was treated separately from normal API research.

Finding an API does not automatically mean that an MCP server is available. Because of that, MCP results can be:

- Yes
- No
- Unknown

The Unknown state is intentional. If the evidence was not strong enough, the system did not try to force a yes/no answer.

## Why keep the evidence?

One of the main design choices in this project was keeping the research evidence separate from the final classification.

For example:

```text
evidence_raw.json
       |
       v
research_results.json
```

This makes it possible to go back from a classification to the documentation that was used to make it.

It also makes the system easier to improve later because the research step does not have to be repeated every time the classification logic changes.

## Limitations

This is a research and triage system, not an automated integration builder.

A READY result means that the available evidence suggests a practical integration path. It does not mean that an integration has been implemented and tested against a live customer account.

Some information can also change over time, especially:

- API availability
- pricing
- authentication requirements
- MCP support
- access restrictions
- documentation URLs

For those cases, another evidence pass may be required.

## Possible next improvements

If I continued developing this, I would add:

- automatic re-checking of stale documentation
- stronger source ranking
- deeper MCP verification
- automated contradiction detection
- confidence scoring based on evidence quality
- a database instead of JSON for larger datasets
- scheduled research refreshes
- more detailed human-review workflows

## Project outcome

The main goal was not just to produce 100 rows of data.

The useful part is the pipeline:

```text
Research → Evidence → Classification → Verification → Decision
```

This makes the research process repeatable and gives a clearer path from public documentation to an integration decision.