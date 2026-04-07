"""
P3: Enhanced Personalization Scoring
=====================================
Compares 3 scoring methods for personalization:
  METHOD A: Vector Similarity Only (Current baseline)
  METHOD B: Multi-Label Category Overlap Only
  METHOD C: Combined (40% Vector + 35% Overlap + 25% Trend)

Uses user profiles from P1 and article classifications from P2.
"""
import json
import os
import time
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def calculate_overlap_score(user_weights: dict, article_weights: dict) -> float:
    """Calculates dot product of category weights + boost for 3+ overlaps."""
    score = 0.0
    matches = 0
    
    for category, u_weight in user_weights.items():
        if category in article_weights:
            a_weight = article_weights[category]
            score += (u_weight * a_weight)
            if u_weight > 0.1 and a_weight > 0.1:
                matches += 1
                
    # 20% boost if 3 or more meaningful categories match
    if matches >= 3:
        score *= 1.20
        
    # Cap at 1.0 (though it rarely exceeds it due to normalization)
    return min(1.0, score)

def normalize_trend(cluster_size: int, popularity: int) -> float:
    """Normalizes trend signals to 0.0-1.0 range."""
    # Assuming cluster size ~ 1 to 10
    # Assuming popularity ~ 0 to 1000
    c_score = min(1.0, cluster_size / 5.0)
    p_score = min(1.0, popularity / 500.0)
    return (c_score * 0.6) + (p_score * 0.4)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    
    # 1. Load User Profiles (from P1)
    linkedin_path = os.path.join(data_dir, "linkedin_profile.json")
    resume_path = os.path.join(data_dir, "resume_profile.json")
    
    with open(linkedin_path, "r") as f: user_1 = json.load(f)
    with open(resume_path, "r") as f: user_2 = json.load(f)
    
    # Add a mock 3rd user (e.g., policy & startups focused)
    user_3 = {
        "name": "Alex VC",
        "job_title": "AI Policy & Startup Investor",
        "bio_summary": "Investor tracking the intersection of AI startups, regulatory policy, and new software frameworks. I invest in early-stage open source projects that navigate EU AI Act compliance.",
        "category_weights": {
            "Startups": 0.9, "AI Policy": 0.8, "Software Engineering": 0.5, "Security": 0.4
        }
    }
    
    users = [user_1, user_2, user_3]

    # 2. Load Articles (Deduplicated corpus vs P2 classifications)
    articles_path = os.path.join(os.path.dirname(script_dir), "SEO_Prototype", "Data", "pipeline_prototype_output.json")
    with open(articles_path, "r") as f: db_articles = json.load(f)
    
    # We map titles to the P2 multi-label classifications
    p2_path = os.path.join(data_dir, "full_corpus_multilabel.json")
    with open(p2_path, "r") as f: p2_classes = json.load(f)
    
    class_map = {a["title"]: a["classifications"] for a in p2_classes}
    
    print("P3: Enhanced Personalization Scoring")
    print(f"Loaded {len(users)} users and {len(db_articles)} articles")
    print(f"Initializing SentenceTransformer...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("Pre-computing article vectors...")
    # Pre-compute article vectors
    article_texts = [f"{a.get('title','')} {a.get('summary','')}" for a in db_articles]
    article_vectors = model.encode(article_texts, show_progress_bar=False)

    print("\n" + "="*80)
    all_results = []
    
    for user in users:
        print(f"\nEvaluating for User: {user['name']} ({user['job_title']})")
        user_vector = model.encode([user["bio_summary"]])[0]
        
        scored_articles = []
        for i, article in enumerate(db_articles):
            title = article.get("title", "")
            
            # Skip articles without classifications
            if title not in class_map:
                continue
                
            article_weights = class_map[title]
            
            # --- Score Calculations ---
            # 1. Vector Similarity (Current Baseline)
            vec_sim = cosine_similarity([user_vector], [article_vectors[i]])[0][0]
            
            # 2. Category Overlap Score (New Multi-label integration)
            overlap_score = calculate_overlap_score(user.get("category_weights", {}), article_weights)
            
            # 3. Trend Signal
            trend_score = normalize_trend(article.get("cluster_size", 1), article.get("popularity_signal", 0))
            
            # 4. Method C: Combined Hybrid Score
            # (vec×0.40) + (overlap×0.35) + (trend×0.25)
            hybrid_score = (vec_sim * 0.40) + (overlap_score * 0.35) + (trend_score * 0.25)
            
            scored_articles.append({
                "title": title,
                "vec_score": float(vec_sim),
                "overlap_score": float(overlap_score),
                "hybrid_score": float(hybrid_score),
                "categories": article_weights
            })
            
        # Top 10 by Method A (Vector Only)
        top_a = sorted(scored_articles, key=lambda x: x["vec_score"], reverse=True)[:10]
        
        # Top 10 by Method C (Hybrid)
        top_c = sorted(scored_articles, key=lambda x: x["hybrid_score"], reverse=True)[:10]
        
        # Comparison logic
        set_a = set([a["title"] for a in top_a])
        set_c = set([a["title"] for a in top_c])
        difference = len(set_a.symmetric_difference(set_c)) / 2 # Number of articles replaced
        
        print(f"Shift analysis: {int(difference)} out of 10 articles changed when moving from Vector-only to Hybrid.")
        
        print("\n  METHOD A: Vector Similarity Only")
        for j, a in enumerate(top_a[:5]):
            print(f"    {j+1}. [{a['vec_score']:.2f}] {a['title'][:60]}...")
            
        print("\n  METHOD C: Hybrid (40% Vec + 35% Overlap + 25% Trend)")
        for j, a in enumerate(top_c[:5]):
            cats = " | ".join([f"{k}({v})" for k,v in a['categories'].items()])
            print(f"    {j+1}. [{a['hybrid_score']:.2f}] {a['title'][:60]}...")
            print(f"    {j+1}. [{a['hybrid_score']:.2f}] {a['title'][:60]}...")
            print(f"        → {cats}")
            
        all_results.append({
            "user_name": user['name'],
            "job_title": user['job_title'],
            "shift_difference": int(difference),
            "method_a_top_10": top_a,
            "method_c_top_10": top_c
        })
        
    output_path = os.path.join(data_dir, "p3_enhanced_scoring_results.json")
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved P3 scoring results to: {output_path}")
            
if __name__ == "__main__":
    main()
