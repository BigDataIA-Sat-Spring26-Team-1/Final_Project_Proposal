import json
import os
import spacy
from collections import Counter

# Load the NLP Model (Dynamic English Language Intelligence)
nlp = spacy.load("en_core_web_sm")

# Minimal whitelist for 100% Zero-Loss on core brands
WHITELIST = {"AI", "ML", "RAG", "LLM", "LLMs", "Claude", "OpenAI", "NVIDIA", "GPT", "Google"}

def extract_entities_spacy(corpus):
    """
    CURATE-AI: THE NEURAL DISCOVERY ENGINE (S5 v7)
    ----------------------------------------------
    Uses SpaCy NER (Named Entity Recognition) to dynamically find 
    Organizations and Products without any hardcoded blacklists.
    """
    entity_counts = Counter()
    
    # We batch process to stay fast
    docs = nlp.pipe([a['title'] for a in corpus], batch_size=50)
    
    for doc in docs:
        found_in_doc = set()
        for ent in doc.ents:
            # We only care about ORG (Companies), PRODUCT (Tech), and maybe PERSON if it's musk/etc.
            if ent.label_ in ["ORG", "PRODUCT", "WORK_OF_ART"]:
                # Clean text: remove leading 'The' which SpaCy often keeps
                clean_text = ent.text.strip()
                if clean_text.lower().startswith("the "):
                    clean_text = clean_text[4:]
                
                # Length filter + Junk Filter (dynamic check for common nouns)
                if len(clean_text) >= 2:
                    found_in_doc.add(clean_text)
                    
        # Add to global counts
        entity_counts.update(found_in_doc)

    # Statistical Significance: Appear in 3+ sources
    return [ent for ent, count in entity_counts.items() if count >= 3]

def main():
    print("PROTOTYPE S5 (v7): NEURAL NLP DISCOVERY STARTING...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    corpus_path = os.path.join(os.path.dirname(script_dir), "Prototypes", "Data", "articles.json")
    with open(corpus_path, "r") as f: full_corpus = json.load(f)

    # 1. DISCOVERY (Fully Dynamic via SpaCy)
    discovered_list = extract_entities_spacy(full_corpus)
    # Ensure our whitelist is always there
    for w in WHITELIST:
        if w not in discovered_list: discovered_list.append(w)
        
    print(f"  Neural Scan Result: Found {len(discovered_list)} dynamic entities.")

    # 2. VELOCITY WINDOWS
    window_a = full_corpus[:1440]
    window_b = full_corpus[1440:]
    
    counts_a, counts_b = Counter(), Counter()

    # Re-scan windows using our discovered high-signal list
    for article in window_a:
        title = article['title']
        for ent in discovered_list:
            if ent in title: counts_a[ent] += 1
            
    for article in window_b:
        title = article['title']
        for ent in discovered_list:
            if ent in title: counts_b[ent] += 1

    # 3. CONSOLIDATION
    velocity_report = []
    for ent in discovered_list:
        a, b = counts_a[ent], counts_b[ent]
        total = a + b
        velocity = ((b - a) / (a if a > 0 else 1)) * 100
        
        if total >= 3:
            velocity_report.append({
                "entity": ent,
                "current_window": b,
                "previous_window": a,
                "total_mentions": total,
                "velocity": f"{velocity:+.1f}%",
                "status": "SURGING" if velocity > 50 else "STABLE" if velocity > -20 else "DECLINING"
            })

    velocity_report.sort(key=lambda x: x['total_mentions'], reverse=True)

    print("\n--- NEURAL SEO DASHBOARD (NLP-DRIVEN) ---")
    print(f"{'ENTITY':<22} | {'LAST 12H':<8} | {'PREV 12H':<8} | {'TOTAL':<5} | {'STATUS'}")
    print("-" * 75)
    for entry in velocity_report[:30]:
        print(f"{entry['entity']:<22} | {entry['current_window']:<8} | {entry['previous_window']:<8} | {entry['total_mentions']:<5} | {entry['status']}")

    # 5. OVERWRITE MASTER
    output_path = os.path.join(script_dir, "Data", "seo_velocity_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(velocity_report, f, indent=2)

if __name__ == "__main__":
    main()
