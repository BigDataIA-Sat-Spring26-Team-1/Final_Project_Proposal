import json
import os
from datetime import datetime

def generate_markdown_newsletter(user_name, persona_type, highlights, niche_gems, cache):
    """
    Assembles the final Markdown newsletter layout.
    """
    date_str = datetime.now().strftime("%B %d, %Y")
    
    md = f"""# 📬 CurateAI: Your Daily Intelligence Report
**Date:** {date_str} | **Reader:** {user_name} | **Persona:** {persona_type}

---

## 🌟 Today's High-Impact Highlights
*The biggest stories in tech, ranked and summarized for your professional lens.*

"""
    
    # Layer 1: Global Highlights
    for i, article in enumerate(highlights[:5]):
        a_id = article["id"]
        # Use Cached Persona Summary if available, fallback to AI Summary, then summary
        summary = cache.get(a_id, {}).get(persona_type) or article.get("ai_summary") or article.get("summary")
        source = article.get("source_name", "Unknown")
        
        md += f"### {i+1}. {article['title']}\n"
        md += f"**Source:** {source} | **Trending Score:** {article.get('cluster_size', 1)} Sources\n\n"
        md += f"{summary}\n\n"
        md += f"[Read Original Article]({article.get('source_url', '#')})\n\n"

    md += """---

## 💎 Personalized Niche Selections
*Hidden gems from the deeper web, hand-picked for your specific bio.*

"""

    # Layer 2: Niche Gems
    for i, article in enumerate(niche_gems[:5]):
        a_id = article["id"]
        summary = cache.get(a_id, {}).get(persona_type) or article.get("ai_summary") or article.get("summary")
        source = article.get("source_name", "Unknown")
        
        md += f"#### [+] {article['title']}\n"
        md += f"**Why it's for you:** Matches your interest in {article.get('topic_classification', {}).get('category', 'Tech')}\n\n"
        md += f"{summary}\n\n"
        md += f"[Source: {source}]({article.get('source_url', '#')})\n\n"

    md += """---
*You are receiving this digest because you are a **CurateAI Beta User**. Manage your interests [here](#).*
"""
    return md

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    
    # 1. Load the Feed Logic (from P8)
    # 2. Load the Persona Cache (from P9)
    
    # For this demo, let's generate it for the 'Security Obsessive'
    # We simulate the results from P8/P9 because we have the files saved
    
    persona_demo_path = os.path.join(data_dir, "personalized_feed_demo.json")
    cache_path = os.path.join(data_dir, "persona_cache.json")
    all_articles_path = os.path.join(data_dir, "top_20_articles.json")

    if not os.path.exists(persona_demo_path) or not os.path.exists(cache_path):
        print("Required data files missing. Make sure Prototypes 8 and 9 were successfully run.")
        return

    with open(persona_demo_path, "r") as f: niche_gems = json.load(f)
    with open(all_articles_path, "r") as f: highlights = json.load(f)
    with open(cache_path, "r") as f: cache = json.load(f)

    # USER AAKASH (Security Researcher)
    print("Generating Newsletter for User: Aakash (Security Persona)...")
    aakash_md = generate_markdown_newsletter(
        "Aakash", "Security", highlights, niche_gems, cache
    )
    
    # USER INVESTOR (VC Persona)
    print("Generating Newsletter for User: Investor (VC Persona)...")
    investor_md = generate_markdown_newsletter(
        "Venture Capital Guru", "VC", highlights, niche_gems, cache
    )

    # Save outputs
    os.makedirs(os.path.join(data_dir, "Newsletters"), exist_ok=True)
    
    with open(os.path.join(data_dir, "Newsletters", "aakash_newsletter.md"), "w") as f:
        f.write(aakash_md)
    with open(os.path.join(data_dir, "Newsletters", "investor_newsletter.md"), "w") as f:
        f.write(investor_md)

    print("\nPROTOTYPE 10 COMPLETE: Final newsletters saved to Prototypes/Data/Newsletters/")

if __name__ == "__main__":
    main()
