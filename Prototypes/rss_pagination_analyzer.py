import feedparser
import json
import pandas as pd
import requests
import time
import math
import os
from datetime import datetime
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
            if first_title and first_title not in initial_titles:
                return True
    except:
        pass
    return False

def main():
    print("Analyzing RSS feeds with enriched metrics...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    os.makedirs(data_dir, exist_ok=True)
    report = []
    now = datetime.utcnow()
    
    for feed_url in RSS_FEEDS:
        print(f"\nAnalyzing: {feed_url}")
        start_t = time.time()
        feed = feedparser.parse(feed_url)
        fetch_time = round(time.time() - start_t, 2)
        
        entries = feed.entries
        source_name = feed.feed.get("title", urlparse(feed_url).netloc)
        
        if not entries:
            print("  -> Empty feed.")
            report.append({
                "Source": source_name, "URL": feed_url, "Status": "Empty",
                "Fetch_Time_Sec": fetch_time, "Total_Items": 0, "Action": "Check manually"
            })
            continue

        valid_dates = []
        titles = set()
        has_full_content = False
        summary_chars, summary_words = [], []
        content_chars, content_words = [], []
        
        for entry in entries:
            titles.add(entry.get("title", "").strip())
            
            # Check for summary
            summ = entry.get("summary", "")
            if summ:
                summary_chars.append(len(summ))
                summary_words.append(len(summ.split()))
                
            # Check for actual full article body (content:encoded usually)
            cont = ""
            if "content" in entry and len(entry.content) > 0:
                cont = entry.content[0].value
                has_full_content = True
                content_chars.append(len(cont))
                content_words.append(len(cont.split()))
            
            try:
                if 'published_parsed' in entry and entry.published_parsed:
                    dt = datetime(*entry.published_parsed[:6])
                    valid_dates.append(dt)
            except:
                pass
                
        avg_summ_chars = round(sum(summary_chars)/len(summary_chars)) if summary_chars else 0
        avg_summ_words = round(sum(summary_words)/len(summary_words)) if summary_words else 0
        avg_cont_chars = round(sum(content_chars)/len(content_chars)) if content_chars else 0
        avg_cont_words = round(sum(content_words)/len(content_words)) if content_words else 0
                
        if not valid_dates:
            report.append({
                "Source": source_name, "URL": feed_url, "Status": "No Dates",
                "Fetch_Time_Sec": fetch_time, "Total_Items": len(entries),
                "Has_Full_Content": has_full_content,
                "Avg_Summary_Words": avg_summ_words, "Avg_Content_Words": avg_cont_words,
                "Oldest_Age_Hrs": "N/A", "Newest_Age_Hrs": "N/A",
                "Action": "Poll minimum every 12 hours"
            })
            continue

        oldest_entry_dt = min(valid_dates)
        newest_entry_dt = max(valid_dates)
        oldest_age = (now - oldest_entry_dt).total_seconds() / 3600.0
        newest_age = (now - newest_entry_dt).total_seconds() / 3600.0
        
        items_count = len(entries)
        caps_daily = oldest_age < 24.0
        
        base_metrics = {
            "Source": source_name, "URL": feed_url,
            "Fetch_Time_Sec": fetch_time, "Total_Items": items_count,
            "Has_Full_Content": has_full_content,
            "Avg_Summary_Words": avg_summ_words, "Avg_Content_Words": avg_cont_words,
            "Oldest_Age_Hrs": round(oldest_age, 1), "Newest_Age_Hrs": round(newest_age, 1)
        }
        
        if not caps_daily:
            report.append({**base_metrics, "Status": "Full day coverage", "Has_WP_API": "N/A", "Has_Pagination": "N/A", "Action": "Poll once per day"})
        else:
            has_wp = check_wp_api(feed_url)
            has_page = check_rss_pagination(feed_url, titles)
            safe_poll = max(1, math.floor(oldest_age * 0.9))
            action = f"Poll every {safe_poll} hours" if not has_wp and not has_page else ("Use WP API" if has_wp else "Use ?paged=")
            report.append({**base_metrics, "Status": "Capped (<24h)", "Has_WP_API": has_wp, "Has_Pagination": has_page, "Action": action})

        time.sleep(1)

    df_report = pd.DataFrame(report)
    df_report.to_csv(os.path.join(data_dir, "feed_analysis_report.csv"), index=False)
    with open(os.path.join(data_dir, "feed_analysis_report.json"), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved to {data_dir}/feed_analysis_report.csv and .json")

if __name__ == "__main__":
    main()
