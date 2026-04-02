import json
import os
import time
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# 1. User Personas
USER_PROFILES = [
    {
        "id": "user_aakash",
        "name": "The Security Obsessive",
        "bio": "I track all major software leaks, cyberattacks, and security vulnerabilities. I care deeply about LLM security, but I find hardware and venture capital funding boring.",
        "interested_categories": ["Security", "AI & Models"],
        "ignored_categories": ["Hardware", "Startups & VC"]
    },
    {
        "id": "user_investor",
        "name": "The AI VC",
        "bio": "I'm looking for the next big AI startup and funding news. I want to see valuations and new product launches from OpenAI, Anthropic, and Google.",
        "interested_categories": ["Startups & VC", "AI & Models"],
        "ignored_categories": ["Security", "Software & Dev"]
    }
]

def generate_personalized_newsletter(all_articles: List[Dict], global_top_20: List[Dict], user: Dict, model: SentenceTransformer):
    """
    Implements the 'Dual-Layer' Newsletter:
    1. Global Top 20 (Re-ordered for User)
    2. Niche Top 10 (Picked from the other 680 articles)
    """
    
    # Pre-calculate bio embedding
    user_vector = model.encode([user["bio"]])[0]
    
    # --- Layer 1: Re-order the Global Top 20 Highlights ---
    global_ranked = []
    top_20_ids = set([a["id"] for a in global_top_20])
    
    for article in global_top_20:
        article_text = f"{article['title']} {article.get('summary', '')}"
        article_vector = model.encode([article_text])[0]
        semantic_sim = cosine_similarity([user_vector], [article_vector])[0][0]
        
        # Category boost
        cat = article.get("topic_classification", {}).get("category", "")
        boost = 0.2 if cat in user["interested_categories"] else -0.2 if cat in user["ignored_categories"] else 0
        
        article["relevance_score"] = float(semantic_sim + boost)
        global_ranked.append(article)
    
    global_ranked = sorted(global_ranked, key=lambda x: x["relevance_score"], reverse=True)

    # --- Layer 2: Find 'Niche Gems' (Excluding Top 20) ---
    other_articles = [a for a in all_articles if a["id"] not in top_20_ids]
    niche_candidates = []
    
    # We only encode a subset of candidates to save time in the prototype
    # In production, all 700 are already pre-encoded in a Vector DB
    print(f"  Scanning {len(other_articles)} potential niche stories for {user['name']}...")
    
    for article in other_articles:
        # For the niche, we prioritize 'Specific' stories that match bio
        article_text = f"{article['title']} {article.get('summary', '')}"
        article_vector = model.encode([article_text], show_progress_bar=False)[0]
        semantic_sim = cosine_similarity([user_vector], [article_vector])[0][0]
        
        # We also want to give a slight bump to niche clusters (>1 source)
        cluster_bonus = 0.1 if article.get("cluster_size", 1) > 1 else 0
        
        article["niche_relevance"] = float(semantic_sim + cluster_bonus)
        niche_candidates.append(article)
        
    niche_top_10 = sorted(niche_candidates, key=lambda x: x["niche_relevance"], reverse=True)[:10]

    return global_ranked, niche_top_10

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    
    # 1. Load the Entire Database (700+)
    db_path = os.path.join(data_dir, "pipeline_prototype_output.json")
    # 2. Load the Ranked Highlights (Top 20)
    top_20_path = os.path.join(data_dir, "top_20_articles.json")
    
    with open(db_path, "r") as f: all_db = json.load(f)
    with open(top_20_path, "r") as f: top_20 = json.load(f)

    print(f"Initializing Transformer model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    for user in USER_PROFILES:
        print("\n" + "="*80)
        print(f"GENERATING NEWSLETTER FOR: {user['name'].upper()}")
        print(f"STRATEGY: Highlights Reordering + Niche Gems Selection")
        print("="*80)
        
        personal_high, personal_niche = generate_personalized_newsletter(all_db, top_20, user, model)
        
        print("\nSECTION 1: TODAY'S CURATED HIGHLIGHTS (Personalized Order)")
        for i, a in enumerate(personal_high[:5]):
            print(f"  [{i+1}] {a['title'][:70]}... (Score: {a['relevance_score']:.2f})")

        print("\nSECTION 2: YOUR NICHE SELECTIONS (Hidden Gems Found for You)")
        for i, a in enumerate(personal_niche):
            print(f"  [+] {a['title'][:70]}... (Similarity: {a['niche_relevance']:.2f})")

if __name__ == "__main__":
    main()
