import json
import os
from typing import List, Optional
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# 1. Define the Content Strategy Model
class ContentBrief(BaseModel):
    angle: str
    suggested_titles: List[str]
    suggested_structure: List[str]
    seo_keywords: List[str]
    community_questions: List[str]
    internal_linking_strategy: str

class ContentStrategyReport(BaseModel):
    company_name: str
    primary_topic: str
    opportunity_score: float
    brief: ContentBrief

def generate_seo_brief(company_name, company_expertise, topic_title, topic_summary, community_data, client: OpenAI) -> ContentBrief:
    """
    CURATE-AI: THE CONTENT STRATEGIST AGENT (S4)
    -------------------------------------------
    This agent takes a 'Blue Ocean' opportunity and builds a technical content brief.
    """
    
    prompt = f"""
    You are an expert SEO Content Strategist for a high-end tech firm.
    
    COMPANY PROFILE:
    Name: {company_name}
    Expertise: {company_expertise}
    
    TARGET TOPIC OPPORTUNITY:
    Topic: {topic_title}
    Initial Summary: {topic_summary}
    
    COMMUNITY CONTEXT (Signals from Reddit/HN):
    {community_data}
    
    GOAL: Generate a Content Brief that differentiates the company from generic news.
    
    STRATEGY RULES:
    1. Angle: How should this company's unique engineering team approach this?
    2. Structures: Outline the technical explanation or tutorial flow.
    3. Community: Include specific questions from Reddit/HN to answer in the post.
    4. Keywords: Suggest high-intent SEO keywords.
    """
    
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a professional SEO strategist for B2B tech."},
                      {"role": "user", "content": prompt}],
            response_format=ContentBrief
        )
        return response.choices[0].message.parsed
    except Exception as e:
        print(f"API Error: {e}")
        return None

def main():
    load_dotenv()
    client = OpenAI()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    scorecards_path = os.path.join(script_dir, "Data", "opportunity_scorecards.json")
    
    if not os.path.exists(scorecards_path):
        print("Run Prototype S3 first.")
        return
        
    with open(scorecards_path, "r") as f: scorecards = json.load(f)

    # We also need the original company profiles for the descriptions
    vectors_path = os.path.join(script_dir, "Data", "company_authority_vectors.json")
    # Simulation of retrieval based on s1.py for the prompt
    expertise_map = {
        "VectorScale (AI Infrastructure Startup)": "High-performance vector databases, HNSW indexing, and production ML infrastructure.",
        "ShieldAI (Cybersecurity Company)": "LLM security, prompt injection defense, and zero-trust architecture.",
        "PayFlow (Fintech Startup)": "AI-powered payment processing, fraud detection, and regulatory compliance automation."
    }

    # Load Social Context (from Phase 1 Data)
    social_path = os.path.join(os.path.dirname(script_dir), "Prototypes", "Data", "social_community_posts.json")
    with open(social_path, "r") as f: social_data = json.load(f)
    # Simulate a search for community questions (Prototype simplified)
    community_context = str(social_data[:5]) 

    print("PROTOTYPE S4: GENERATING STRATEGIC CONTENT BRIEFS...")
    
    final_reports = []

    # Process TOP opportunity for each company
    for comp_name, matches in scorecards.items():
        top_opportunity = matches[0]
        
        # Only process high-score opportunities
        if top_opportunity['final_score'] < 80:
            print(f"  Skipping {comp_name}: No high-ROI opportunity today.")
            continue
            
        print(f"  Generating brief for {comp_name} on topic: {top_opportunity['topic'][:40]}...")
        
        brief = generate_seo_brief(
            comp_name, 
            expertise_map.get(comp_name, "Tech"), 
            top_opportunity['topic'], 
            "Emerging high-signal trend detected by Curate-AI.",
            community_context,
            client
        )
        
        if brief:
            report = ContentStrategyReport(
                company_name=comp_name,
                primary_topic=top_opportunity['topic'],
                opportunity_score=top_opportunity['final_score'],
                brief=brief
            )
            final_reports.append(report.dict())

    # SAVE RESULTS
    output_path = os.path.join(script_dir, "Data", "content_strategy_briefs.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_reports, f, indent=2)

    # DISPLAY A SAMPLE PREVIEW
    if final_reports:
        sample = final_reports[0]
        print(f"\n--- SAMPLE BRIEF PREVIEW: {sample['company_name']} ---")
        print(f"TOPIC: {sample['primary_topic']}")
        print(f"ANGLE: {sample['brief']['angle']}")
        print(f"TITLES: {', '.join(sample['brief']['suggested_titles'])}")

    print(f"\nCOMPLETED: Content briefs saved to SEO_Prototype/Data/")

if __name__ == "__main__":
    main()
