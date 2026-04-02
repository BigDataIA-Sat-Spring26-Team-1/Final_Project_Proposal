import json
import os
import time
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# 1. Define the Taxonomy
# We prioritize GenAI, as this is an AI-focused newsletter
AXIOMATIC_KEYWORDS = {
    "AI & Models": ["llm", "openai", "claude", "anthropic", "gpt-4", "llama", "gemini", "mistral", "transformer", "genai", "sora"],
    "Security": ["vulnerability", "hack", "leaked", "breach", "exploit", "cybersecurity", "cve", "ransomware", "trojan", "malware"],
    "Startups & VC": ["founding", "valuation", "series", "ipo", "funding", "startup", "venture", "acquisition", "unicorn"],
    "Hardware": ["nvidia", "gpu", "h100", "tpu", "chip", "semiconductor", "tsmc", "intel", "amd", "apple silicon"],
    "Software & Dev": ["open source", "github", "api", "framework", "library", "coding", "full stack", "react", "rust", "python"]
}

DEFAULT_CATEGORY = "General Tech"

class TopicClassification(BaseModel):
    category: str
    confidence: float
    reasoning: str

def hybrid_classify(title: str, summary: str, client: OpenAI) -> TopicClassification:
    # --- Phase 1: Axiomatic Keyword Check (Fast/Free) ---
    clean_text = f"{title} {summary}".lower()
    for category, keywords in AXIOMATIC_KEYWORDS.items():
        if any(keyword in clean_text for keyword in keywords):
            return TopicClassification(
                category=category,
                confidence=0.9,
                reasoning=f"Matched axiomatic keywords: {[k for k in keywords if k in clean_text]}"
            )
    
    # --- Phase 2: LLM Fallback (Smart/Paid) ---
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Categorize this tech news into one of these: {list(AXIOMATIC_KEYWORDS.keys()) + [DEFAULT_CATEGORY]}"},
                {"role": "user", "content": f"Title: {title}\nSummary: {summary}"}
            ],
            response_format=TopicClassification,
        )
        return response.choices[0].message.parsed
    except Exception as e:
        return TopicClassification(category=DEFAULT_CATEGORY, confidence=0.5, reasoning=f"Error: {str(e)}")

def main():
    load_dotenv()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    input_path = os.path.join(data_dir, "top_20_articles.json") # We classify the Top 20 first
    
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    # Note: Requires OPENAI_API_KEY env variable
    client = OpenAI()
    
    print(f"Starting classification for {len(articles)} articles...")
    start_time = time.time()
    
    keyword_hits = 0
    llm_hits = 0
    
    for article in articles:
        result = hybrid_classify(article['title'], article.get('summary', ''), client)
        article['topic_classification'] = result.dict()
        
        if "Matched axiomatic keywords" in result.reasoning:
            keyword_hits += 1
        else:
            llm_hits += 1
            
        print(f"  [{result.category}] {article['title'][:60]}... ({result.confidence*100:.0f}%)")

    # Save enriched output
    output_path = os.path.join(data_dir, "classified_top_20.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    total_time = time.time() - start_time
    print(f"\nClassification complete in {total_time:.2f}s")
    print(f"Efficiency Stats: {keyword_hits} Keyword Hits (Free) | {llm_hits} LLM Calls (Paid)")
    print(f"Saved to: {output_path}")

if __name__ == "__main__":
    main()
