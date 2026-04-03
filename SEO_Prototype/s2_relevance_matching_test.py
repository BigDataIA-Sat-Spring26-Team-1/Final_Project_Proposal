import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def main():
    print("PROTOTYPE S2: DEEP CORPUS RELEVANCE MATCHING STARTING...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Load the Companies with Vectors (from S1)
    vectors_path = os.path.join(script_dir, "Data", "company_authority_vectors.json")
    with open(vectors_path, "r") as f: companies = json.load(f)

    # 2. Load the ENTIRE Article Corpus (3,000+ items)
    # This is where we find "Under the Radar" gems for SEO
    corpus_path = os.path.join(os.path.dirname(script_dir), "Prototypes", "Data", "articles.json")
    if not os.path.exists(corpus_path):
        print("Master article corpus missing.")
        return
    with open(corpus_path, "r") as f: full_corpus = json.load(f)

    print(f"  Scanning deep corpus of {len(full_corpus)} articles...")

    # 3. Embedding the Full Corpus (only titles for speed in prototype)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # We take the first 1000 for a representative 'Real World' scan
    sample_corpus = full_corpus[:1000] 
    titles = [a['title'] for a in sample_corpus]
    corpus_embeddings = model.encode(titles, show_progress_bar=False)
    
    company_discovery = {}

    for comp in companies:
        c_vector = np.array(comp['authority_vector']).reshape(1, -1)
        sims = cosine_similarity(c_vector, corpus_embeddings)[0]
        
        matches = []
        for i in range(len(sample_corpus)):
            matches.append({
                "title": sample_corpus[i]['title'],
                "relevance_score": float(sims[i]),
                "source": sample_corpus[i].get('source', 'Unknown')
            })
            
        # Sort by best relevance
        matches.sort(key=lambda x: x['relevance_score'], reverse=True)
        company_discovery[comp['name']] = matches

    # 4. REPORT: Top Technical Micro-Opportunities
    # We want to see UNEXPECTED but highly relevant matches
    for name, matches in company_discovery.items():
        print(f"\n--- DISCOVERY FOR: {name} ---")
        # Show top 5 "Opportunities"
        for i, match in enumerate(matches[:5]):
            print(f"  {i+1}. [{match['source']}] {match['title'][:70]}... (Score: {match['relevance_score']:.4f})")

    # 5. SAVE DATA FOR S3 (Opportunity Assessment)
    output_path = os.path.join(script_dir, "Data", "topic_company_matches.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(company_discovery, f, indent=2)

    print(f"\nCOMPLETED: Deep matching saved.")

if __name__ == "__main__":
    main()
