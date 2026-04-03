import json
import os
import time
import random
import pandas as pd
import trafilatura
from urllib.parse import urlparse

def get_stratified_sample(articles, samples_per_source=3):
    by_source = {}
    for a in articles:
        src = a.get("source", "Unknown")
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(a)
    
    sampled = []
    for src, items in by_source.items():
        # take up to samples_per_source
        sampled.extend(items[:samples_per_source])
    return sampled

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    articles_path = os.path.join(data_dir, "articles.json")
    
    if not os.path.exists(articles_path):
        print(f"File not found: {articles_path}")
        return

    with open(articles_path, "r", encoding="utf-8") as f:
        all_articles = json.load(f)

    # 5-10 articles per source
    test_articles = get_stratified_sample(all_articles, samples_per_source=3)
    print(f"Testing extraction on {len(test_articles)} articles across {len(set(a['source'] for a in test_articles))} sources...")

    raw_results = []

    for idx, article in enumerate(test_articles):
        url = article['link']
        source = article.get('source', 'Unknown')
        print(f"[{idx+1}/{len(test_articles)}] {source}: {url}")
        
        start_time = time.time()
        
        # Adding a fake User-Agent string configuration to Trafilatura to prevent basic blocking
        config = trafilatura.settings.use_config()
        config.set('DEFAULT', 'USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
        
        # 1. Fetch the raw HTML
        downloaded = trafilatura.fetch_url(url, config=config)
        
        status = "Success"
        extracted_text = ""
        fetch_time = time.time() - start_time
        extract_time = 0.0
        char_count = 0
        word_count = 0
        
        if downloaded is None:
            status = "Blocked/404"
        else:
            e_start = time.time()
            extracted_text = trafilatura.extract(downloaded, include_comments=False, config=config)
            extract_time = time.time() - e_start
            
            if extracted_text and len(extracted_text) > 100:
                char_count = len(extracted_text)
                word_count = len(extracted_text.split())
                status = "Success"
            else:
                status = "Paywall/No_Text"
                
        total_time = fetch_time + extract_time
        
        raw_results.append({
            "Source": source,
            "URL": url,
            "Status": status,
            "Char_Count": char_count,
            "Word_Count": word_count,
            "Fetch_Time_Sec": fetch_time,
            "Extract_Time_Sec": extract_time,
            "Total_Time_Sec": total_time
        })
        
        # Sleep randomly between 1.5 to 3.5 seconds to avoid IP bans
        time.sleep(random.uniform(1.5, 3.5))

    df = pd.DataFrame(raw_results)
    
    # Generate aggregated source report
    source_stats = []
    for source, group in df.groupby("Source"):
        total = len(group)
        success_group = group[group["Status"] == "Success"]
        success_count = len(success_group)
        fail_count = total - success_count
        success_rate = round((success_count / total) * 100, 1)
        
        avg_time = round(group["Total_Time_Sec"].mean(), 2)
        avg_words = round(success_group["Word_Count"].mean()) if success_count > 0 else 0
        avg_chars = round(success_group["Char_Count"].mean()) if success_count > 0 else 0
        
        source_stats.append({
            "Source": source,
            "Attempted": total,
            "Success": success_count,
            "Failed": fail_count,
            "Success_%": success_rate,
            "Avg_Latency_Sec": avg_time,
            "Avg_Words": avg_words,
            "Avg_Chars": avg_chars
        })
        
    df_stats = pd.DataFrame(source_stats)
    df_stats.to_csv(os.path.join(data_dir, "extraction_source_report.csv"), index=False)
    df.to_csv(os.path.join(data_dir, "extraction_raw_logs.csv"), index=False)
    
    print("\n" + "="*50)
    print("EXTRACTION PROTOTYPE COMPLETE")
    print("="*50)
    print(f"Saved aggregated report to {data_dir}/extraction_source_report.csv")

if __name__ == "__main__":
    main()
