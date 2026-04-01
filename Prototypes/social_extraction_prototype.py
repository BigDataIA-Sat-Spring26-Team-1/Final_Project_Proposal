import json
import os
import time
import random
import pandas as pd
import trafilatura

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    social_path = os.path.join(data_dir, "social_community_posts.json")
    
    if not os.path.exists(social_path):
        print(f"File not found: {social_path}. Please run Prototype 3 first.")
        return

    with open(social_path, "r", encoding="utf-8") as f:
        all_posts = json.load(f)

    # Filter for posts that are actual external links (exclude self-posts and reddit comment threads)
    link_posts = [p for p in all_posts if p.get("Is_Link_Post", False) and "reddit.com" not in p.get("URL", "")]
    
    # We'll test a random sample of 30 external articles found on HN and Reddit
    sample_size = min(30, len(link_posts))
    test_articles = random.sample(link_posts, sample_size)
    
    print(f"Testing Trafilatura extraction on {len(test_articles)} external links discovered via Reddit & HN...")

    raw_results = []

    for idx, article in enumerate(test_articles):
        url = article['URL']
        source = article.get('Source', 'Unknown')
        print(f"[{idx+1}/{len(test_articles)}] Found on {source}: {url[:60]}...")
        
        start_time = time.time()
        
        config = trafilatura.settings.use_config()
        config.set('DEFAULT', 'USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 1. Fetch raw HTML
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
                status = "Paywall/No_Text/JS"
                
        total_time = fetch_time + extract_time
        
        raw_results.append({
            "Found_On": source,
            "Target_URL": url,
            "Status": status,
            "Char_Count": char_count,
            "Word_Count": word_count,
            "Fetch_Time_Sec": round(fetch_time, 2),
            "Extract_Time_Sec": round(extract_time, 2),
            "Total_Time_Sec": round(total_time, 2)
        })
        
        # Friendly delay
        time.sleep(random.uniform(1.5, 3.0))

    df = pd.DataFrame(raw_results)
    
    print("\n" + "="*50)
    print("SOCIAL LINK EXTRACTION PROTOTYPE COMPLETE")
    print("="*50)
    
    success_rate = (len(df[df['Status'] == 'Success']) / len(df)) * 100
    avg_length = df[df['Status'] == 'Success']['Char_Count'].mean()
    avg_time = df['Total_Time_Sec'].mean()
    
    print(f"Overall Success Rate: {success_rate:.1f}%")
    print(f"Average Extract Time: {avg_time:.2f} seconds")
    print(f"Average Article Length (Successful ones): {avg_length:.0f} characters\n")
    
    # Generate summary report grouped by the social platform where it was found
    source_stats = []
    for source, group in df.groupby("Found_On"):
        total = len(group)
        success_group = group[group["Status"] == "Success"]
        success_count = len(success_group)
        fail_count = total - success_count
        sr = round((success_count / total) * 100, 1)
        
        source_stats.append({
            "Source": source,
            "Attempted_Links": total,
            "Successful_Extractions": success_count,
            "Failed": fail_count,
            "Success_%": sr
        })
        
    df_stats = pd.DataFrame(source_stats)
    print(df_stats.to_string(index=False))
    
    df.to_csv(os.path.join(data_dir, "social_extraction_raw_logs.csv"), index=False)
    df_stats.to_csv(os.path.join(data_dir, "social_extraction_summary.csv"), index=False)
    
    print(f"\nSaved raw logs and summary to {data_dir}/social_extraction_*.csv")

if __name__ == "__main__":
    main()
