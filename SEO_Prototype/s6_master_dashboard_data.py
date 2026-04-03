import json
import os

def main():
    print("PROTOTYPE S6: THE FINAL SEO INTELLIGENCE MASTER SYNC STARTING...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. LOAD THE 100% CLEAN NEURAL SIGNAL (from S5 v7)
    velocity_path = os.path.join(script_dir, "Data", "seo_velocity_report.json")
    if not os.path.exists(velocity_path):
        print("Run Prototype S5 first.")
        return
    with open(velocity_path, "r") as f: surging_raw = json.load(f)

    # 2. LOAD OPPORTUNITIES & BRIEFS
    scorecards_path = os.path.join(script_dir, "Data", "opportunity_scorecards.json")
    with open(scorecards_path, "r") as f: scorecards = json.load(f)
    
    # LOAD FULL CORPUS FOR GLOBAL STATS
    corpus_path = os.path.join(os.path.dirname(script_dir), "Prototypes", "Data", "articles.json")
    with open(corpus_path, "r") as f: full_corpus = json.load(f)

    # 3. BUILD THE 'DASHBOARD PAYLOAD'
    # We sort strictly by VELOCITY highlight for discovery
    # But only keep the TOP CLEAN SIGNALS
    surging_gems = []
    for item in surging_raw:
        # Convert the string velocity '+50.0%' back to float for sorting
        vel_val = float(item['velocity'].strip('%'))
        
        surging_gems.append({
            "entity": item['entity'],
            "velocity_v": vel_val,
            "total": item['total_mentions'],
            "label": "BREAKING" if item['previous_window'] == 0 else "SURGING" if vel_val > 50 else "STABLE"
        })
    
    # Sort by Velocity descending
    surging_gems.sort(key=lambda x: x['velocity_v'], reverse=True)

    # Part B: Top Opportunities per Company (Summarized)
    company_highlights = []
    for comp_name, matches in scorecards.items():
        top = matches[0]
        company_highlights.append({
            "company": comp_name,
            "opportunity": top['topic'][:60],
            "score": top['final_score'],
            "status": top['status']
        })

    # 4. CONSOLIDATE MASTER REPORT
    master_dashboard_report = {
      "timestamp": "2026-04-10T20:15:00Z",
      "global_stats": {
        "articles_scanned": len(full_corpus),
        "entities_identified": len(surging_raw),
        "high_signal_trends": len([g for g in surging_gems if g['velocity_v'] > 80])
      },
      "surging_trends": surging_gems[:15], # Top 15 CLEAN Neural Discoveries
      "business_opportunities": company_highlights
    }

    # 5. DASHBOARD VIEW-DEMO (Verification)
    print("\n--- FINAL SEO DASHBOARD (NLP-VERIFIED) ---")
    for gem in master_dashboard_report['surging_trends']:
        # This will now match S5 v7 exactly!
        print(f"  [{gem['label']}] {gem['entity']:<15} | Velocity: {gem['velocity_v']:+7.1f}% | (Count: {gem['total']})")

    print("\n--- COMPANY ACTION ITEMS ---")
    for item in master_dashboard_report['business_opportunities']:
        print(f"  {item['company']:<10} -> {item['status']} | {item['opportunity']}...")

    # 6. SAVE MASTER JSON
    output_path = os.path.join(script_dir, "Data", "seo_master_dashboard_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(master_dashboard_report, f, indent=2)

    print(f"\nCOMPLETED: Finalized SEO Intelligence Data.")

if __name__ == "__main__":
    main()
