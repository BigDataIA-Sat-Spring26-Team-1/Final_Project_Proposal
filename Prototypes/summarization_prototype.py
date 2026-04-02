import json
import os
import time
from typing import List, Dict, Set
from openai import OpenAI
from dotenv import load_dotenv

# Re-using our personas from Prototype 8
USER_PERSONAS = {
    "Security": "A cybersecurity researcher interested in software vulnerabilities, data breaches, and LLM security.",
    "VC": "A Venture Capitalist looking for startup funding, valuations, and major product launches."
}

def generate_multi_persona_cache(unique_articles: List[Dict], client: OpenAI) -> Dict:
    """
    Simulates the Persona-First Cache.
    For each unique article, generate a summary for EACH persona type.
    """
    persona_cache = {} # Key: article_id, Value: {persona_a: summary, persona_b: summary}
    
    print(f"Generating Persona-First Cache for {len(unique_articles)} unique stories across {len(USER_PERSONAS)} persona archetypes...")
    
    for article in unique_articles:
        a_id = article["id"]
        persona_cache[a_id] = {}
        
        context = article.get("full_text") or article.get("summary") or "No content available."
        context = context[:2000] # Token window
        
        for p_name, p_desc in USER_PERSONAS.items():
            print(f"  Writing '{p_name}' summary for: {article['title'][:40]}...")
            
            prompt = f"""
            Summarize this for a {p_desc}. Write exactly two professional sentences focusing on what matters to THEM.
            ARTICLE: {article['title']} | {context}
            """
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150
                )
                persona_cache[a_id][p_name] = response.choices[0].message.content.strip()
            except:
                persona_cache[a_id][p_name] = "Error generating summary."
                
    return persona_cache

def main():
    load_dotenv()
    client = OpenAI()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    
    # 1. Load the results of Prototype 8 (Personalized Feeds for 2 Users)
    demo_path = os.path.join(data_dir, "personalized_feed_demo.json")
    if not os.path.exists(demo_path):
        print("Run Prototype 8 first.")
        return
        
    with open(demo_path, "r") as f:
        # For simplicity, we just take the first user's sample from the demo
        articles = json.load(f)[:2] # Let's just summarize 2 articles for speed/cost

    # 2. RUN THE PERSONA-FIRST CACHE
    # This generates ONE summary per PERSONA, regardless of how many USERS there are.
    cache = generate_multi_persona_cache(articles, client)
    
    # 3. DEMONSTRATE THE CACHE (Different versions of the SAME Article)
    print("\n" + "="*80)
    print("PERSONA-FIRST CACHE DEMO: TWO DIFFERENT PERSPECTIVES ON THE SAME STORY")
    print("="*80)
    
    for a_id, versions in cache.items():
        original = [a for a in articles if a["id"] == a_id][0]
        print(f"\nORIGINAL TITLE: {original['title']}")
        print("-" * 40)
        print(f"SECURITY VERSION: {versions['Security']}")
        print("-" * 40)
        print(f"VC VERSION: {versions['VC']}")
        print("-" * 40)

    # Save cache for Layout Engine
    output_path = os.path.join(data_dir, "persona_cache.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
