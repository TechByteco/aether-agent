# Obscura Enchanted Agent Engine — Production API Reference

Complete documentation for the REST API, Server-Sent Events (SSE), Model Context Protocol (MCP) server, and Python SDK.

---

## 1. REST API Endpoints

Base URL: `http://localhost:8000` (or `https://your-domain.com`)

### Authentication
If `OBSCURA_API_KEY` is configured, pass your key via header or query param:
- Header: `X-API-Key: your_secret_key`
- Query: `?api_key=your_secret_key`

---

### POST `/navigate`
Navigates the browser to a target URL, executes token distillation, and indexes interactive elements with `[@ref:ID]` tags.

**Request:**
```json
{
  "url": "https://news.ycombinator.com",
  "session_id": "session-1",
  "timeout": 30.0,
  "bypass_cache": false
}
```

**Response (200 OK):**
```json
{
  "url": "https://news.ycombinator.com",
  "title": "Hacker News",
  "markdown": "# Hacker News\n**URL:** https://news.ycombinator.com\n\n---\n...",
  "interactive_elements": [
    {
      "ref_id": "1",
      "tag_name": "a",
      "text": "Hacker News",
      "selector": "a[href='news']",
      "role": "link"
    }
  ],
  "raw_char_count": 33793,
  "distilled_char_count": 405,
  "estimated_raw_tokens": 8448,
  "estimated_distilled_tokens": 101,
  "token_savings_pct": 98.8
}
```

---

### POST `/act`
Dispatches an atomic user action (`click`, `type`, `select`, `hover`, `scroll`, `press_key`) by `ref` ID or CSS selector.

**Request:**
```json
{
  "action": "click",
  "ref": "1",
  "session_id": "session-1"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "action": "click",
  "ref": "1",
  "message": "Clicked element 1"
}
```

---

### GET `/snapshot`
Returns the current distilled Markdown snapshot of the active page.

**Parameters:**
- `session_id` (optional, query): Session identifier (default: `"default"`)

---

### GET `/diff`
Returns only the semantic DOM mutations (added, modified, removed elements) since the previous action.

**Response (200 OK):**
```json
{
  "previous_url": "https://store.test",
  "current_url": "https://store.test/cart",
  "has_changed": true,
  "summary": "State updated: +1 added, *1 modified, -0 removed.",
  "diff_markdown": "### Newly Appeared Controls (1):\n+ [@ref:15] A: 'Proceed to Checkout'"
}
```

---

### POST `/fill_form`
Populates an entire multi-field form in one atomic request.

**Request:**
```json
{
  "fields": [
    {"ref_or_selector": "1", "value": "alice@example.com"},
    {"ref_or_selector": "2", "value": "SuperSecretPass123!"}
  ],
  "session_id": "session-1"
}
```

---

### POST `/extract`
Extracts structured repeating records into a JSON array matching specified CSS selectors.

**Request:**
```json
{
  "container_selector": "tr.athing",
  "fields": {
    "rank": "span.rank",
    "title": "span.titleline > a",
    "site": "span.sitestr"
  },
  "session_id": "session-1"
}
```

---

### GET `/metrics`
Prometheus metrics and engine telemetry:
- Memory usage (MB)
- Cumulative prompt tokens saved
- Active sessions and tab counts
- p50/p95/p99 navigation latency

---

### GET `/health`
Health check endpoint used by Kubernetes and load balancers.

```json
{
  "status": "healthy",
  "engine_version": "1.0.0",
  "api_version": "1.0.0",
  "uptime_seconds": 1420.5,
  "active_sessions": 3
}
```

---

### GET `/sse/events`
Live Server-Sent Events stream emitting browser state changes:
- `navigation_completed`
- `action_executed`
- `dom_mutated`

---

## 2. Model Context Protocol (MCP) Tools

| Tool | Purpose | Key Parameters |
| :--- | :--- | :--- |
| `browser_navigate` | Navigates to a URL with token distillation | `url` |
| `browser_distilled_snapshot` | Returns token-dense markdown with `[@ref:ID]` tags | none |
| `browser_diff_snapshot` | Emits only mutations since last turn | none |
| `browser_act` | Atomic action execution | `action`, `ref`, `value` |
| `browser_fill_form_smart` | Atomic batch form filling | `fields: [...]` |
| `browser_extract_structured_data` | Extracts JSON matching a schema | `container_selector`, `fields` |
| `browser_session_stats` | Live performance and memory stats | none |

---

## 3. Configuration Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `OBSCURA_API_KEY` | *(none)* | Secret key for REST API authentication |
| `OBSCURA_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `OBSCURA_LOG_FORMAT` | `pretty` | `pretty` or `json` |
| `MAX_ACTIVE_TABS` | `10` | Tab concurrency limit per engine |
| `MEMORY_MB_PER_TAB` | `35.0` | Memory budget per tab (MB) |
| `PORT` | `8000` | HTTP API server port |
| `CACHE_ENABLED` | `true` | Toggle snapshot and HTTP response caching |
| `RATE_LIMIT_ENABLED`| `true` | Toggle sliding window rate limiter |
