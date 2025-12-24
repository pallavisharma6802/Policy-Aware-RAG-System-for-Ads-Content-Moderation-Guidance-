import weaviate
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from typing import List, Dict
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from db.session import SessionLocal
from db.models import PolicyChunk

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def get_weaviate_client() -> weaviate.Client:
    client = weaviate.Client(url=WEAVIATE_URL)
    return client

def create_schema(client: weaviate.Client):
    schema = {
        "class": "PolicyChunk",
        "description": "Policy document chunks with embeddings",
        "vectorizer": "none",
        "properties": [
            {
                "name": "chunk_id",
                "dataType": ["text"],
                "description": "UUID matching PostgreSQL chunk_id"
            },
            {
                "name": "chunk_text",
                "dataType": ["text"],
                "description": "Full chunk text with hierarchy prefix"
            },
            {
                "name": "doc_id",
                "dataType": ["text"],
                "description": "Versioned document identifier"
            },
            {
                "name": "doc_url",
                "dataType": ["text"],
                "description": "URL to the source policy document"
            },
            {
                "name": "policy_section",
                "dataType": ["text"],
                "description": "Leaf section title"
            },
            {
                "name": "policy_path",
                "dataType": ["text"],
                "description": "Full hierarchical path"
            },
            {
                "name": "policy_section_level",
                "dataType": ["text"],
                "description": "Section hierarchy level (H2, H3)"
            },
            {
                "name": "policy_source",
                "dataType": ["text"],
                "description": "Policy source platform (google, facebook, etc.)"
            },
            {
                "name": "region",
                "dataType": ["text"],
                "description": "Applicable region (GLOBAL, US, EU, UK)"
            },
            {
                "name": "content_type",
                "dataType": ["text"],
                "description": "Content type (AD_TEXT, IMAGE, VIDEO, LANDING_PAGE, GENERAL)"
            }
        ]
    }
    
    if client.schema.exists("PolicyChunk"):
        print("Schema already exists, deleting...")
        client.schema.delete_class("PolicyChunk")
    
    client.schema.create_class(schema)
    print("Schema created successfully")

def load_chunks_from_db(db: Session) -> List[PolicyChunk]:
    chunks = db.query(PolicyChunk).order_by(
        PolicyChunk.doc_id, 
        PolicyChunk.chunk_index
    ).all()
    return chunks

def generate_embeddings(texts: List[str], model) -> List[List[float]]:
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    embeddings_list = embeddings.tolist()
    
    if len(embeddings_list) > 0:
        assert len(embeddings_list[0]) == 384, (
            f"Expected 384-dimensional embeddings, got {len(embeddings_list[0])}"
        )
    
    return embeddings_list

def ingest_chunks(client: weaviate.Client, chunks: List[PolicyChunk], embeddings: List[List[float]]):
    print(f"Ingesting {len(chunks)} chunks into Weaviate...")
    
    with client.batch as batch:
        batch.batch_size = 100
        
        for chunk, embedding in zip(chunks, embeddings):
            properties = {
                "chunk_id": str(chunk.chunk_id),
                "chunk_text": chunk.chunk_text,
                "doc_id": chunk.doc_id,
                "doc_url": chunk.doc_url if chunk.doc_url else "",
                "policy_section": chunk.policy_section,
                "policy_path": chunk.policy_path,
                "policy_section_level": chunk.policy_section_level,
                "policy_source": chunk.policy_source.value,
                "region": chunk.region.value,
                "content_type": chunk.content_type.value
            }
            
            batch.add_data_object(
                data_object=properties,
                class_name="PolicyChunk",
                uuid=str(chunk.chunk_id),
                vector=embedding
            )
    
    print("Ingestion complete")

def main():
    print("Starting embedding and ingestion process...")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    
    print("\nLoading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    print("Connecting to Weaviate...")
    client = get_weaviate_client()
    
    print("Creating schema...")
    create_schema(client)
    
    print("\nLoading chunks from PostgreSQL...")
    db = SessionLocal()
    try:
        chunks = load_chunks_from_db(db)
        print(f"Loaded {len(chunks)} chunks")
        
        if len(chunks) == 0:
            print("No chunks found in database. Run ingestion pipeline first.")
            return
        
        print("\nGenerating embeddings...")
        texts = [chunk.chunk_text for chunk in chunks]
        embeddings = generate_embeddings(texts, model)
        
        print(f"Generated {len(embeddings)} embeddings")
        print(f"Embedding dimension: {len(embeddings[0])}")
        
        print("\nIngesting into Weaviate...")
        ingest_chunks(client, chunks, embeddings)
        
        count = client.query.aggregate("PolicyChunk").with_meta_count().do()
        total = count['data']['Aggregate']['PolicyChunk'][0]['meta']['count']
        print(f"\nTotal chunks in Weaviate: {total}")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
