import feedparser
import json
import pandas as pd
import requests
import time
import math
import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse
import warnings
warnings.filterwarnings('ignore')

RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://www.wired.com/feed/rss",
    "https://venturebeat.com/feed/",
    "https://feeds.feedburner.com/TechCrunch/",
    "https://news.mit.edu/rss/topic/artificial-intelligence2",
    "https://blog.google/technology/ai/rss/",
    "https://openai.com/blog/rss.xml",
    "https://www.deepmind.com/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://lilianweng.github.io/index.xml",
    "https://www.technologyreview.com/feed/",
    "https://spectrum.ieee.org/feeds/feed.rss",
    "https://simonwillison.net/atom/everything",
    "https://www.nature.com/subjects/artificial-intelligence.rss",
    "http://export.arxiv.org/rss/cs.AI",
    "http://export.arxiv.org/rss/cs.LG",
    "https://news.ycombinator.com/rss",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://aws.amazon.com/blogs/machine-learning/feed/",
    "https://hackernoon.com/tagged/ai/feed",
    "https://feeds.bloomberg.com/technology/news.rss",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://medium.com/feed/artificialis",
    "http://feeds.feedburner.com/blogspot/gJZg",
    "https://developer.nvidia.com/blog/feed",
    "https://www.microsoft.com/en-us/research/feed/"
]

def check_wp_api(url):
    """Check if the site has a WordPress JSON API."""
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    wp_api_url = f"{base_url}/wp-json/wp/v2/posts?per_page=1"
    try:
        req = requests.get(wp_api_url, timeout=5)
        if req.status_code == 200 and isinstance(req.json(), list):
            return True
    except:
        pass
    return False

def check_rss_pagination(url, initial_titles):
    """Check if the feed supports pagination via ?paged=2."""
    parsed = urlparse(url)
    query_params = dict(parse_qsl(parsed.query))
    query_params['paged'] = '2'
    new_query = urlencode(query_params)
    parsed_updated = parsed._replace(query=new_query)
    paged_url = urlunparse(parsed_updated)
    
    try:
        feed = feedparser.parse(paged_url)
        if len(feed.entries) > 0:
            first_title = feed.entries[0].get("title", "").strip()
            # If the first title of page 2 isn't in page 1's titles
            if first_title and first_title not in initial_titles:
                return True
    except:
        pass
    return False

def main():
    print("Analyzing RSS feeds for capacity limitations and alternatives...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    os.makedirs(data_dir, exist_ok=True)
    
    report = []
    
    now = datetime.utcnow()
    
    for feed_url in RSS_FEEDS:
        print(f"\nAnalyzing: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        entries = feed.entries
        source_name = feed.feed.get("title", urlparse(feed_url).netloc)
        
        if not entries:
            print("  -> Empty feed.")
            report.append({
                "Source": source_name,
                "URL": feed_url,
                "Status": "Broken / Empty",
                "Action": "Check manually"
            })
            continue

        valid_dates = []
        titles = set()
        
        for entry in entries:
            titles.add(entry.get("title", "").strip())
            # Parse date safely
            try:
                if 'published_parsed' in entry and entry.published_parsed:
                    dt = datetime(*entry.published_parsed[:6])
                    valid_dates.append(dt)
            except:
                pass
                
        if not valid_dates:
            report.append({
                "Source": source_name,
                "URL": feed_url,
                "Status": "No Dates",
                "Action": "Poll minimum every 12 hours (fallback)"
            })
            continue

        # Find the oldest entry in the current payload
        oldest_entry_dt = min(valid_dates)
        age_in_hours = (now - oldest_entry_dt).total_seconds() / 3600.0
        items_count = len(entries)
        
        print(f"  -> Oldest item is {age_in_hours:.1f} hours old. Total items: {items_count}")
        
        # Check if the feed provides less than 24 hours of content
        caps_daily_output = age_in_hours < 24.0
        
        if not caps_daily_output:
            print("  -> Provides > 24 hours. Safe for daily polling.")
            report.append({
                "Source": source_name,
                "URL": feed_url,
                "Status": "Full day coverage",
                "Has_WP_API": "N/A",
                "Has_Pagination": "N/A",
                "Action": "Poll once per day"
            })
        else:
            print("  -> Feed caps before 24 hours. Checking alternatives...")
            has_wp = check_wp_api(feed_url)
            has_page = check_rss_pagination(feed_url, titles)
            
            # Polling frequency strategy
            # If the oldest item is X hours old, we must poll at least every X hours. Let's round down slightly for safety.
            safe_poll_interval = max(1, math.floor(age_in_hours * 0.9))
            
            action = f"Requires polling every {safe_poll_interval} hours via Airflow"
            if has_wp:
                action = "Use native WordPress API for historical backfill"
            elif has_page:
                action = "Use ?paged= pagination for historical backfill"
                
            report.append({
                "Source": source_name,
                "URL": feed_url,
                "Status": "Capped (< 24hr loop)",
                "Has_WP_API": has_wp,
                "Has_Pagination": has_page,
                "Action": action
            })

        time.sleep(1) # Gentle throttling

    # Save outputs
    print("\n" + "="*50)
    print("FEED CAP & PAGINATION ANALYSIS REPORT")
    print("="*50)
    
    df_report = pd.DataFrame(report)
    print(df_report.to_string(index=False))
    
    json_path = os.path.join(data_dir, "feed_analysis_report.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    csv_path = os.path.join(data_dir, "feed_analysis_report.csv")
    df_report.to_csv(csv_path, index=False)
    
    print(f"\nReport saved to {data_dir}/feed_analysis_report.csv and .json")

if __name__ == "__main__":
    main()
