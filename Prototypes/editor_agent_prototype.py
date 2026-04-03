import json
import os
from typing import List, Literal
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# 1. Define the Editor's Standard (The Checklist)
class EditorIssue(BaseModel):
    issue_type: Literal["hallucination", "factual_error", "tone_mismatch", "missing_link"]
    description: str
    severity: Literal["high", "medium", "low"]
    suggested_fix: str

class EditorReport(BaseModel):
    verdict: Literal["pass", "needs_revision", "reject"]
    issues: List[EditorIssue]
    editorial_note: str

def edit_newsletter(article_title: str, article_full_text: str, summary_draft: str, client: OpenAI) -> EditorReport:
    """
    Simulates the Editor Agent (The Guardrail).
    It compares the Writer's summary draft against the Original Article Text.
    """
    
    prompt = f"""
    You are the Editor-in-Chief of a high-end tech newsletter. 
    Your job is to FACT-CHECK the draft summary against the original source text.
    
    ORIGINAL ARTICLE TITLE: {article_title}
    ORIGINAL SOURCE TEXT (TRUNCATED): {article_full_text[:3000]}
    
    WRITER'S DRAFT SUMMARY: {summary_draft}
    
    STRICT RULES:
    1. Look for 'hallucinations' (facts in the draft not in the source).
    2. Check for 'factual errors' (misstating numbers/names).
    3. Look for 'tone mismatch' (is it too informal or professional?).
    
    Provide your report in a structured JSON format.
    """
    
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a professional editorial reviewer."},
                      {"role": "user", "content": prompt}],
            response_format=EditorReport
        )
        return response.choices[0].message.parsed
    except Exception as e:
        return EditorReport(
            verdict="reject",
            issues=[EditorIssue(issue_type="hallucination", description=f"API error: {str(e)}", severity="high", suggested_fix="Check API connection")],
            editorial_note="System crash during review."
        )

def main():
    load_dotenv()
    client = OpenAI()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "Data")
    
    # CASE 1: Test with a GOOD draft (The one we generated earlier)
    # STORY: Slack adding 30 AI features
    original_title = "Slack adds 30 AI features"
    original_body = "Slack today announced more than 30 new capabilities for Slackbot... built on Anthropic's Claude model."
    good_draft = "Slack's overhaul of its chatbot adds 30 new features, including meeting note-taking and deep research modes. For security researchers, this expansion raises questions about data privacy and the security of external tool integration."

    # CASE 2: Test with a BAD draft (We inject a hallucination)
    bad_draft = "Slack has been acquired by Apple for $500 billion, marking a new era of AI for the iPhone. This move will compromise all existing developer integrations."

    print("EDITOR AGENT: REVIEWING DRAFTS...")
    
    print("\n--- TEST 1: REVIEWING GOOD DRAFT ---")
    report1 = edit_newsletter(original_title, original_body, good_draft, client)
    print(f"VERDICT: {report1.verdict.upper()}")
    print(f"NOTE: {report1.editorial_note}")
    if report1.issues:
        for iss in report1.issues: print(f"  [{iss.severity}] {iss.issue_type}: {iss.description}")

    print("\n--- TEST 2: REVIEWING 'HALLUCINATED' DRAFT ---")
    report2 = edit_newsletter(original_title, original_body, bad_draft, client)
    print(f"VERDICT: {report2.verdict.upper()}")
    print(f"NOTE: {report2.editorial_note}")
    if report2.issues:
        for iss in report2.issues: 
            print(f"  [{iss.severity}] {iss.issue_type}: {iss.description}")
            print(f"  FIX: {iss.suggested_fix}")

    # Output results for final Master Pipeline (Prototype 11)
    output_path = os.path.join(data_dir, "editor_report_sample.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report2.dict(), f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
