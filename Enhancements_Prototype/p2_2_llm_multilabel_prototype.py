"""
P2_2: Multi-Label Classification via LLM (Dynamic Labels)
==========================================================
Uses GPT-4o-mini to assign 2-3 topic labels per article.
Labels are NOT from a fixed taxonomy — the LLM decides freely.
Runs on the deduplicated corpus (~699 articles) asynchronously with rate limiting.
Logs detailed cost, token, and latency metrics.
"""
import json
import os
import time
import asyncio
from datetime import datetime
from typing import List, Dict
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
aclient = AsyncOpenAI()

# Pricing: GPT-4o-mini (as of 2026)
INPUT_COST_PER_1M = 0.15   # $/1M input tokens
OUTPUT_COST_PER_1M = 0.60  # $/1M output tokens

SYSTEM_PROMPT = """You are a precise article classifier for a tech news platform.
Given an article's title and summary, assign exactly 2-3 topic labels that best describe its content.
Use short, specific labels (1-3 words each). Assign a weight (0.0-1.0) to each label reflecting relevance.
Weights should sum to approximately 1.0.

Return JSON: {"labels": [{"label": "...", "weight": 0.5}, ...]}"""


def get_article_text(article: dict) -> str:
    """Build classification input from title + summary. Handles missing summaries."""
    title = article.get("title", "").strip()
    summary = (article.get("summary") or "").strip()
    if summary and len(summary) > 10:
        return f"Title: {title}\nSummary: {summary[:300]}"
    return f"Title: {title}"

async def aclassify_single(article_text: str, sem: asyncio.Semaphore) -> tuple:
    """Classify one article asynchronously with a semaphore for rate limiting."""
    async with sem:
        start = time.time()
        try:
            response = await aclient.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": article_text}
                ],
                response_format={"type": "json_object"},
                max_tokens=150
            )
            latency = time.time() - start
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            try:
                data = json.loads(response.choices[0].message.content)
                labels = {item["label"]: item["weight"] for item in data.get("labels", [])}
            except (json.JSONDecodeError, KeyError, TypeError):
                labels = {"Uncategorized": 1.0}
            
            return labels, usage, latency
        except Exception as e:
            return {"Error": 1.0}, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, 0.0

async def amain():
    # Load deduplicated corpus
    corpus_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "SEO_Prototype", "Data", "pipeline_prototype_output.json"
    )
    with open(corpus_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    print(f"P2_2: LLM Multi-Label Classification ASYNC (Dynamic Labels)")
    print(f"  Corpus: {len(articles)} deduplicated articles")
    print(f"  Model: gpt-4o-mini")
    print(f"  Concurrency limit: 20 parallel requests")
    print("=" * 60)

    # Track metrics
    total_input_tokens = 0
    total_output_tokens = 0
    total_latency = 0.0
    all_labels_seen = {}
    results = []
    errors = 0

    start_time = time.time()
    
    # Process asynchronously with a semaphore to cap at 20 concurrent requests
    sem = asyncio.Semaphore(20)
    tasks = []
    
    for article in articles:
        text = get_article_text(article)
        tasks.append(aclassify_single(text, sem))
        
    print(f"Submitting {len(tasks)} async classification tasks...")
    
    # Execute batch
    batch_results = await asyncio.gather(*tasks)
    
    for i, (labels, usage, latency) in enumerate(batch_results):
        article = articles[i]
        if "Error" in labels:
            errors += 1
            print(f"  [{i+1:3d}] ERROR classification failed for: {article.get('title', '')[:45]}")
            
        total_input_tokens += usage["prompt_tokens"]
        total_output_tokens += usage["completion_tokens"]
        total_latency += latency

        # Track label frequency
        for label in labels:
            all_labels_seen[label] = all_labels_seen.get(label, 0) + 1

        results.append({
            "title": article.get("title", ""),
            "source": article.get("source_name", ""),
            "labels": labels,
            "tokens": usage,
            "latency_s": round(latency, 3)
        })

    total_time = time.time() - start_time

    # Cost calculation
    input_cost = (total_input_tokens / 1_000_000) * INPUT_COST_PER_1M
    output_cost = (total_output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
    total_cost = input_cost + output_cost

    # Save results
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "Data", "p2_2_llm_classifications.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Save metrics report
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "corpus_size": len(articles),
        "model": "gpt-4o-mini",
        "total_time_s": round(total_time, 2),
        "avg_latency_per_article_s": round(total_latency / len(articles), 3),
        "articles_per_second": round(len(articles) / total_time, 2),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "avg_tokens_per_article": round((total_input_tokens + total_output_tokens) / len(articles), 1),
        "input_cost_usd": round(input_cost, 4),
        "output_cost_usd": round(output_cost, 4),
        "total_cost_usd": round(total_cost, 4),
        "cost_per_article_usd": round(total_cost / len(articles), 6),
        "unique_labels_discovered": len(all_labels_seen),
        "top_20_labels": dict(sorted(all_labels_seen.items(), key=lambda x: -x[1])[:20]),
        "errors": errors,
        "multi_label_rate": round(sum(1 for r in results if len(r["labels"]) >= 2) / len(results) * 100, 1) if len(results) > 0 else 0.0
    }

    metrics_path = os.path.join(script_dir, "Data", "p2_2_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Print final report
    print("\n" + "=" * 60)
    print("P2_2 LLM CLASSIFICATION ASYNC — FINAL REPORT")
    print("=" * 60)
    print(f"  Articles classified:     {len(articles)}")
    print(f"  Errors:                  {errors}")
    print(f"  Total wall time:         {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Throughput:              {len(articles)/total_time:.1f} articles/s")
    print(f"  ---")
    print(f"  Input tokens:            {total_input_tokens:,}")
    print(f"  Output tokens:           {total_output_tokens:,}")
    print(f"  Total tokens:            {total_input_tokens + total_output_tokens:,}")
    print(f"  Avg tokens/article:      {(total_input_tokens + total_output_tokens)/len(articles):.0f}")
    print(f"  ---")
    print(f"  Input cost:              ${input_cost:.4f}")
    print(f"  Output cost:             ${output_cost:.4f}")
    print(f"  TOTAL COST:              ${total_cost:.4f}")
    print(f"  Cost/article:            ${total_cost/len(articles):.6f}")
    print(f"  Projected daily (800):   ${total_cost/len(articles)*800:.4f}")
    print(f"  Projected monthly:       ${total_cost/len(articles)*800*30:.2f}")
    print(f"  ---")
    print(f"  Unique labels found:     {len(all_labels_seen)}")
    print(f"  Multi-label rate (2+):   {metrics['multi_label_rate']}%")
    print(f"  Top 10 labels:")
    for label, count in sorted(all_labels_seen.items(), key=lambda x: -x[1])[:10]:
        print(f"    {label:30s} | {count}")
    print(f"  ---")
    print(f"  Results: {output_path}")
    print(f"  Metrics: {metrics_path}")

def main():
    asyncio.run(amain())

if __name__ == "__main__":
    main()
