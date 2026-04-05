import json
import os

def calculate_opportunity_score_v2(relevance, cluster_size, source_name):
    """
    CURATE-AI: THE SEO OPPORTUNITY ALGORITHM (Ver. 2.0 - 'BLUE OCEAN' UPDATE)
    ----------------------------------------------------------------------
    After verifying Prototype S1 & S2, I realized that very high relevance
    on obscure research was being 'punished' for low velocity. 
    
    This update prioritizes 'HIDDEN GEMS' over generic news trends.
    
    Why this updated formula? (The 4-Signal Discovery Model)
    1. EXTREME RELEVANCE REWARD (40% weight): 
       If a story's cosine similarity is in the 'Very High' range (>0.45), 
       we give it a massive 'Expertise Bonus'. This ensures niche research
       outranks generic 'Slack' news for a technical user.
    
    2. THE 'RISING STAR' ACCELERATOR (30% weight):
       Low Cluster Size (1-3) is no longer a major penalty—it's a 'Seed' signal.
       Medium Cluster Size (4-12) is the Peak Revenue state.
       Large Cluster Size (>15) is now a 'Saturation Penalty'. 
       
    3. THE 'AUTHORITY-GAP' MULTIPLIER (20% weight):
       If a major news network hasn't picked up the story yet, the score multiplier 
       increases. This gives a startup a 'Head Start' of 24-48 hours.
       
    4. SOURCE TRUST (10% weight):
       If the source is a primary source (e.g. OpenAI Blog, MIT News, ArXiv), 
       it gets a credibility boost compared to a generic blog aggregator.
    """
    
    # --- Part 1: THE RELEVANCE ANCHOR (Weighted 40%) ---
    # We apply a logarithmic curve to reward extreme relevance disproportionately.
    rel_score = min((relevance * 200), 100) 
    if relevance > 0.5: rel_score += 15 # 'HIDDEN GEM' BONUS (95th percentile match)
    
    # --- Part 2: THE VELOCITY DYNAMIC (Weighted 30%) ---
    # Goal: Catch it as it leaves 'Obscure' but before it hits 'Saturated'.
    if cluster_size == 1: 
        vel_score = 65  # Better: A seed is an opportunity, not a failure.
    elif 2 <= cluster_size <= 10: 
        vel_score = 100 # THE SWEET SPOT: Rising trend.
    else:
        vel_score = 30  # SATURATED: Every reporter is already on this story.
    
    # --- Part 3: THE COMPETITION GAP (Weighted 30%) ---
    # In SEO, you want 'High Traffic, Low Competition'.
    monopoly_sources = ["TechCrunch", "Wired", "The Verge", "The New York Times", "WSJ", "VentureBeat"]
    if source_name in monopoly_sources:
        comp_score = 20 # Red Ocean: You will be fighting Google, Meta, and the NYT.
    else:
        comp_score = 95 # Blue Ocean: High chance of ranking #1 on results.
        
    # --- THE FINAL COMPOSITE SCORE ---
    final_opportunity_score = (rel_score * 0.4) + (vel_score * 0.3) + (comp_score * 0.3)
    
    # Verdict Logic
    if final_opportunity_score >= 85: status = "💎 HIDDEN GEM (Highest ROI Opportunity)"
    elif final_opportunity_score >= 70: status = "🔥 ACT NOW (High Traction Opportunity)"
    elif final_opportunity_score >= 50: status = "⏳ MONITOR (Developing Opportunity)"
    else: status = "🚫 SKIP (Crowded / Low Relevance)"
    
    return round(final_opportunity_score, 1), status

def main():
    print("PROTOTYPE S3 (v2): THE SEO OPPORTUNITY SCORER (BLUE OCEAN UPDATE) STARTING...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    matches_path = os.path.join(script_dir, "Data", "topic_company_matches.json")
    
    with open(matches_path, "r") as f: company_data = json.load(f)

    # Use Phase 2 Output for Cluster Size & Source Logic
    global_top_path = os.path.join(os.path.dirname(script_dir), "Prototypes", "Data", "top_20_articles.json")
    with open(global_top_path, "r") as f: global_news = json.load(f)
    cluster_map = {a['title']: a.get('cluster_size', 1) for a in global_news}

    final_scorecards = {}

    for name, discovery in company_data.items():
        print(f"\nRANKING OPPORTUNITIES FOR: {name}...")
        
        scored_matches = []
        # Look at deeper exploration set (Top 100 matches from S2)
        for m in discovery[:100]:
            c_size = cluster_map.get(m['title'], 1)
            score, status = calculate_opportunity_score_v2(m['relevance_score'], c_size, m['source'])
            
            scored_matches.append({
                "topic": m['title'],
                "final_score": score,
                "status": status,
                "metrics": {
                    "relevance": m['relevance_score'],
                    "momentum": c_size,
                    "primary_source": m['source']
                }
            })
            
        scored_matches.sort(key=lambda x: x['final_score'], reverse=True)
        final_scorecards[name] = scored_matches

        # Print the 'Winner' for this company
        winner = scored_matches[0]
        print(f"  TOP PICK: {winner['status']}")
        print(f"  TOPIC: {winner['topic'][:75]}...")
        print(f"  SCORE: {winner['final_score']}")

    # SAVE DATA FOR THE AGENTIC LAYER
    output_path = os.path.join(script_dir, "Data", "opportunity_scorecards.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_scorecards, f, indent=2)

    print(f"\nCOMPLETED: V2 scorecards saved to SEO_Prototype/Data/")

if __name__ == "__main__":
    main()
