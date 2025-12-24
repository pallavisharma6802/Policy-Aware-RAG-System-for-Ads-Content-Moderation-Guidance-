# API Layer

REST API and web interface for the Policy-Aware RAG System.

## Overview

FastAPI-based REST API with automatic OpenAPI documentation and interactive web UI for querying the policy system.

## Architecture

```
Browser/Client
    ↓
FastAPI (port 8000)
    ├─ POST /query      → RAG Pipeline → JSON Response
    ├─ GET /health      → Service Status → Health Check
    └─ GET /            → Static HTML → Web UI
```

## Endpoints

### POST /query

Main endpoint for policy questions.

**Request:**

```json
{
  "query": "Can I advertise alcohol?",
  "limit": 5,
  "region": "Global",
  "content_type": "Advertising Policy",
  "policy_source": "Google Ads Policy"
}
```

**Response (success):**

```json
{
  "answer": "Alcohol advertising is allowed with certification...",
  "refused": false,
  "citations": [
    {
      "chunk_id": "google_ads_overview_chunk_005",
      "policy_path": "Prohibited Content > Alcohol",
      "doc_id": "google_ads_overview",
      "doc_url": "https://support.google.com/adspolicy/answer/6012382"
    }
  ],
  "refusal_reason": null,
  "latency_ms": 2543.2,
  "num_tokens_generated": 87
}
```

**Response (refusal):**

```json
{
  "answer": "I cannot provide a confident answer based on the provided sources.",
  "refused": true,
  "citations": [],
  "refusal_reason": "LLM determined sources insufficient to answer query",
  "latency_ms": 1823.1,
  "num_tokens_generated": 23
}
```

**Validation rules:**

- `query`: 3-500 characters (required)
- `limit`: 1-20 results (default: 5)
- `region`, `content_type`, `policy_source`: optional filters

**Error responses:**

```json
// 422 Validation Error
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "ensure this value has at least 3 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}

// 500 Internal Server Error
{
  "detail": "Error generating response: <error message>"
}
```

**cURL example:**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the gambling rules?",
    "limit": 5
  }'
```

**Python example:**

```python
import requests

response = requests.post(
    "http://localhost:8000/query",
    json={
        "query": "Can I advertise alcohol?",
        "limit": 5
    }
)

data = response.json()
print(f"Answer: {data['answer']}")
print(f"Citations: {len(data['citations'])}")

for citation in data['citations']:
    print(f"  - {citation['policy_path']}")
    print(f"    URL: {citation['doc_url']}")
```

### GET /health

Service health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "database": "connected",
  "vector_db": "connected",
  "llm": "connected"
}
```

**Status values:**

- `healthy`: All services operational
- `degraded`: One or more services unavailable

**Component checks:**

- **database**: PostgreSQL connection (`engine.connect()`)
- **vector_db**: Weaviate availability (`client.schema.get()`)
- **llm**: Ollama service (`/api/tags` endpoint)

**Usage:**

```bash
curl http://localhost:8000/health

# For monitoring/alerts
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
  echo "Service healthy"
else
  echo "Service unhealthy"
fi
```

### GET /

Interactive web UI for querying the system.

**Features:**

- Query input textarea
- Result limit dropdown (3, 5, 10)
- Real-time answer display
- Citation rendering with policy links
- Loading states
- Error handling

**Access:**

```
http://localhost:8000
```

## Pydantic Models

### QueryRequest

```python
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500,
                      description="Policy question to answer")
    limit: int = Field(default=5, ge=1, le=20,
                      description="Maximum number of sources to retrieve")
    region: Optional[str] = Field(None, description="Filter by policy region")
    content_type: Optional[str] = Field(None, description="Filter by content type")
    policy_source: Optional[str] = Field(None, description="Filter by policy source")
```

### QueryResponse

```python
class QueryResponse(BaseModel):
    answer: str = Field(description="Generated answer text")
    refused: bool = Field(description="Whether LLM refused to answer")
    citations: List[CitationResponse] = Field(description="Source citations")
    refusal_reason: Optional[str] = Field(None, description="Reason for refusal if applicable")
    latency_ms: float = Field(description="Total response time in milliseconds")
    num_tokens_generated: int = Field(description="Number of tokens in answer")
```

### CitationResponse

```python
class CitationResponse(BaseModel):
    chunk_id: str = Field(description="Unique chunk identifier")
    policy_path: str = Field(description="Hierarchical policy section path")
    doc_id: str = Field(description="Source document identifier")
    doc_url: str = Field(description="URL to full policy document")
```

### HealthResponse

```python
class HealthResponse(BaseModel):
    status: str = Field(description="Overall system status: healthy or degraded")
    database: str = Field(description="PostgreSQL connection status")
    vector_db: str = Field(description="Weaviate connection status")
    llm: str = Field(description="Ollama service status")
```

## Web Interface

Located in `api/static/index.html`

**Components:**

**Form:**

- Query textarea (3-500 chars)
- Limit dropdown (3, 5, 10)
- Submit button

**Result display:**

- Answer text
- Citation list with clickable policy links
- Loading spinner during processing
- Error messages

**Citation rendering:**

```javascript
citations.forEach((citation) => {
  const citationDiv = document.createElement("div");
  citationDiv.className = "citation";
  citationDiv.innerHTML = `
    <strong>${citation.policy_path}</strong><br>
    Document ID: ${citation.doc_id}<br>
    ${
      citation.doc_url.startsWith("http")
        ? `<a href="${citation.doc_url}" target="_blank">View Full Policy Document →</a>`
        : `URL: ${citation.doc_url}`
    }
  `;
  citationsContainer.appendChild(citationDiv);
});
```

**Styling:**

- Blue theme (#1a73e8)
- Responsive grid layout
- Clean professional design
- Loading states
- Mobile-friendly

## API Documentation

FastAPI automatically generates interactive API documentation:

**Swagger UI:**

```
http://localhost:8000/docs
```

- Interactive API explorer
- Try endpoints directly
- View request/response schemas
- Authentication support

**ReDoc:**

```
http://localhost:8000/redoc
```

- Alternative documentation view
- Better for reading/printing
- Detailed schema descriptions

**OpenAPI JSON:**

```
http://localhost:8000/openapi.json
```

- Machine-readable API spec
- For code generation
- For API gateways

## CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production recommendation:**

```python
allow_origins=[
    "https://yourdomain.com",
    "https://app.yourdomain.com"
]
```

## Static File Serving

```python
app.mount("/static", StaticFiles(directory="api/static"), name="static")
```

Serves files from `api/static/`:

- `index.html` - Main web UI
- CSS, JS, images (if added)

## Running the Server

**Development:**

```bash
# With auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python
python api/main.py
```

**Production:**

```bash
# Multiple workers
uvicorn api.main:app --workers 4 --host 0.0.0.0 --port 8000

# With Gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Docker:**

```bash
docker-compose up -d
# Automatically starts on port 8000
```

## Environment Variables

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=policy_rag
POSTGRES_USER=policy_user
POSTGRES_PASSWORD=policy_pass

# Vector DB
WEAVIATE_URL=http://localhost:8080

# LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:4b

# Logging
LOG_LEVEL=INFO
```

## Testing

Located in `tests/test_api_endpoints.py`

**Categories:**

**API contract tests:**

- `test_query_happy_path`: Valid query returns citations
- `test_query_refusal_path`: Out-of-scope triggers refusal
- `test_query_with_multiple_citations`: Multiple sources returned

**Input validation:**

- `test_missing_query_field`: Missing required field rejected (422)
- `test_invalid_limit_negative`: Negative limit rejected (422)
- `test_invalid_limit_zero`: Zero limit rejected (422)
- `test_invalid_limit_too_large`: Excessive limit rejected (422)
- `test_query_too_short`: Query below 3 chars rejected (422)
- `test_query_too_long`: Query over 500 chars rejected (422)

**Infrastructure:**

- `test_html_page_loads`: Frontend serves correctly (200)
- `test_health_endpoint`: Health check returns status

**Performance:**

- `test_query_latency_under_threshold`: Query completes reasonably (<300s)
- `test_query_returns_metrics`: Response includes latency and tokens

**Flexibility:**

- `test_query_with_optional_filters`: Optional parameters handled

**Run tests:**

```bash
# All API tests
pytest tests/test_api_endpoints.py -v

# Specific test
pytest tests/test_api_endpoints.py::test_query_happy_path -v

# With coverage
pytest tests/test_api_endpoints.py --cov=api --cov-report=html
```

**All 14 tests pass (100% success rate)**

## Performance

**Latency breakdown:**

- API overhead: <50ms
- RAG pipeline: 2-5 seconds
- **Total**: 2-5 seconds per query

**Throughput:**

- Single worker: ~1-2 queries/minute
- 4 workers: ~4-8 queries/minute
- Bottleneck: LLM inference

**Optimization:**

- Use GPU for LLM (2-3x faster)
- Add Redis caching for frequent queries
- Reduce retrieval limit
- Use smaller LLM model

## Security

**Production checklist:**

1. **Restrict CORS:**

   ```python
   allow_origins=["https://yourdomain.com"]
   ```

2. **Add rate limiting:**

   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)

   @app.post("/query")
   @limiter.limit("10/minute")
   async def query(request: QueryRequest):
       ...
   ```

3. **Enable HTTPS:**

   - Use nginx reverse proxy
   - Add SSL/TLS certificates
   - Redirect HTTP to HTTPS

4. **Add authentication:**

   ```python
   from fastapi.security import HTTPBearer
   security = HTTPBearer()

   @app.post("/query")
   async def query(request: QueryRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
       # Verify token
       ...
   ```

5. **Input sanitization:**

   - Already handled by Pydantic
   - Add additional validation if needed

6. **Error handling:**
   - Don't expose internal errors to clients
   - Log detailed errors server-side
   - Return generic error messages

## Monitoring

**Metrics to track:**

- Request count by endpoint
- Response latency (p50, p95, p99)
- Error rate
- Refusal rate
- Citations per response
- LLM token usage

**Logging:**

```python
import logging
logger = logging.getLogger(__name__)

@app.post("/query")
async def query(request: QueryRequest):
    logger.info(f"Query received: {request.query[:50]}")
    # ...
    logger.info(f"Response: refused={response.refused}, latency={response.latency_ms}ms")
```

**Health monitoring:**

```bash
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

# Prometheus metrics
from prometheus_client import Counter, Histogram
query_counter = Counter('api_queries_total', 'Total queries')
query_latency = Histogram('api_query_latency_seconds', 'Query latency')
```

## Error Handling

**Validation errors (422):**

```python
try:
    # Pydantic validates automatically
    request = QueryRequest(**data)
except ValidationError as e:
    # FastAPI returns 422 with detailed error
    return {"detail": e.errors()}
```

**Internal errors (500):**

```python
@app.post("/query")
async def query(request: QueryRequest):
    try:
        response = generate_policy_response(...)
        return response
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {str(e)}"
        )
```

## Deployment

**Development:**

```bash
uvicorn api.main:app --reload
```

**Production (systemd):**

```ini
[Unit]
Description=Policy RAG API
After=network.target

[Service]
User=www-data
WorkingDirectory=/app
ExecStart=/usr/bin/uvicorn api.main:app --workers 4 --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Production (Docker):**

```bash
docker-compose up -d
```

**Production (Kubernetes):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: policy-rag-api
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: api
          image: policy-rag-api:latest
          ports:
            - containerPort: 8000
          env:
            - name: POSTGRES_HOST
              value: postgres-service
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
```

## Architecture Decisions

**Why FastAPI?**

- Modern async Python framework
- Automatic OpenAPI documentation
- Built-in validation with Pydantic
- High performance (comparable to Node.js)
- Excellent developer experience

**Why static file serving?**

- Simplifies deployment (no separate frontend server)
- Reduces infrastructure complexity
- Good enough for admin/internal tools

**Why health endpoint?**

- Load balancer health checks
- Monitoring integration
- Debugging connection issues

**Why CORS enabled?**

- Enables browser-based access
- Required for web UI
- Can be restricted in production

**Why Pydantic validation?**

- Type safety
- Automatic error messages
- OpenAPI schema generation
- Reduces boilerplate code
