import feedparser
import json
import pandas as pd
from datetime import datetime
import time
from urllib.parse import urlparse

# Key RSS feeds to test with (AI & Tech focus)
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
    "https://news.ycombinator.com/rss"
]

def normalize_url(url):
    if not url:
        return ""
    parsed = urlparse(url)
    return parsed.netloc + parsed.path

def main():
    print(f"Starting to parse {len(RSS_FEEDS)} RSS feeds...")
    
    all_articles = []
    feed_stats = []

    for feed_url in RSS_FEEDS:
        print(f"Fetching: {feed_url}")
        start_time = time.time()
        
        # Parse the feed
        feed = feedparser.parse(feed_url)
        
        entries_count = len(feed.entries)
        source_name = feed.feed.get("title", urlparse(feed_url).netloc)
        
        fields_presence = {
            "title": 0, "summary": 0, "published_date": 0, 
            "author": 0, "link": 0, "categories": 0
        }
        
        summary_lengths = []
        
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()
            link = entry.get("link", "").strip()
            
            # Author can be in 'author' or 'dc:creator'
            author = entry.get("author", entry.get("dc_creator", ""))
            
            # Published Date
            published_date = entry.get("published", entry.get("updated", ""))
            
            # Categories / tags
            categories = [t.get("term", "") for t in entry.get("tags", [])]
            
            article = {
                "source": source_name,
                "feed_url": feed_url,
                "title": title,
                "summary": summary,
                "published_date": published_date,
                "author": author,
                "link": link,
                "categories": categories,
                "summary_length": len(summary)
            }
            
            # Track field presence
            if title: fields_presence["title"] += 1
            if summary: fields_presence["summary"] += 1
            if published_date: fields_presence["published_date"] += 1
            if author: fields_presence["author"] += 1
            if link: fields_presence["link"] += 1
            if categories: fields_presence["categories"] += 1
                
            summary_lengths.append(len(summary))
            all_articles.append(article)
        
        avg_summary_len = sum(summary_lengths) / len(summary_lengths) if summary_lengths else 0
        
        feed_stats.append({
            "feed_url": feed_url,
            "source_title": source_name,
            "articles_count": entries_count,
            "fields_presence": {k: (v/entries_count if entries_count else 0) for k, v in fields_presence.items()},
            "avg_summary_length": avg_summary_len
        })
        
        time.sleep(0.5) # Gentle request pausing

    # Deduplication
    unique_articles = []
    seen_urls = set()
    seen_titles = set()
    duplicates_count = 0

    for article in all_articles:
        n_url = normalize_url(article["link"])
        title_lower = article["title"].lower()
        
        if n_url in seen_urls or title_lower in seen_titles:
            duplicates_count += 1
        else:
            seen_urls.add(n_url)
            if title_lower:
                seen_titles.add(title_lower)
            # Remove helper column for final JSON/CSV
            art_copy = article.copy()
            del art_copy["summary_length"]
            unique_articles.append(art_copy)

    print("\n" + "="*50)
    print("PROTOTYPE 1: RSS INGESTION STATS")
    print("="*50)
    print(f"Total articles fetched: {len(all_articles)}")
    print(f"Total unique articles: {len(unique_articles)}")
    print(f"Duplicates removed: {duplicates_count}")
    print("\nBreakdown by Source:")
    
    df_stats = pd.DataFrame([{
        "Source": s["source_title"],
        "Count": s["articles_count"],
        "Avg_Summary_Len": round(s["avg_summary_length"]),
        "%_Has_Title": f"{s['fields_presence']['title']*100:.0f}%",
        "%_Has_Summary": f"{s['fields_presence']['summary']*100:.0f}%",
        "%_Has_Date": f"{s['fields_presence']['published_date']*100:.0f}%",
        "%_Has_Author": f"{s['fields_presence']['author']*100:.0f}%",
        "%_Has_Categories": f"{s['fields_presence']['categories']*100:.0f}%"
    } for s in feed_stats])
    
    print(df_stats.to_string(index=False))
    
    # Analyze publication dates parsing
    valid_dates = 0
    for article in unique_articles:
        if article['published_date']:
            # We just count them as present. feedparser attempts standard parsing
            valid_dates += 1
            
    print(f"\nOverall Valid/Present Dates: {valid_dates} out of {len(unique_articles)} unique articles")
    
    overall_avg_summary = sum([a["summary_length"] for a in all_articles]) / len(all_articles) if all_articles else 0
    print(f"Overall Average Summary Length (chars): {overall_avg_summary:.0f}")

    # Save to JSON
    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(unique_articles, f, indent=2, ensure_ascii=False)
        
    # Save to CSV
    df = pd.DataFrame(unique_articles)
    df.to_csv("articles.csv", index=False)
    print(f"\nSaved {len(unique_articles)} articles to articles.json and articles.csv")

if __name__ == "__main__":
    main()
