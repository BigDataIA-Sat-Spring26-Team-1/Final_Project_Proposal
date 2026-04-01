import json
import os
import re
from urllib.parse import urlparse, urlunparse
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def normalize_url(url):
    """Normalize a URL for exact deduplication."""
    if not url:
        return ""
    try:
        # 1. Parse URL
        parsed = urlparse(url)
        # 2. Lowercase netloc and strip www.
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        # 3. Strip trailing slashes from path
        path = parsed.path.rstrip('/')
        # 4. Strip tracking parameters (utm_*, etc.) from query or just keep path
        # For simplicity in exact URL dedup across news sites, we usually just compare netloc + path.
        # Many news sites use query params for legit routing (like id=123), so we'll just sort the query.
        norm_url = f"{netloc}{path}"
        return norm_url
    except:
        return url

def get_similarity_clusters(articles, similarity_threshold=0.65):
    """
    Groups articles into clusters based on title similarity using TF-IDF.
    Returns a list of clusters, where each cluster is a list of article dicts.
    Note: Threshold of 0.65 for TF-IDF is often good for exact same news events using different wording.
    """
    if not articles:
        return []

    # Clean titles (lowercase, remove punctuation)
    titles = [re.sub(r'[^\w\s]', '', a.get("Title", a.get("title", "")).lower()) for a in articles]
    
    # Compute TF-IDF matrix
    vectorizer = TfidfVectorizer(stop_words='english')
    try:
        tfidf_matrix = vectorizer.fit_transform(titles)
        cosine_sim = cosine_similarity(tfidf_matrix)
    except ValueError:
        # Happens if vocab is empty
        return [[a] for a in articles]

    clusters = []
    assigned = set()
    
    for i in range(len(articles)):
        if i in assigned:
            continue
            
        # Start a new cluster
        current_cluster = [articles[i]]
        assigned.add(i)
        
        # Find all unassigned articles matching this one above threshold
        for j in range(i + 1, len(articles)):
            if j not in assigned and cosine_sim[i][j] >= similarity_threshold:
                current_cluster.append(articles[j])
                assigned.add(j)
                
        clusters.append(current_cluster)
        
    return clusters

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    
    rss_path = os.path.join(data_dir, "articles.json")
    social_path = os.path.join(data_dir, "social_community_posts.json")
    
    if not os.path.exists(rss_path) or not os.path.exists(social_path):
        print("Required JSON files missing in Data/. Run previous prototypes first.")
        return

    # Load data
    with open(rss_path, "r", encoding="utf-8") as f:
        rss_articles = json.load(f)
    with open(social_path, "r", encoding="utf-8") as f:
        social_posts = json.load(f)

    # Standardize dictionary keys for the merge
    standardized_all = []
    
    for r in rss_articles:
        standardized_all.append({
            "Title": r.get('title', ''),
            "Normalized_URL": normalize_url(r.get('link', '')),
            "Original_URL": r.get('link', ''),
            "Source": r.get('source', 'Unknown RSS'),
            "Type": "RSS",
            "Published": r.get('published_date', '')
        })
        
    for s in social_posts:
        # Ignore Reddit text-discussions that have no external URL (since they can't natively match an RSS article URL)
        if s.get("Is_Link_Post", False):
            standardized_all.append({
                "Title": s.get('Title', ''),
                "Normalized_URL": normalize_url(s.get('URL', '')),
                "Original_URL": s.get('URL', ''),
                "Source": s.get('Source', 'Unknown Social'),
                "Type": f"Social ({s.get('Original_Platform', '')})",
                "Published": s.get('Published_At', ''),
                "Score": s.get('Score', 0)
            })

    total_combined = len(standardized_all)
    print(f"Total entries to deduplicate: {total_combined} ({len(rss_articles)} RSS, {len([s for s in social_posts if s.get('Is_Link_Post')])} Social Links)")

    # Method 1: URL-Based Deduplication (Exact canonical match)
    url_clusters = {}
    for article in standardized_all:
        n_url = article["Normalized_URL"]
        if n_url not in url_clusters:
            url_clusters[n_url] = []
        url_clusters[n_url].append(article)
        
    url_deduped_articles = []
    
    # Resolve URL clusters (We keep one canonical 'parent' article, and append 'mentioned_in' sources)
    for n_url, cluster in url_clusters.items():
        canonical = cluster[0].copy()
        canonical["All_Sources"] = list(set([c["Source"] for c in cluster]))
        canonical["Source_Count"] = len(canonical["All_Sources"])
        url_deduped_articles.append(canonical)

    url_unique_count = len(url_deduped_articles)
    print(f"After Phase 1 (URL Exact Match): {url_unique_count} distinct stories left (Reduced by {total_combined - url_unique_count}).")

    # Method 2: Title-Based Similarity Deduplication on the remaining articles
    # This catches instances where Arstechnica and Verge both write "Apple launches new iPhone" but have DIFFERENT URLs.
    print("\nRunning Phase 2 (TF-IDF Title Similarity clustering > 0.65)...")
    final_clusters = get_similarity_clusters(url_deduped_articles, similarity_threshold=0.65)
    
    final_stories = []
    trending_stories = []
    
    for cluster in final_clusters:
        # Combine the "All_Sources" from every URL that was grouped into this semantic cluster
        merged_sources = set()
        for item in cluster:
            merged_sources.update(item["All_Sources"])
            
        merged_sources = list(merged_sources)
        canonical = cluster[0].copy()
        canonical["All_Sources"] = merged_sources
        canonical["Source_Count"] = len(merged_sources)
        
        # If a story cluster has sources from 2 or more distinct platforms/publications, it is "Trending" (Reduced to 2 for prototype scale)
        if canonical["Source_Count"] >= 2:
            canonical["Trending_Flag"] = True
            trending_stories.append(canonical)
        else:
            canonical["Trending_Flag"] = False
            
        # Optional: We could store alternative titles from the cluster, but we'll stick to canonical index 0
        final_stories.append(canonical)

    print(f"After Phase 2 (Semantic Titles): {len(final_stories)} distinct stories left (Reduced by {url_unique_count - len(final_stories)}).")

    # Output stats
    print("==================================================")
    print("DEDUPLICATION & TRENDING PROTOTYPE COMPLETE")
    print("==================================================")
    print(f"Trending Stories Identified (Covered by 2+ original sources): {len(trending_stories)}")

    if trending_stories:
        print("\nTOP TRENDING EXAMPLES FOUND:")
        # Sort by source count descending
        trending_stories = sorted(trending_stories, key=lambda x: x["Source_Count"], reverse=True)
        for i, t in enumerate(trending_stories[:5]):
            print(f"\n[{i+1}] {t['Title']}")
            print(f"    Listed on {t['Source_Count']} sources: {', '.join(t['All_Sources'])}")
            if t.get('Score'):
                print(f"    Social Score: {t['Score']}")

    # -------------------------------------------------------------
    # Generate the Funnel Metrics Report automatically
    # -------------------------------------------------------------
    total_raw_ingested = len(rss_articles) + len(social_posts)
    target_validation_count = total_combined # Only ones with valid Links
    url_pass_count = url_unique_count
    semantic_pass_count = len(final_stories)
    
    funnel_report = [
        {"Stage_Name": "1. Total Ingested (Raw)", "Article_Count": total_raw_ingested, "Description": f"Combined payload of {len(rss_articles)} RSS articles and {len(social_posts)} Social Network posts."},
        {"Stage_Name": "2. Target Validation", "Article_Count": target_validation_count, "Description": f"Excluded {total_raw_ingested - target_validation_count} purely text-based (non-link) Reddit discussions."},
        {"Stage_Name": "3. Exact URL Match Pass", "Article_Count": url_pass_count, "Description": f"Removed {target_validation_count - url_pass_count} explicitly duplicated URLs."},
        {"Stage_Name": "4. Semantic (TF-IDF) Pass", "Article_Count": semantic_pass_count, "Description": f"Removed {url_pass_count - semantic_pass_count} semantic duplicates using Cosine Similarity > 0.65 on Titles."},
        {"Stage_Name": "5. Final Pipeline Yield", "Article_Count": semantic_pass_count, "Description": "The completely unique, mathematically deduplicated corpus of stories that will be passed to the LangGraph agents."}
    ]
    
    df_funnel = pd.DataFrame(funnel_report)

    # Save to disk
    df_all = pd.DataFrame(final_stories)
    df_all.to_csv(os.path.join(data_dir, "deduplicated_stories.csv"), index=False)
    
    with open(os.path.join(data_dir, "deduplicated_stories.json"), "w", encoding="utf-8") as f:
        json.dump(final_stories, f, indent=2, ensure_ascii=False)
        
    df_trend = pd.DataFrame(trending_stories)
    df_trend.to_csv(os.path.join(data_dir, "trending_stories.csv"), index=False)
    
    # Save Funnel Metrics
    df_funnel.to_csv(os.path.join(data_dir, "dedup_funnel_metrics.csv"), index=False)
    with open(os.path.join(data_dir, "dedup_funnel_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(funnel_report, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(final_stories)} totally deduplicated stories to {data_dir}/deduplicated_stories.csv")
    print(f"Saved {len(trending_stories)} Trending hot-topics to {data_dir}/trending_stories.csv")
    print(f"Saved Funnel Metrics tabular report to {data_dir}/dedup_funnel_metrics.csv")

if __name__ == "__main__":
    main()
