import json
import os
import time
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def vector_dedup_test():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    input_path = os.path.join(data_dir, "pipeline_prototype_output.json")
    
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        articles = json.load(f)
    
    print(f"Loaded {len(articles)} articles. Initializing SentenceTransformer (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # We combine Title + Summary for a richer embedding
    sentences = [f"{a['title']} {a.get('summary', '')}" for a in articles]
    
    print("Generating embeddings...")
    start_time = time.time()
    embeddings = model.encode(sentences, show_progress_bar=True)
    encode_time = time.time() - start_time
    print(f"Embedding generation took {encode_time:.2f} seconds.")
    
    print("Calculating cosine similarity matrix...")
    sim_matrix = cosine_similarity(embeddings)
    
    # Finding clusters with threshold
    threshold = 0.75
    visited = set()
    clusters = []
    
    for i in range(len(articles)):
        if i in visited:
            continue
        
        # Find all indices with similarity > threshold
        similar_indices = np.where(sim_matrix[i] > threshold)[0]
        
        current_cluster = []
        for idx in similar_indices:
            if idx not in visited:
                current_cluster.append(articles[idx])
                visited.add(idx)
        
        if len(current_cluster) > 1:
            clusters.append(current_cluster)
            
    print("\n" + "="*50)
    print("SEMANTIC CLUSTERING (VECTOR) RESULTS")
    print("="*50)
    print(f"Total Clusters Found: {len(clusters)}")
    
    # Show top 10 clusters
    clusters = sorted(clusters, key=lambda x: len(x), reverse=True)
    for i, cluster in enumerate(clusters[:10]):
        print(f"\nCluster {i+1} (Size: {len(cluster)})")
        for a in cluster:
            print(f"  - [{a['source_name']}] {a['title']}")

if __name__ == "__main__":
    vector_dedup_test()
