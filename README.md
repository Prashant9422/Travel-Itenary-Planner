# GenAI Travel Itinerary Planner

A modular Streamlit application that uses LangChain, Ollama, RAG (Chroma vector search), local sample travel data, Pydantic structured output, and Markdown/JSON export to generate personalized travel itineraries.

> **Important:** bundled CSV data is illustrative sample data, not live flight fares, hotel availability, verified opening hours, or bookable inventory. The application does not make bookings.

For a client-facing project summary, workflow diagrams, demo script, glossary, and current scope, see [CLIENT_PROJECT_OVERVIEW.md](./CLIENT_PROJECT_OVERVIEW.md).

## Architecture

```text
Streamlit UI (app.py + app/components/)
             |
             v
TripRequest (Pydantic validation)
             |
             v
Itinerary service (LangChain prompt + output parser)
      |                         |
      v                         v
CSV data service          RAG service
(flights/hotels/          (HuggingFace embeddings
 attractions/guides)       + Chroma vector store)
      |                         |
      +------------+------------+
                   v
           LLM factory / adapter
       Ollama | OpenAI | Gemini
                   |
                   v
        Structured Itinerary output
                   |
                   v
      Editable UI + Markdown/JSON export
```

## Requirements

- Python 3.11, 3.12, or 3.13 recommended. Python 3.15 is not currently supported because `chromadb` depends on `onnxruntime`, which has no compatible distribution for Python 3.15.
- Ollama installed and running for the default local model
- 8 GB RAM recommended for a small local model; larger models need more
- Internet access for first-time Python package and embedding-model downloads

## Setup (Ollama — default)

1. Install Ollama from <https://ollama.com/>.
2. Pull a model:

   ```bash
   ollama pull llama3.1:8b
   ```

   If your computer has limited RAM, choose a smaller model and update `OLLAMA_MODEL` in `.env`.

3. Create and activate a virtual environment:

   **Windows PowerShell**
   ```powershell
   py -3.13 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   **macOS/Linux**
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   ```

4. Install dependencies:

   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env` and adjust model settings if needed.

   Windows:
   ```powershell
   Copy-Item .env.example .env
   ```

   macOS/Linux:
   ```bash
   cp .env.example .env
   ```

6. Start Ollama if it is not already running, then run:

   ```bash
   streamlit run app.py
   ```

7. Open the local URL Streamlit prints (normally `http://localhost:8501`). The first RAG request downloads the embedding model and creates a local Chroma index; this may take a few minutes.

## Use another LLM

The LLM factory is isolated in `app/services/llm_factory.py`. The sidebar lets you choose the provider. Configure the relevant API key and model in `.env`:

- OpenAI: set `OPENAI_API_KEY`, `OPENAI_MODEL`; choose `openai` in the sidebar.
- Gemini: set `GOOGLE_API_KEY`, `GEMINI_MODEL`; choose `gemini` in the sidebar.
- Ollama: set `OLLAMA_BASE_URL`, `OLLAMA_MODEL`; choose `ollama`.

Never commit `.env` or API keys. Add new providers by adding a branch to `get_llm()` or by implementing a common adapter interface.

## Project structure

```text
travel_genai_project/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── data/
│   ├── attractions.csv
│   ├── destination_guides.csv
│   ├── flights.csv
│   ├── hotels.csv
│   └── travel_basics.md
├── app/
│   ├── config.py
│   ├── schemas.py
│   ├── components/
│   │   ├── sidebar.py
│   │   ├── trip_form.py
│   │   └── itinerary_view.py
│   └── services/
│       ├── data_service.py
│       ├── export_service.py
│       ├── itinerary_service.py
│       ├── llm_factory.py
│       └── rag_service.py
└── tests/
    └── test_schemas.py
```

## Where the GenAI and RAG happen

1. `TripRequest` validates user input using Pydantic.
2. `rag_service.py` converts local CSV rows and Markdown into LangChain `Document` objects, embeds them, and stores them in Chroma.
3. The itinerary service retrieves relevant chunks with semantic similarity search.
4. `ChatPromptTemplate` sends user requirements, structured CSV context, and retrieved RAG context to the selected chat model.
5. `PydanticOutputParser` asks the LLM to return a schema-shaped itinerary. The UI renders it and enables JSON/Markdown downloads.

RAG is not a guarantee of truth: retrieval only returns information present in the local knowledge base. For a production version, add source URLs, freshness timestamps, ingestion validation, deduplication, and verified live-provider APIs.

## Budget estimates

The estimated trip total adds sample accommodation costs (nightly rate × nights × one room per two travelers, rounded up), matching one-way flight fares per traveler when available, and planned activity costs. Cost estimates are not reduced to force them under budget; when the total exceeds the requested budget, the app shows the full estimate, overage, and cost breakdown. If no matching flight route exists, the app tells the user that flights are unavailable and shows a total excluding flights. Flight fares, hotel rates, and activity costs are illustrative and should be verified before booking. The expanded flight dataset contains synthetic routes and fare estimates for testing; these do not confirm that a route operates. This total excludes meals and local transportation.

## Destination coverage and sources

The travel CSV files include a `source` column. Existing rows are illustrative sample data without verified external sources; the column states this explicitly. The attractions and destination guides CSVs also contain synthetic test fixtures; rows marked synthetic/test data are excluded from itinerary and RAG context and must not be treated as real attractions or travel advice. Replace sample values with verified records and authoritative source references before production use. The generation prompt forbids inventing destination-specific facts or citations, and itinerary generation stops with a data-coverage message when no destination-matched attraction rows exist.

The trip form accepts an optional **Starting location** (departure city). When provided, it filters the sample flight routes to those whose origin matches the entered city. Sample fares are not live or bookable; destination-matched attraction data is still required to generate an itinerary.

## Run tests

```bash
pytest -q
```

Tests validate the Pydantic schemas and date-range rules; they do not call an LLM.

## Future improvements / roadmap

### Phase 1 — Reliable data
- Replace demonstration CSVs with verified travel datasets and official source links.
- Add live APIs for flights, hotels, maps, places, attraction hours, weather, and transit. Check each provider's terms and rate limits.
- Store fetched data with source, retrieval timestamp, currency, and expiry/TTL.

### Phase 2 — Better planning agents
- Add LangGraph to orchestrate specialized nodes: preference extraction, retrieval, flight/hotel search, itinerary drafting, budget validation, and itinerary critique.
- Add tool calling for weather, maps, distance/time estimates, and live supplier searches.
- Add a critique-and-revise loop that checks date coverage, opening hours, travel distances, user constraints, and budget before returning a plan.
- Add user approval before any consequential booking action.

### Phase 3 — Personalization and memory
- Add opt-in user profiles and persistent preferences (diet, pace, accessibility, preferred airlines/hotel tiers).
- Add a recommendation system based on explicit ratings and past saved itineraries.
- Add conversational edits such as “swap day two and three” or “make this more relaxed,” while preserving locked activities.

### Phase 4 — Production readiness
- Add authentication, per-user storage, PostgreSQL, secrets management, request limits, retries, timeouts, structured logs, tracing, and evaluation.
- Add caching for embeddings and external API responses.
- Add automated tests for prompt injection, malformed model output, unsupported facts, cost arithmetic, and provider failures.
- Deploy in Docker; optionally use a hosted vector database and cloud LLM provider.

## Known limitations in this starter

- Sample prices are placeholders and not live quotes.
- Flight origin is not yet collected in the UI; the sample flight data is contextual only.
- Editing currently saves notes in the current Streamlit session; it does not yet execute an automatic regeneration workflow.
- The starter uses semantic RAG and a single generation chain; LangGraph agents and live APIs are roadmap items, not claimed as already implemented.
- LLM responses may be incorrect. Verify travel logistics using official sources.
