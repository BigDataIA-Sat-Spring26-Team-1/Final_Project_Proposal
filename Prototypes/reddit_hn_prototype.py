import requests
import json
import time
import os
import pandas as pd
from datetime import datetime

def fetch_reddit_posts(subreddits, limit=50):
    print(f"Fetching top {limit} daily posts from Reddit subreddits...")
    headers = {
        "User-Agent": "CurateAI_Prototype/1.0 (Contact: academic_project@university.edu)"
    }
    
    posts = []
    stats = []
    now = datetime.utcnow()
    
    for sub in subreddits:
        source_name = f"Reddit (r/{sub})"
        print(f"  -> {source_name}...")
        url = f"https://www.reddit.com/r/{sub}/top.json?limit={limit}&t=day"
        
        start_t = time.time()
        success = False
        fetched_count = 0
        dates = []
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            latency = time.time() - start_t
            
            if resp.status_code == 200:
                data = resp.json()
                children = data.get("data", {}).get("children", [])
                fetched_count = len(children)
                success = True
                
                for child in children:
                    post_data = child["data"]
                    pub_dt = datetime.utcfromtimestamp(post_data.get("created_utc", 0))
                    dates.append(pub_dt)
                    
                    posts.append({
                        "Source": source_name,
                        "Original_Platform": "Reddit",
                        "Title": post_data.get("title", ""),
                        "URL": post_data.get("url", ""),
                        "SelfText_Length_Chars": len(post_data.get("selftext", "")),
                        "Score": post_data.get("score", 0),
                        "Comments": post_data.get("num_comments", 0),
                        "Published_At": pub_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        "Is_Link_Post": not post_data.get("is_self", True)
                    })
            else:
                latency = time.time() - start_t
                print(f"     [!] Failed with HTTP {resp.status_code}")
        except Exception as e:
            latency = time.time() - start_t
            print(f"     [!] Request error: {e}")
            
        oldest = (now - min(dates)).total_seconds() / 3600.0 if dates else "N/A"
        newest = (now - max(dates)).total_seconds() / 3600.0 if dates else "N/A"
            
        stats.append({
            "Source": source_name,
            "Attempted": limit,
            "Success_Count": fetched_count,
            "Failed_Count": limit - fetched_count if success else limit,
            "Success_Rate_%": round((fetched_count/limit)*100, 1) if limit else 0,
            "API_Latency_Sec": round(latency, 2),
            "Oldest_Age_Hrs": round(oldest, 1) if isinstance(oldest, float) else oldest,
            "Newest_Age_Hrs": round(newest, 1) if isinstance(newest, float) else newest
        })
            
        time.sleep(2)
        
    return posts, stats

def fetch_hn_stories(limit=100):
    print(f"\nFetching top {limit} stories from Hacker News via Firebase API...")
    posts = []
    stats = []
    now = datetime.utcnow()
    
    top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    start_t = time.time()
    
    success_count = 0
    fail_count = 0
    dates = []
    
    try:
        resp = requests.get(top_url, timeout=10)
        top_latency = time.time() - start_t
        
        if resp.status_code == 200:
            story_ids = resp.json()[:limit]
            print(f"  -> Found {len(story_ids)} IDs. Fetching details concurrently...")
            
            for idx, sid in enumerate(story_ids):
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{sid}.json"
                try:
                    item_resp = requests.get(item_url, timeout=5)
                    if item_resp.status_code == 200:
                        item_data = item_resp.json()
                        if item_data and item_data.get('type') == 'story':
                            success_count += 1
                            pub_dt = datetime.utcfromtimestamp(item_data.get("time", 0))
                            dates.append(pub_dt)
                            
                            posts.append({
                                "Source": "Hacker News",
                                "Original_Platform": "Hacker News",
                                "Title": item_data.get("title", ""),
                                "URL": item_data.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                                "SelfText_Length_Chars": len(item_data.get("text", "")),
                                "Score": item_data.get("score", 0),
                                "Comments": item_data.get("descendants", 0),
                                "Published_At": pub_dt.strftime('%Y-%m-%d %H:%M:%S'),
                                "Is_Link_Post": "url" in item_data
                            })
                        else:
                            fail_count += 1
                    else:
                        fail_count += 1
                except:
                    fail_count += 1
                    
        total_latency = time.time() - start_t
        
        oldest = (now - min(dates)).total_seconds() / 3600.0 if dates else "N/A"
        newest = (now - max(dates)).total_seconds() / 3600.0 if dates else "N/A"
        
        stats.append({
            "Source": "Hacker News",
            "Attempted": limit,
            "Success_Count": success_count,
            "Failed_Count": fail_count,
            "Success_Rate_%": round((success_count/limit)*100, 1) if limit else 0,
            "API_Latency_Sec": round(total_latency, 2), # Note: this is sequential latency for all 100 items
            "Oldest_Age_Hrs": round(oldest, 1) if isinstance(oldest, float) else oldest,
            "Newest_Age_Hrs": round(newest, 1) if isinstance(newest, float) else newest
        })
        
    except Exception as e:
        print(f"  [!] HN request error: {e}")
        
    return posts, stats

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    os.makedirs(data_dir, exist_ok=True)
    
    reddit_posts, reddit_stats = fetch_reddit_posts(["MachineLearning", "artificial", "technology", "LocalLLaMA", "programming"], limit=50)
    hn_posts, hn_stats = fetch_hn_stories(limit=100)
    
    all_posts = reddit_posts + hn_posts
    all_stats = reddit_stats + hn_stats
    
    df_posts = pd.DataFrame(all_posts)
    df_stats = pd.DataFrame(all_stats)
    
    # Enrich stats with engagement averages
    eng_stats = df_posts.groupby("Source")[["Score", "Comments", "SelfText_Length_Chars"]].mean().round(1).reset_index()
    eng_stats.rename(columns={"Score": "Avg_Score", "Comments": "Avg_Comments", "SelfText_Length_Chars": "Avg_Text_Chars"}, inplace=True)
    
    link_counts = df_posts.groupby("Source")["Is_Link_Post"].mean().round(2).reset_index()
    link_counts.rename(columns={"Is_Link_Post": "Link_Ratio"}, inplace=True)
    
    df_final_stats = pd.merge(df_stats, eng_stats, on="Source", how="left")
    df_final_stats = pd.merge(df_final_stats, link_counts, on="Source", how="left")
    
    print("\n" + "="*50)
    print("COMMUNITY/SOCIAL SOURCE REPORT")
    print("="*50)
    print(df_final_stats.to_string(index=False))
    
    # Save outputs
    with open(os.path.join(data_dir, "social_community_posts.json"), "w") as f:
        json.dump(all_posts, f, indent=2)
    df_posts.to_csv(os.path.join(data_dir, "social_community_posts.csv"), index=False)
    
    with open(os.path.join(data_dir, "social_source_report.json"), "w") as f:
        json.dump(df_final_stats.to_dict(orient="records"), f, indent=2)
    df_final_stats.to_csv(os.path.join(data_dir, "social_source_report.csv"), index=False)
    
    print(f"\nSaved detailed reports to {data_dir}/social_source_report.csv and .json")

if __name__ == "__main__":
    main()
