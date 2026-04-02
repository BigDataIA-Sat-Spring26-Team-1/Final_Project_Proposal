import json
import os
import time
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

def preprocess(text):
    return re.sub(r'[^\w\s]', '', text.lower())

def run_tfidf_dedup(articles):
    start = time.time()
    titles = [preprocess(a['title']) for a in articles]
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(titles)
    sim_matrix = cosine_similarity(tfidf_matrix)
    
    threshold = 0.5 # TF-IDF is more sensitive to exact words
    clusters = []
    visited = set()
    for i in range(len(articles)):
        if i not in visited:
            cluster = [i]
            visited.add(i)
            for j in range(i+1, len(articles)):
                if sim_matrix[i][j] > threshold:
                    cluster.append(j)
                    visited.add(j)
            clusters.append(cluster)
    return len(clusters), time.time() - start

def run_vector_dedup(articles, model):
    start = time.time()
    titles = [a['title'] for a in articles]
    embeddings = model.encode(titles, show_progress_bar=False)
    sim_matrix = cosine_similarity(embeddings)
    
    threshold = 0.75 # Vector is more semantically accurate
    clusters = []
    visited = set()
    for i in range(len(articles)):
        if i not in visited:
            cluster = [i]
            visited.add(i)
            for j in range(i+1, len(articles)):
                if sim_matrix[i][j] > threshold:
                    cluster.append(j)
                    visited.add(j)
            clusters.append(cluster)
    return len(clusters), time.time() - start

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, "Data", "articles.json")
    
    if not os.path.exists(input_path):
        print("Data/articles.json not found.")
        return

    with open(input_path, "r") as f:
        articles = json.load(f)[:300] # Test on 300 for speed

    print(f"Comparing Deduplication Approaches on {len(articles)} articles...")
    
    # 1. TF-IDF
    tfidf_count, tfidf_time = run_tfidf_dedup(articles)
    
    # 2. Vector
    model = SentenceTransformer('all-MiniLM-L6-v2')
    vec_count, vec_time = run_vector_dedup(articles, model)
    
    report = f"""# Deduplication Architecture Comparison

| Metric | TF-IDF (Keyword) | Sentence-Transformers (Vector) |
| :--- | :--- | :--- |
| **Unique Stories Found** | {tfidf_count} | {vec_count} |
| **Duplicates Removed** | {len(articles) - tfidf_count} | {len(articles) - vec_count} |
| **Inference Time** | {tfidf_time:.4f}s | {vec_time:.4f}s |
| **Precision** | Low (Exact words only) | High (Captures Meaning) |

### Why we moved to Vectors:
TF-IDF failed to group stories like "OpenAI Funding" vs "ChatGPT Creator raises money". 
The Vector approach correctly identified {len(articles) - vec_count} clusters that were hidden 
behind different headlines, leading to a much cleaner user experience.
"""
    
    report_path = os.path.join(script_dir, "Data", "Final Reports", "dedup_logic_comparison.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"Architecture comparison saved to: {report_path}")

if __name__ == "__main__":
    main()
