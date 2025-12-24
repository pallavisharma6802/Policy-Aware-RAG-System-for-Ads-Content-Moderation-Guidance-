import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from api.models import QueryRequest, QueryResponse, CitationResponse, HealthResponse
from app.generation import generate_policy_response
from db.session import engine

load_dotenv()

app = FastAPI(
    title="Policy-Aware RAG System",
    description="Grounded answer generation for Google Ads policy compliance queries",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Serve the HTML frontend."""
    html_file = static_dir / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return {"message": "Policy RAG API is running. Visit /docs for API documentation."}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    health = {
        "status": "healthy",
        "database": "unknown",
        "vector_db": "unknown",
        "llm": "unknown"
    }
    
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        health["database"] = "connected"
    except Exception as e:
        health["database"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    try:
        import weaviate
        weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
        client = weaviate.Client(url=weaviate_url)
        client.schema.get()
        health["vector_db"] = "connected"
    except Exception as e:
        health["vector_db"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    try:
        import requests
        ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=2)
        if response.status_code == 200:
            health["llm"] = "connected"
        else:
            health["llm"] = "unreachable"
            health["status"] = "degraded"
    except Exception as e:
        health["llm"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    return HealthResponse(**health)


@app.post("/query", response_model=QueryResponse)
async def query_policy(request: QueryRequest):
    try:
        response = generate_policy_response(
            query=request.query,
            limit=request.limit,
            region=request.region,
            content_type=request.content_type,
            policy_source=request.policy_source
        )
        
        citations = [
            CitationResponse(
                chunk_id=c.chunk_id,
                policy_path=c.policy_path,
                doc_id=c.doc_id,
                doc_url=c.doc_url
            )
            for c in response.citations
        ]
        
        return QueryResponse(
            answer=response.answer,
            refused=response.refused,
            citations=citations,
            refusal_reason=response.refusal_reason,
            latency_ms=response.latency_ms,
            num_tokens_generated=response.num_tokens_generated
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal processing error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
