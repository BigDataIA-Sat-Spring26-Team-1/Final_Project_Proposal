import json
import os
import uuid
import time
from datetime import datetime, timedelta, timezone
import re
from urllib.parse import urlparse
import trafilatura
from dateutil import parser as date_parser
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def normalize_url(url):
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path.rstrip('/')
        return f"{netloc}{path}"
    except:
        return url

def is_recent(date_str, max_hours=48):
    if not date_str:
        return True # Can't prove it's old, so we keep it safely
    try:
        dt = date_parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        age = now - dt
        # If it's older than max_hours, or somehow from a future date >1 hr, drop it
        return timedelta(hours=-1) <= age <= timedelta(hours=max_hours)
    except:
        return True

def load_raw_data(data_dir):
    rss_path = os.path.join(data_dir, "articles.json")
    social_path = os.path.join(data_dir, "social_community_posts.json")
    
    rss_data = []
    social_data = []
    
    if os.path.exists(rss_path):
        with open(rss_path, "r", encoding="utf-8") as f:
            rss_data = json.load(f)
    if os.path.exists(social_path):
        with open(social_path, "r", encoding="utf-8") as f:
            social_data = json.load(f)
            
    return rss_data, social_data

def normalize_to_schema(rss_data, social_data):
    normalized = []
    ingested_at = datetime.now(timezone.utc).isoformat()
    
    for r in rss_data:
        # Skip HN RSS feed
        if 'news.ycombinator.com' in r.get('feed_url', ''):
            continue
            
        pub_date = r.get('published_date', '')
        if not is_recent(pub_date, max_hours=48):
            continue
            
        normalized.append({
            "id": str(uuid.uuid4()),
            "title": r.get('title', ''),
            "summary": r.get('summary', ''),
            "source_name": r.get('source', 'Unknown'),
            "source_type": "rss",
            "source_url": r.get('link', ''),
            "published_at": pub_date,
            "author": r.get('author', ''),
            "raw_categories": r.get('categories', []),
            "content_type": "article",
            "popularity_signal": 0, 
            "cluster_size": 1,
            "full_text": None,
            "ingested_at": ingested_at
        })
        
    for s in social_data:
        pub_date = s.get('Published_At', '')
        if not is_recent(pub_date, max_hours=48):
            continue
            
        platform = s.get('Original_Platform', '').lower()
        if 'reddit' in platform:
            continue
            
        normalized.append({
            "id": str(uuid.uuid4()),
            "title": s.get('Title', ''),
            "summary": "", 
            "source_name": s.get('Source', 'Unknown'),
            "source_type": "hackernews",
            "source_url": s.get('URL', ''),
            "published_at": pub_date,
            "author": "",
            "raw_categories": [],
            "content_type": "hn_story",
            "popularity_signal": s.get('Score', 0),
            "cluster_size": 1,
            "full_text": None,
            "ingested_at": ingested_at
        })
        
    return normalized

def deduplicate_articles(articles, model):
    if not articles:
        return []
        
    # Phase 1: Basic URL Normalization (Exact Match)
    url_clusters = {}
    for article in articles:
        n_url = normalize_url(article["source_url"])
        if not n_url:
            n_url = article["id"] 
        if n_url not in url_clusters:
            url_clusters[n_url] = []
        url_clusters[n_url].append(article)
        
    url_deduped = []
    for n_url, cluster in url_clusters.items():
        cluster = sorted(cluster, key=lambda x: len(x.get('summary', '')), reverse=True)
        canonical = cluster[0].copy()
        
        total_pop = sum([c.get("popularity_signal", 0) for c in cluster])
        canonical["popularity_signal"] = total_pop
        canonical["sources"] = list(set([c.get('source_name') for c in cluster]))
        url_deduped.append(canonical)
        
    # Phase 2: Semantic Vector Clustering (Meaning Match)
    print(f"  Running semantic deduplication on {len(url_deduped)} url-unique items...")
    sentences = [f"{a['title']} {a.get('summary', '')}" for a in url_deduped]
    embeddings = model.encode(sentences, show_progress_bar=False)
    sim_matrix = cosine_similarity(embeddings)
    
    threshold = 0.70 
    visited = set()
    final_deduped = []
    
    for i in range(len(url_deduped)):
        if i in visited:
            continue
            
        similar_indices = np.where(sim_matrix[i] > threshold)[0]
        cluster_items = []
        for idx in similar_indices:
            if idx not in visited:
                cluster_items.append(url_deduped[idx])
                visited.add(idx)
        
        cluster_items = sorted(cluster_items, key=lambda x: (len(x.get('summary', '')), len(x.get('full_text', '') or '')), reverse=True)
        canonical = cluster_items[0].copy()
        
        total_pop = sum([c.get("popularity_signal", 0) for c in cluster_items])
        all_sources = []
        for itm in cluster_items:
            all_sources.extend(itm.get('sources', [itm.get('source_name')]))
            
        canonical["popularity_signal"] = total_pop
        canonical["all_sources"] = list(set(all_sources))
        canonical["cluster_size"] = len(canonical["all_sources"])
        
        final_deduped.append(canonical)
        
    return final_deduped

def extract_full_text(articles, top_k=20):
    half_k = top_k // 2
    sorted_by_cluster = sorted(articles, key=lambda x: x.get("cluster_size", 1), reverse=True)
    sorted_by_popularity = sorted(articles, key=lambda x: x.get("popularity_signal", 0), reverse=True)
    
    selected_articles = []
    seen_ids = set()
    
    for a in sorted_by_cluster:
        if len(selected_articles) >= half_k: break
        if a["id"] not in seen_ids:
            selected_articles.append(a)
            seen_ids.add(a["id"])
            
    for a in sorted_by_popularity:
        if len(selected_articles) >= top_k: break
        if a["id"] not in seen_ids:
            selected_articles.append(a)
            seen_ids.add(a["id"])

    top_articles = selected_articles
    successful_extractions = 0
    config = trafilatura.settings.use_config()
    config.set('DEFAULT', 'USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
    
    print(f"Extracting full text for top {top_k} stories...")
    for idx, article in enumerate(top_articles):
        url = article["source_url"]
        if not url or 'reddit.com' in url or 'news.ycombinator.com' in url:
            continue
            
        print(f"  [{idx+1}/{top_k}] Fetching: {url[:60]}...")
        downloaded = trafilatura.fetch_url(url, config=config)
        if downloaded:
            extracted_text = trafilatura.extract(downloaded, include_comments=False, config=config)
            if extracted_text and len(extracted_text) > 100:
                article["full_text"] = extracted_text
                successful_extractions += 1
    return top_articles, successful_extractions

def main():
    start_time = time.time()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    os.makedirs(data_dir, exist_ok=True)
    
    print("Step 1: Loading raw data...")
    rss_data, social_data = load_raw_data(data_dir)
    total_raw = len(rss_data) + len(social_data)
    
    print("Step 2: Normalizing to unified schema...")
    normalized_articles = normalize_to_schema(rss_data, social_data)
    
    print("Step 3: Deduplicating with Semantic Vectors...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    unique_articles = deduplicate_articles(normalized_articles, model)
    
    print("Step 4: Extracting full text for top 20...")
    final_sorted_articles, extract_success = extract_full_text(unique_articles, top_k=20)
    
    output_path = os.path.join(data_dir, "pipeline_prototype_output.json")
    top_20_path = os.path.join(data_dir, "top_20_articles.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_articles, f, indent=2, ensure_ascii=False)
        
    with open(top_20_path, "w", encoding="utf-8") as f:
        json.dump(final_sorted_articles, f, indent=2, ensure_ascii=False)
        
    runtime = time.time() - start_time
    source_counts = {"rss": 0, "hackernews": 0}
    multi_source_clusters = [a for a in unique_articles if a.get("cluster_size", 1) > 1]
    
    for a in unique_articles:
        source_counts[a["source_type"]] = source_counts.get(a["source_type"], 0) + 1
        
    print("\n" + "="*50)
    print("PIPELINE PROTOTYPE REPORT")
    print("="*50)
    print(f"Total raw ingested: {total_raw}")
    print(f"Total after dedup: {len(unique_articles)}")
    print(f"By source type: RSS: {source_counts['rss']}, HN: {source_counts['hackernews']}")
    print(f"Clusters formed (>1 source): {len(multi_source_clusters)}")
    if multi_source_clusters:
        top_clusters = sorted(multi_source_clusters, key=lambda x: x["cluster_size"], reverse=True)[:5]
        print("  Top clusters:")
        for tc in top_clusters:
            print(f"   - {tc['title'][:60]}... (Sources: {tc['cluster_size']})")
            
    print(f"Full text extracted: {extract_success} / 20 attempted")
    print(f"Pipeline runtime: {runtime:.2f} seconds")

if __name__ == "__main__":
    main()
