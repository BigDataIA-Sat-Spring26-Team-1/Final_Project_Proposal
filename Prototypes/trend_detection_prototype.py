import json
import os
import time
from typing import List, Dict

# --- TREND DETECTION PARAMETERS ---
# These are the magic numbers we use to decide a story's "status"
# Editorial Weight: How many unique sources confirmed the story
BREAKING_THRES = 3         # Story hit 3+ news outlets simultaneously
TRENDING_THRES = 2         # Story hit 2 news outlets

# Viral Weight: How many community upvotes/points it gathered
# We adjust these thresholds based on the median score of the day
COMMUNITY_FAVORITE_THRES = 150 
VIRAL_SPIKE_THRES = 500

def detect_trends(articles: List[Dict]) -> List[Dict]:
    """Mathematical status assignment based on editorial density and social signal."""
    for article in articles:
        c_size = article.get("cluster_size", 1)
        pop_signal = article.get("popularity_signal", 0)
        
        status = "REGULAR"
        priority_boost = 0
        
        # 1. Editorial Density Logic (The "News Momentum")
        if c_size >= BREAKING_THRES:
            status = "BREAKING"
            priority_boost += 50
        elif c_size >= TRENDING_THRES:
            status = "TRENDING"
            priority_boost += 20
            
        # 2. Viral Logic (The "People's Choice")
        if pop_signal >= VIRAL_SPIKE_THRES:
            # If a story is both Breaking and Viral, it's "MEGA-VIRAL"
            if status == "BREAKING":
                status = "BREAKING-VIRAL"
            else:
                status = "VIRAL"
            priority_boost += 40
        elif pop_signal >= COMMUNITY_FAVORITE_THRES:
            if status == "REGULAR":
                status = "COMMUNITY-PICK"
            priority_boost += 15
            
        # 3. Assignment
        article["trend_status"] = status
        article["ranking_score"] = (c_size * 10) + pop_signal + priority_boost
        
    # Sort entire dataset by our new ranking_score
    return sorted(articles, key=lambda x: x["ranking_score"], reverse=True)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    
    # We run this on the CLASSIFIED top 20 to get the final rank-ordered newsletter
    input_path = os.path.join(data_dir, "classified_top_20.json") 
    
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    print(f"Analyzing {len(articles)} articles for trends...")
    ranked_articles = detect_trends(articles)
    
    # Output Final Trend Report
    print("\n" + "="*50)
    print("TREND DETECTION & RANKING REPORT")
    print("="*50)
    
    for i, a in enumerate(ranked_articles[:10]):
        status_tag = f"[{a['trend_status']}]"
        print(f"{i+1}. {status_tag:<18} SCORE: {a['ranking_score']:<5} | {a['title'][:60]}...")
        if a['cluster_size'] > 1:
            print(f"   (Verified by {a['cluster_size']} sources: {', '.join(a['all_sources'][:3])})")

    # Save to final stage for Prototype 8 (Writer Agent)
    output_path = os.path.join(data_dir, "final_ranked_news.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ranked_articles, f, indent=2, ensure_ascii=False)
        
    print(f"\nFinal ranked dataset saved to: {output_path}")

if __name__ == "__main__":
    main()
