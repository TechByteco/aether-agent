# Obscura Enchanted Agent Engine

An ultra-lightweight (30MB RAM) browser runtime, Model Context Protocol (MCP) server, and production REST API engineered specifically for Autonomous AI Agent Swarms.

---

## Key Highlights

- **30MB–35MB RAM Footprint:** Native V8 execution without heavy Chromium/Blink layout overhead.
- **Semantic DOM Distillation:** Token reduction of 80% to 95% while preserving headings, clean text, and structured tables.
- **Deterministic Action Grounding:** Actionable controls automatically indexed with deterministic `[@ref:ID]` tags for zero-ambiguity agent execution.
- **DOM Mutation Diffing:** Stateful diff engine returning only mutations (added, modified, removed elements) across sequential turns to save up to 95% tokens.
- **High-Concurrency REST + SSE API:** Production FastAPI server with Server-Sent Events (SSE) for live browser event streaming.
- **Multi-Tier Caching:** `SnapshotCache` (LRU), `ResponseCache` (gzip-compressed HTTP responses), and `RobotsTxtCache` (per-domain compliance).
- **Resilient Networking:** Sliding-window rate limiting and exponential backoff retry with jitter.
- **Autonomous Multi-Page Crawler:** Configurable breadth-first and streaming domain crawl engine with depth control and link deduplication.
- **Enterprise Observability:** Prometheus metrics exposition (`/metrics`), structured JSON logging, and pre-built Grafana dashboards.
- **Production-Ready Deployment:** Docker Compose with Nginx reverse proxy & Redis, plus complete Kubernetes manifests with Horizontal Pod Autoscaler (HPA).

---

## Architecture

```
Raw Web Page (HTML / SPA)
          │
          ▼
   Obscura Engine (30MB V8)
          │
    ┌─────┴───────────────────────────────┐
    ▼                                     ▼
Semantic Distiller                  Mutation Differ
(Strips SVG/styles,                 (Emits only deltas
 Injects [@ref:ID] tags)             between agent turns)
    │                                     │
    └──────────────────┬──────────────────┘
                       ▼
    ┌──────────────────┴──────────────────┐
    ▼                                     ▼
Enchanted MCP Server               FastAPI REST + SSE Server
(JSON-RPC stdio transport)         (High-concurrency cluster)
    │                                     │
    └──────────────────┬──────────────────┘
                       ▼
         Autonomous AI Agents & Swarms
    (Claude, Cursor, Antigravity, AutoGen, CrewAI)
```

---

## Quickstart

### 1. Installation

```bash
git clone https://github.com/TechByteco/obscura_enchanted_agent_engine.git
cd obscura_enchanted_agent_engine
pip install -r requirements.txt
```

### 2. Run Test Suite (20/20 Passing)

```bash
python run_tests.py
```

### 3. Launch MCP Server (for Claude Desktop / Cursor)

```bash
python -m obscura_engine.cli serve
```

### 4. Launch Production REST + SSE API Server

```bash
python -m obscura_engine.cli serve-api --host 0.0.0.0 --port 8000
```

### 5. Launch Autonomous Multi-Page Crawl

```bash
python -m obscura_engine.cli crawl https://news.ycombinator.com --max-pages 15 --max-depth 2
```

---

## Production API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/navigate` | Navigates to a URL and returns a distilled snapshot |
| `POST` | `/act` | Executes click, type, select, or hover via `@ref:ID` |
| `GET` | `/snapshot` | Returns the current distilled markdown snapshot |
| `GET` | `/diff` | Emits only DOM mutations since the last step |
| `POST` | `/fill_form` | Populates multiple form inputs in a single round-trip |
| `POST` | `/extract` | Extracts repeating DOM rows/cards into JSON matching a schema |
| `GET` | `/sessions` | Lists active browser sessions |
| `POST` | `/sessions` | Creates an isolated browser session tab |
| `DELETE`| `/sessions/{id}` | Destroys an active session tab |
| `GET` | `/metrics` | Prometheus metrics and engine telemetry |
| `GET` | `/health` | Health check endpoint for load balancers and k8s |
| `GET` | `/sse/events` | Live Server-Sent Events stream of browser actions |

For detailed curl examples and request schemas, see [docs/API.md](docs/API.md).

---

## Deployment

### Docker Compose (API + Nginx + Prometheus + Grafana)

```bash
docker compose -f deploy/docker-compose.prod.yml up -d
```

### Kubernetes

```bash
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/hpa.yaml
```

---

## License

Apache-2.0 License. Built for autonomous AI agents and enterprise agent swarms.
