import json
import os
import time
import pandas as pd
import trafilatura
from urllib.parse import urlparse

def get_stratified_sample(articles, sample_size=50):
    """Get a diverse sample of URLs across different sources."""
    # Group by source
    by_source = {}
    for a in articles:
        src = a.get("source", "Unknown")
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(a)
        
    sampled = []
    # Pick round-robin from each source until we hit sample_size
    sources = list(by_source.keys())
    counts = {s: 0 for s in sources}
    idx = 0
    
    while len(sampled) < sample_size and len(sources) > 0:
        src = sources[idx % len(sources)]
        if counts[src] < len(by_source[src]):
            sampled.append(by_source[src][counts[src]])
            counts[src] += 1
        else:
            sources.remove(src)
            if not sources:
                break
            continue # Don't advance idx so we don't skip
        idx += 1
        
    return sampled

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    articles_path = os.path.join(data_dir, "articles.json")
    
    if not os.path.exists(articles_path):
        print(f"File not found: {articles_path}. Please run Prototype 1 first.")
        return

    with open(articles_path, "r", encoding="utf-8") as f:
        all_articles = json.load(f)

    # Get ~50 diverse articles to test
    test_articles = get_stratified_sample(all_articles, sample_size=50)
    print(f"Testing extraction on {len(test_articles)} articles across {len(set(a['source'] for a in test_articles))} sources...")

    results = []
    extracted_data = []

    for idx, article in enumerate(test_articles):
        url = article['link']
        source = article.get('source', 'Unknown')
        print(f"[{idx+1}/{len(test_articles)}] Fetching: {url} (Source: {source})")
        
        start_time = time.time()
        
        # 1. Fetch the raw HTML
        downloaded = trafilatura.fetch_url(url)
        
        fetch_success = downloaded is not None
        status = "Success"
        extracted_text = None
        char_count = 0
        
        if not fetch_success:
            status = "Fetch Failed (Blocked/404)"
            # Fallback to summary
            extracted_text = article.get('summary', '')
            char_count = len(extracted_text)
        else:
            # 2. Extract the clean text
            extracted_text = trafilatura.extract(
                downloaded, 
                include_comments=False, 
                include_tables=False, 
                no_fallback=False
            )
            
            if extracted_text and len(extracted_text) > 100:
                char_count = len(extracted_text)
                status = "Success"
            else:
                status = "Extraction Failed (Paywall/JS/Empty)"
                # Fallback to summary
                extracted_text = article.get('summary', '')
                char_count = len(extracted_text)
                
        extract_time = time.time() - start_time
        
        results.append({
            "Source": source,
            "URL": url,
            "Status": status,
            "Char_Count": char_count,
            "Extract_Time": round(extract_time, 2),
            "Used_Fallback": status != "Success"
        })
        
        extracted_data.append({
            "URL": url,
            "Text": extracted_text,
            "Status": status
        })
        
        # Be nice
        time.sleep(1)

    print("\n" + "="*50)
    print("EXTRACTION PROTOTYPE STATS")
    print("="*50)
    
    df = pd.DataFrame(results)
    
    success_rate = (len(df[df['Status'] == 'Success']) / len(df)) * 100
    avg_length = df[df['Status'] == 'Success']['Char_Count'].mean()
    avg_time = df['Extract_Time'].mean()
    
    print(f"Overall Success Rate: {success_rate:.1f}%")
    print(f"Average Extract Time: {avg_time:.2f} seconds")
    print(f"Average Article Length (Successful ones): {avg_length:.0f} characters")
    
    print("\nFailures by Source:")
    failures = df[df['Status'] != 'Success']
    if not failures.empty:
        fail_counts = failures.groupby(['Source', 'Status']).size().reset_index(name='Count')
        print(fail_counts.to_string(index=False))
    else:
        print("None! 100% success.")

    # Save reports
    df.to_csv(os.path.join(data_dir, "extraction_report.csv"), index=False)
    with open(os.path.join(data_dir, "extracted_texts.json"), "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nSaved detailed reports to {data_dir}/extraction_report.csv and extracted_texts.json")

if __name__ == "__main__":
    main()
