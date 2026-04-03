import json
import os
import time
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, "Data", "articles.json")
    
    with open(input_path, "r") as f:
        raw_articles = json.load(f)

    # 1. URL DEDUP
    url_map = {a['link']: a for a in raw_articles}
    unique_urls = list(url_map.values())
    
    # 2. VECTOR DEDUP (on 1000 samples)
    sample_set = unique_urls[:1000]
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode([a['title'] for a in sample_set], show_progress_bar=False)
    sim_matrix = cosine_similarity(embeddings)
    
    # Simple cluster count
    threshold = 0.7
    visited = set()
    clusters = 0
    for i in range(len(sample_set)):
        if i not in visited:
            clusters += 1
            visited.add(i)
            for j in range(i+1, len(sample_set)):
                if sim_matrix[i][j] > threshold:
                    visited.add(j)

    # CREATE METRIC CSV
    metrics = {
        "Metric": ["Total Ingested", "URL Uniques", "Vector Uniques (1k Sample)", "Reduction Rate (Vector)"],
        "Value": [len(raw_articles), len(unique_urls), clusters, f"{(1000-clusters)/10:.1f}%"]
    }
    
    df = pd.DataFrame(metrics)
    output_path = os.path.join(script_dir, "Data", "Final Reports", "vector_funnel_metrics.csv")
    df.to_csv(output_path, index=False)
    print(f"Vector metrics saved to {output_path}")

if __name__ == "__main__":
    main()
