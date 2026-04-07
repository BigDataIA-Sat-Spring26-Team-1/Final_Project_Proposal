"""
P2: Multi-Label Article Classification (Optimized)
===================================================
Hybrid approach:
  Phase 1: Keyword matching (free, microseconds per article)
  Phase 2: Embedding similarity using all-MiniLM-L6-v2 (free, ~2.5s for 3000 articles)

No LLM calls needed. The same embedding model used for deduplication
is reused here, so in production the article vectors are already computed.
"""
import json
import os
import time
from typing import List, Dict, Optional
from collections import Counter
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# CurateAI Taxonomy with rich descriptions for embedding-based matching.
# Each description is written to maximize semantic separation between categories.
TAXONOMY_DESCRIPTIONS = {
    "LLMs": "Large language models, GPT, Claude, Llama, Gemini, Mistral, transformers, fine-tuning, prompt engineering, text generation, foundation models, language AI",
    "AI Agents": "Autonomous AI agents, agentic workflows, tool use, function calling, LangGraph, AutoGen, CrewAI, multi-agent systems, orchestration, MCP protocol",
    "Computer Vision": "Image recognition, object detection, image generation, diffusion models, Stable Diffusion, Midjourney, video generation, Sora, visual AI, DALL-E",
    "Security": "Cybersecurity, vulnerabilities, hacking, data breaches, ransomware, exploits, CVEs, malware, adversarial attacks, jailbreaking, prompt injection defense",
    "Hardware": "GPUs, NVIDIA, TPUs, chips, semiconductors, TSMC, Intel, AMD, Apple Silicon, H100, CUDA, compute infrastructure, quantum computing",
    "Software Engineering": "Open source, GitHub, APIs, frameworks, programming languages, Rust, Python, Docker, Kubernetes, DevOps, full-stack, software development",
    "AI Policy": "AI regulation, EU AI Act, copyright, ethics, bias, safety, governance, responsible AI, alignment, government policy on artificial intelligence",
    "General AI": "Artificial intelligence research, machine learning, deep learning, neural networks, natural language processing, general technology news",
    "Data Engineering": "Data pipelines, ETL, Airflow, Snowflake, data warehouses, vector databases, embeddings, data lakes, streaming, Apache Spark, data infrastructure",
    "Startups": "Startup funding, venture capital, Series A/B/C, IPO, valuations, unicorns, acquisitions, tech companies, founders, fundraising rounds"
}

# Fast keyword map for Phase 1: keyword → list of categories it triggers
KEYWORD_MAP = {
    "llm": ["LLMs"], "gpt": ["LLMs"], "openai": ["LLMs"], "claude": ["LLMs"],
    "anthropic": ["LLMs"], "llama": ["LLMs"], "gemini": ["LLMs"], "mistral": ["LLMs"],
    "transformer": ["LLMs"], "language model": ["LLMs"], "chatgpt": ["LLMs"],
    "fine-tuning": ["LLMs", "Data Engineering"], "fine tuning": ["LLMs", "Data Engineering"],
    "rag": ["LLMs", "Data Engineering"],
    "prompt injection": ["LLMs", "Security"], "jailbreak": ["Security", "LLMs"],
    "agent": ["AI Agents"], "agentic": ["AI Agents"], "tool use": ["AI Agents"],
    "function calling": ["AI Agents", "LLMs"], "langgraph": ["AI Agents"],
    "crewai": ["AI Agents"], "mcp": ["AI Agents", "Software Engineering"],
    "diffusion": ["Computer Vision"], "stable diffusion": ["Computer Vision"],
    "midjourney": ["Computer Vision"], "image generation": ["Computer Vision", "LLMs"],
    "object detection": ["Computer Vision"], "sora": ["Computer Vision", "LLMs"],
    "vulnerability": ["Security"], "hack": ["Security"], "breach": ["Security"],
    "exploit": ["Security"], "cybersecurity": ["Security"], "ransomware": ["Security"],
    "malware": ["Security"], "adversarial": ["Security", "LLMs"],
    "nvidia": ["Hardware"], "gpu": ["Hardware"], "h100": ["Hardware"],
    "tpu": ["Hardware"], "chip": ["Hardware"], "semiconductor": ["Hardware"],
    "cuda": ["Hardware", "Software Engineering"],
    "open source": ["Software Engineering"], "github": ["Software Engineering"],
    "api": ["Software Engineering"], "framework": ["Software Engineering"],
    "rust": ["Software Engineering"], "python": ["Software Engineering"],
    "docker": ["Software Engineering", "Data Engineering"],
    "kubernetes": ["Software Engineering", "Data Engineering"],
    "regulation": ["AI Policy"], "eu ai act": ["AI Policy"],
    "copyright": ["AI Policy"], "ethics": ["AI Policy"],
    "bias": ["AI Policy", "General AI"], "safety": ["AI Policy", "Security"],
    "pipeline": ["Data Engineering"], "airflow": ["Data Engineering"],
    "snowflake": ["Data Engineering"], "vector database": ["Data Engineering", "LLMs"],
    "embedding": ["Data Engineering", "LLMs"], "etl": ["Data Engineering"],
    "funding": ["Startups"], "valuation": ["Startups"], "series a": ["Startups"],
    "series b": ["Startups"], "series c": ["Startups"],
    "ipo": ["Startups"], "startup": ["Startups"], "acquisition": ["Startups"],
    "unicorn": ["Startups"],
}


def keyword_classify(text: str) -> Optional[Dict[str, float]]:
    """Phase 1: Free keyword-based multi-label classification.
    Returns a dict of {category: weight} or None if no keywords matched."""
    text_lower = text.lower()
    hits: Dict[str, int] = {}

    for keyword, categories in KEYWORD_MAP.items():
        if keyword in text_lower:
            for cat in categories:
                hits[cat] = hits.get(cat, 0) + 1

    if not hits:
        return None

    total = sum(hits.values())
    return {cat: round(count / total, 2) for cat, count in
            sorted(hits.items(), key=lambda x: -x[1])[:3]}


def embedding_classify(article_vectors: np.ndarray, taxonomy_vectors: np.ndarray,
                       category_names: List[str], top_k: int = 3) -> List[Dict[str, float]]:
    """Phase 2: Batch embedding-based classification.
    Computes cosine similarity between all articles and all category descriptions.
    Returns a list of {category: weight} dicts, one per article."""
    # Shape: (num_articles, num_categories)
    sim_matrix = cosine_similarity(article_vectors, taxonomy_vectors)

    results = []
    for i in range(sim_matrix.shape[0]):
        scores = sim_matrix[i]
        top_indices = np.argsort(scores)[::-1][:top_k]

        # Normalize top-k scores to sum to ~1.0
        top_scores = scores[top_indices]
        total = top_scores.sum()
        if total > 0:
            weights = {category_names[idx]: round(float(top_scores[j] / total), 2)
                       for j, idx in enumerate(top_indices) if top_scores[j] > 0}
        else:
            weights = {category_names[top_indices[0]]: 1.0}

        results.append(weights)
    return results


def main():
    # Load article corpus
    articles_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "Prototypes", "Data", "articles.json"
    )
    with open(articles_path, "r", encoding="utf-8") as f:
        all_articles = json.load(f)

    sample = all_articles[:30]

    print(f"P2: Multi-Label Classification (Optimized)")
    print(f"  Total corpus: {len(all_articles)} | Sample: {len(sample)}")
    print(f"  Categories: {list(TAXONOMY_DESCRIPTIONS.keys())}")
    print("-" * 60)

    # Load embedding model (same one used for dedup — reusable in production)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Pre-encode taxonomy descriptions (done once, cached in production)
    category_names = list(TAXONOMY_DESCRIPTIONS.keys())
    category_texts = list(TAXONOMY_DESCRIPTIONS.values())
    taxonomy_vectors = model.encode(category_texts, show_progress_bar=False)

    start = time.time()
    keyword_count = 0
    embedding_count = 0
    multi_label_count = 0
    results = []

    # Phase 1: Try keyword classification first
    needs_embedding = []
    needs_embedding_indices = []

    for i, article in enumerate(sample):
        text = f"{article.get('title', '')} {article.get('summary', '')}"
        kw_result = keyword_classify(text)

        if kw_result is not None:
            keyword_count += 1
            results.append({
                "title": article.get("title", ""),
                "source": article.get("source", ""),
                "method": "keyword",
                "classifications": kw_result
            })
            if len(kw_result) >= 2:
                multi_label_count += 1
        else:
            needs_embedding.append(text)
            needs_embedding_indices.append(i)
            results.append(None)  # placeholder

    # Phase 2: Batch embedding classification for remaining articles
    if needs_embedding:
        article_vectors = model.encode(needs_embedding, show_progress_bar=False)
        emb_results = embedding_classify(article_vectors, taxonomy_vectors, category_names)

        for j, idx in enumerate(needs_embedding_indices):
            article = sample[idx]
            embedding_count += 1
            classifications = emb_results[j]
            results[idx] = {
                "title": article.get("title", ""),
                "source": article.get("source", ""),
                "method": "embedding",
                "classifications": classifications
            }
            if len(classifications) >= 2:
                multi_label_count += 1

    elapsed = time.time() - start

    # Print results
    for r in results:
        labels_str = " | ".join([f"{k}({v:.2f})" for k, v in r["classifications"].items()])
        print(f"  [{r['method']:>9}] {r['title'][:55]}...")
        print(f"             → {labels_str}")

    # Save
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "Data", "multilabel_classifications.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Full corpus benchmark
    print("\n" + "-" * 60)
    print("FULL CORPUS BENCHMARK (embedding classification only)")
    bench_start = time.time()
    all_texts = [f"{a.get('title', '')} {a.get('summary', '')}" for a in all_articles]
    all_vectors = model.encode(all_texts, show_progress_bar=True)
    all_classifications = embedding_classify(all_vectors, taxonomy_vectors, category_names)
    bench_elapsed = time.time() - bench_start
    print(f"  Classified {len(all_articles)} articles in {bench_elapsed:.2f}s")
    print(f"  That's {len(all_articles)/bench_elapsed:.0f} articles/second")

    # Save full corpus classifications
    full_output_path = os.path.join(script_dir, "Data", "full_corpus_multilabel.json")
    full_results = []
    for i, article in enumerate(all_articles):
        full_results.append({
            "title": article.get("title", ""),
            "source": article.get("source", ""),
            "classifications": all_classifications[i]
        })
    with open(full_output_path, "w", encoding="utf-8") as f:
        json.dump(full_results, f, indent=2, ensure_ascii=False)

    # Summary
    print("\n" + "=" * 60)
    print("P2 MULTI-LABEL CLASSIFICATION REPORT")
    print("=" * 60)
    print(f"  Sample size:       {len(sample)}")
    print(f"  Keyword (free):    {keyword_count} ({keyword_count/len(sample)*100:.0f}%)")
    print(f"  Embedding (free):  {embedding_count} ({embedding_count/len(sample)*100:.0f}%)")
    print(f"  LLM calls:         0 (zero cost)")
    print(f"  Multi-Label (2+):  {multi_label_count} ({multi_label_count/len(sample)*100:.0f}%)")
    print(f"  Target (>60%):     {'PASS' if multi_label_count/len(sample) > 0.6 else 'FAIL'}")
    print(f"  Sample time:       {elapsed:.2f}s")
    print(f"  Full corpus time:  {bench_elapsed:.2f}s for {len(all_articles)} articles")
    print(f"  Saved:             {output_path}")
    print(f"  Full corpus:       {full_output_path}")


if __name__ == "__main__":
    main()
