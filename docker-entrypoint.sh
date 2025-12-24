#!/bin/bash
set -e

echo "Policy-Aware RAG System Starting..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done
echo "PostgreSQL is ready"

# Wait for Weaviate to be ready
echo "Waiting for Weaviate..."
until curl -sf "$WEAVIATE_URL/v1/.well-known/ready" > /dev/null; do
  echo "Weaviate is unavailable - sleeping"
  sleep 2
done
echo "Weaviate is ready"

# Wait for Ollama to be ready
echo "Waiting for Ollama..."
until curl -sf "$OLLAMA_HOST/api/tags" > /dev/null; do
  echo "Ollama is unavailable - sleeping"
  sleep 2
done
echo "Ollama is ready"

# Check if Ollama model is available, if not pull it
echo "Checking Ollama model: $OLLAMA_MODEL"
if ! curl -s "$OLLAMA_HOST/api/tags" | grep -q "\"name\":\"$OLLAMA_MODEL\""; then
  echo "Pulling Ollama model: $OLLAMA_MODEL (this may take several minutes)..."
  curl -X POST "$OLLAMA_HOST/api/pull" -d "{\"name\":\"$OLLAMA_MODEL\"}"
  echo "Model downloaded"
else
  echo "Model already available"
fi

# Initialize database tables
echo "Initializing database tables..."
python -c "from db.session import init_db; init_db()"
echo "Database initialized"

# Check if documents need to be downloaded
if [ ! -f "/app/data/metadata.json" ]; then
  echo "Downloading policy documents..."
  python -m ingestion.load_docs
  echo "Documents downloaded"
else
  echo "Documents already present"
fi

# Check if documents need to be chunked
if [ ! -f "/app/data/chunks.json" ]; then
  echo "Chunking documents..."
  python -m ingestion.chunk
  echo "Documents chunked"
else
  echo "Chunks already present"
fi

# Check if embeddings need to be created
CHUNK_COUNT=$(curl -s "$WEAVIATE_URL/v1/objects?class=PolicyChunk&limit=1" | grep -o '"totalResults":[0-9]*' | grep -o '[0-9]*' || echo "0")
if [ "$CHUNK_COUNT" -eq "0" ]; then
  echo "Creating embeddings and indexing in Weaviate..."
  python -m ingestion.embed
  echo "Embeddings indexed"
else
  echo "Embeddings already indexed ($CHUNK_COUNT chunks)"
fi

echo "Starting FastAPI server..."

# Start the FastAPI application
exec uvicorn api.main:app --host 0.0.0.0 --port 8000
