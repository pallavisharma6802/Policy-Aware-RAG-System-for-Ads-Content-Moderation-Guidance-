import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional

sys.path.append(str(Path(__file__).parent.parent))

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.llms import Ollama

from app.retrieval import retrieve_policy_chunks
from app.schemas import PolicyResponse
from app.citations import extract_citations, validate_citations, build_citations

MIN_CONFIDENCE_SCORE = 0.25
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

POLICY_PROMPT = PromptTemplate(
    input_variables=["question", "sources"],
    template="""You are a policy compliance assistant for Google Ads.

Answer using ONLY the sources below. Every factual claim MUST include a citation.

Rules:
1. Use ONLY the provided sources - no external knowledge
2. Cite sources using this exact format: [SOURCE:<chunk_id>]
3. If sources lack sufficient information, respond with exactly: REFUSE

Question: {question}

Sources:
{sources}

Answer:"""
)


def should_refuse(results: List[Dict], min_score: float = MIN_CONFIDENCE_SCORE) -> tuple[bool, Optional[str]]:
    if not results:
        return True, "No relevant policies found for this query."
    
    if results[0]["score"] < min_score:
        return True, f"Insufficient confidence in policy match (score: {results[0]['score']:.2f})."
    
    return False, None


def format_sources(results: List[Dict]) -> str:
    formatted = []
    
    for result in results:
        chunk_id = result["chunk_id"]
        chunk_text = result["chunk_text"]
        formatted.append(f"SOURCE {chunk_id}:\n{chunk_text}\n")
    
    return "\n".join(formatted)


def get_llm(model_name: Optional[str] = None) -> Ollama:
    return Ollama(
        model=model_name or OLLAMA_MODEL,
        base_url=OLLAMA_HOST,
        temperature=0.05,
    )


def generate_policy_response(
    query: str,
    llm: Optional[Ollama] = None,
    limit: int = 5,
    region: Optional[str] = None,
    content_type: Optional[str] = None,
    policy_source: Optional[str] = None
) -> PolicyResponse:
    start_time = time.time()
    
    results = retrieve_policy_chunks(
        query=query,
        limit=limit,
        region=region,
        content_type=content_type,
        policy_source=policy_source
    )
    
    refuse, reason = should_refuse(results)
    if refuse:
        latency_ms = (time.time() - start_time) * 1000
        return PolicyResponse(
            answer="",
            refused=True,
            refusal_reason=reason,
            latency_ms=latency_ms
        )
    
    sources_text = format_sources(results)
    
    if llm is None:
        llm = get_llm()
    
    chain = LLMChain(llm=llm, prompt=POLICY_PROMPT)
    
    try:
        generation_start = time.time()
        answer = chain.run(question=query, sources=sources_text)
        generation_time = (time.time() - generation_start) * 1000
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return PolicyResponse(
            answer="",
            refused=True,
            refusal_reason=f"LLM generation failed: {str(e)}",
            latency_ms=latency_ms
        )
    
    if answer.strip() == "REFUSE":
        latency_ms = (time.time() - start_time) * 1000
        return PolicyResponse(
            answer="",
            refused=True,
            refusal_reason="LLM determined sources insufficient to answer query.",
            latency_ms=latency_ms
        )
    
    cited_ids = extract_citations(answer)
    retrieved_ids = {r["chunk_id"] for r in results}
    
    if not validate_citations(cited_ids, retrieved_ids):
        latency_ms = (time.time() - start_time) * 1000
        return PolicyResponse(
            answer="",
            refused=True,
            refusal_reason="Generated response failed citation validation.",
            latency_ms=latency_ms
        )
    
    citations = build_citations(cited_ids, results)
    
    num_tokens = len(answer.split())
    latency_ms = (time.time() - start_time) * 1000
    
    return PolicyResponse(
        answer=answer,
        refused=False,
        citations=citations,
        latency_ms=latency_ms,
        num_tokens_generated=num_tokens
    )


if __name__ == "__main__":
    print("Testing Generation Pipeline")
    print()
    
    test_queries = [
        "Can I advertise alcohol?",
        "What are the requirements for advertising healthcare products?",
        "Can I use trademarked terms in my ad copy?",
    ]
    
    for i, test_query in enumerate(test_queries, 1):
        print(f"Test {i}/3: {test_query}")
        
        response = generate_policy_response(test_query, limit=5)
        
        print(f"Refused: {response.refused}")
        
        if response.refused:
            print(f"Reason: {response.refusal_reason}")
        else:
            print(f"\nAnswer: {response.answer}\n")
            print(f"Citations: {len(response.citations)}")
            for j, citation in enumerate(response.citations, 1):
                print(f"  {j}. {citation.policy_path}")
        
        if response.latency_ms:
            print(f"Latency: {response.latency_ms:.1f}ms")
        if response.num_tokens_generated:
            print(f"Tokens: {response.num_tokens_generated}")
        
        print()
    
    print("Testing complete")
