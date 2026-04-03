import requests
import json
import time
from datetime import datetime
import os

# Target websites that returned True for WP API in our analysis
TARGETS = [
    "https://techcrunch.com",
    "https://venturebeat.com"
]

def fetch_recent_wp_posts(base_url, max_pages=5, per_page=20):
    print(f"\n--- Testing WP API for {base_url} ---")
    api_url = f"{base_url}/wp-json/wp/v2/posts"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    all_posts = []
    
    for page in range(1, max_pages + 1):
        params = {
            "per_page": per_page,
            "page": page,
            "_fields": "id,date,title,link" # Only request what we need to save bandwidth
        }
        
        print(f"Fetching page {page}...")
        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if not data:
                    print("  No more data returned. Reached end of posts.")
                    break
                
                print(f"  Successfully retrieved {len(data)} posts.")
                all_posts.extend(data)
                
                # Check date of the oldest post on this page
                oldest_date_str = data[-1]['date']
                oldest_dt = datetime.fromisoformat(oldest_date_str)
                age_hours = (datetime.utcnow() - oldest_dt).total_seconds() / 3600
                print(f"  Oldest post on this page is {age_hours:.1f} hours old.")
                
            elif response.status_code == 429:
                print(f"  [ERROR] Rate limited on page {page} (HTTP 429)")
                break
            elif response.status_code in [401, 403]:
                print(f"  [ERROR] Access denied / Blocked (HTTP {response.status_code})")
                break
            else:
                print(f"  [ERROR] Failed to fetch page {page}. HTTP {response.status_code}")
                break
                
            time.sleep(2) # Friendly delay between requests to avoid rate limits
            
        except Exception as e:
            print(f"  [ERROR] Request failed: {e}")
            break

    return all_posts

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    os.makedirs(data_dir, exist_ok=True)
    
    results = {}
    
    for target in TARGETS:
        posts = fetch_recent_wp_posts(target, max_pages=5)
        results[target] = len(posts)
        print(f"Total posts retrieved for {target}: {len(posts)}")
        
    # Save a small sample log
    with open(os.path.join(data_dir, "wp_api_test_results.json"), "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
