import os
import json
import feedparser
import spacy
import time
import numpy as np
from collections import Counter
from datetime import datetime
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
from dotenv import load_dotenv

# 1. RSS SOURCES
RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://openai.com/blog/rss.xml",
    "https://news.mit.edu/rss/topic/artificial-intelligence2",
    "http://export.arxiv.org/rss/cs.AI",
    "https://blog.google/technology/ai/rss/",
    "https://huggingface.co/blog/feed.xml",
    "https://venturebeat.com/feed/",
    "https://aws.amazon.com/blogs/machine-learning/feed/",
    "https://developer.nvidia.com/blog/feed"
]

# 2. PERSONA DEFINITIONS (These will be dynamically injected into the Markdown)
USER_PERSONA_INFO = {
    "title": "Principal AI Infrastructure Engineer",
    "interests": "LLM scaling, Vector DB benchmarks, HNSW index optimization, PyTorch production deployment.",
    "raw_string": "Principal AI Infrastructure Engineer focused on LLM scaling, Vector DB benchmarks, and production scaling."
}

COMPANY_INFO = {
    "name": "VectorScale Systems",
    "expertise": "Enterprise-grade vector databases and RAG (Retrieval-Augmented Generation) infrastructure.",
    "authority_zones": "Vector indexing, GPU acceleration for search, hybrid-search architectures."
}

try:
    nlp = spacy.load("en_core_web_sm")
except:
    nlp = None

def main():
    load_dotenv()
    client = OpenAI()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] --- CURATE-AI: FULL PERSONA-SYNCED DEMO ---")
    start_time = time.time()
    
    # --- STAGE 1: INGESTION ---
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Step 1/6: Fetching live entries...")
    raw_articles = []
    for f_url in RSS_FEEDS:
        f = feedparser.parse(f_url)
        s_name = f.feed.get('title', 'Source')
        for e in f.entries[:20]: 
            raw_articles.append({"title": e.title, "link": e.link, "summary": e.get('summary', ''), "source": s_name})
    
    # --- STAGE 2: DEDUPLICATION ---
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode([a['title'] for a in raw_articles], show_progress_bar=False)
    sim_matrix = cosine_similarity(embeddings)
    unique_articles = []
    discarded = set()
    for i in range(len(raw_articles)):
        if i in discarded: continue
        unique_articles.append(raw_articles[i])
        for idx in np.where(sim_matrix[i] > 0.85)[0]:
            if idx > i: discarded.add(idx)

    # --- STAGE 3: TREND VELOCITY ---
    mid = len(unique_articles) // 2
    w_a, w_b = unique_articles[:mid], unique_articles[mid:]
    def scan(docs):
        c = Counter()
        if not nlp: return c
        for d in nlp.pipe([a['title'] + " " + a['summary'][:200] for a in docs]):
            for e in d.ents:
                if e.label_ in ["ORG", "PRODUCT"] and len(e.text) > 2: c[e.text] += 1
        return c
    e_a, e_b = scan(w_a), scan(w_b)
    final_trends = []
    for ent in set(e_a.keys()) | set(e_b.keys()):
        a, b = e_a[ent], e_b[ent]
        vel = ((a - b) / (b if b > 0 else 1)) * 100
        if (a+b) >= 2: final_trends.append({"e": ent, "t": a+b, "v": vel})
    final_trends.sort(key=lambda x: x['v'], reverse=True)

    # --- STAGE 4: PERSONALIZATION ---
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Step 4/6: Neural Scoring for '{USER_PERSONA_INFO['title']}'...")
    p_vec = model.encode([USER_PERSONA_INFO['raw_string']])[0]
    u_vecs = model.encode([a['title'] for a in unique_articles])
    scores = cosine_similarity([p_vec], u_vecs)[0]
    for i, a in enumerate(unique_articles): a['score'] = float(scores[i])
    unique_articles.sort(key=lambda x: x['score'], reverse=True)

    # --- STAGE 5: B2B AGENTIC BRIEF ---
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Step 5/6: Generating SEO Strategy for {COMPANY_INFO['name']}...")
    try:
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": f"SEO brief for '{unique_articles[0]['title']}' specifically tailored for {COMPANY_INFO['name']} which does {COMPANY_INFO['expertise']}. 3 paragraphs."}])
        brief = res.choices[0].message.content
    except: brief = "LLM Generation failed."

    # --- STAGE 6: DYNAMIC MARKDOWN REPORT ---
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Step 6/6: Consolidating Final Markdown (Dynamic Personas)...")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = f"""# 🏆 CurateAI: TARGETED PRODUCTION DEMO
**Execution Time:** {now_str}
**Total Batch Size:** {len(unique_articles)} Unique Articles

---

## 👤 1. B2C PERSONALIZED NEWSLETTER (Neural Matching)
### **Target User Persona:**
> **Job Title:** {USER_PERSONA_INFO['title']}
> **Interests:** {USER_PERSONA_INFO['interests']}

### **Personalized Top 10 Feed (Highest Relevant First):**
"""
    for i, a in enumerate(unique_articles[:10]):
        md += f"{i+1}. **{a['title']}**\n   *Match Score: {a['score']*100:.1f}% | Source: {a['source']}*\n"

    md += f"""
---

## 💼 2. B2B ENTERPRISE SEO STRATEGY (Neural Authority)
### **Target Company Profile:**
> **Company Name:** {COMPANY_INFO['name']}
> **Core Expertise:** {COMPANY_INFO['expertise']}
> **Authority Zones:** {COMPANY_INFO['authority_zones']}

### **Strategic SEO Opportunity Brief:**
> **Target News Source:** *"{unique_articles[0]['title']}"*

{brief}

---

## 📈 3. NEURAL DASHBOARD SIGNAL (% VELOCITY)
| Technical Entity | Mentions | Day-over-Day Velocity | Status |
|:---|:---:|:---:|:---|
"""
    for t in final_trends[:15]:
        status = "🔥 SURGING" if t['v'] > 40 else "📉 DECLINING" if t['v'] < -20 else "✅ STABLE"
        md += f"| {t['e']} | {t['t']} | {t['v']:+7.1f}% | {status} |\n"

    md += f"""
---
**VERIFICATION LOG:**
*   Pipeline Efficiency: {((len(raw_articles)-len(unique_articles))/len(raw_articles))*100:.1f}% unique data surfacing.
*   Matching Model: `all-MiniLM-L6-v2` (High-Dimensional Semantic Search).
*   Discovery Engine: SpaCy Neural NER + Agentic Strategy Layer.
*   Execution Latency: {time.time() - start_time:.2f}s
"""
    
    path = "/Users/aakashbelide/Aakash/Higher Studies/Course/Sem-4/DAMG 7245/Final_Project/Final_Project_Proposal/CurateAI_MASTER_DEMO_REPORT.md"
    with open(path, "w", encoding="utf-8") as f: f.write(md)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] COMPLETED: Master Demo Report ready for presentation.")

if __name__ == "__main__":
    main()
