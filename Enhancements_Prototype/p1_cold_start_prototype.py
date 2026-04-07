"""
P1: Cold Start — LinkedIn PDF & Resume Import
Extracts user interest profiles from uploaded PDFs using text extraction + LLM profiling.
Benchmarks pdfplumber vs pypdf for extraction speed and quality.
"""
import time
import os
import json
import pdfplumber
from pypdf import PdfReader
from typing import List, Dict
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()


class UserInterestProfile(BaseModel):
    name: str
    job_title: str
    seniority: str
    primary_interests: List[str]
    technical_skills: List[str]
    bio_summary: str
    category_weights: Dict[str, float]


def extract_with_pdfplumber(file_path: str) -> tuple[str, float]:
    start = time.time()
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print(f"    [!] pdfplumber error: {e}")
    return text, time.time() - start


def extract_with_pypdf(file_path: str) -> tuple[str, float]:
    start = time.time()
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        print(f"    [!] pypdf error: {e}")
    return text, time.time() - start


def detect_document_type(text: str) -> str:
    """Detect whether the PDF is a LinkedIn export or a standard resume."""
    linkedin_markers = ["linkedin.com/in/", "Experience", "Top Skills", "About", "Education"]
    score = sum(1 for m in linkedin_markers if m.lower() in text.lower())
    return "LinkedIn PDF" if score >= 3 else "Resume"


def build_profile_via_llm(text: str, source_type: str) -> UserInterestProfile:
    """Send extracted text to GPT-4o-mini to generate a structured interest profile."""
    prompt = f"""
    Analyze the following {source_type} and extract a structured interest profile.

    TAXONOMY (assign a weight 0.0–1.0 for each):
    LLMs, AI Agents, Computer Vision, Security, Hardware, Software Engineering, AI Policy, General AI, Data Engineering, Startups

    TEXT:
    {text[:6000]}

    Return JSON:
    {{
        "name": "...",
        "job_title": "...",
        "seniority": "entry / mid / senior / lead",
        "primary_interests": ["...", "..."],
        "technical_skills": ["...", "..."],
        "bio_summary": "2-sentence professional summary suitable for vector encoding",
        "category_weights": {{
            "LLMs": 0.0,
            "AI Agents": 0.0,
            "Computer Vision": 0.0,
            "Security": 0.0,
            "Hardware": 0.0,
            "Software Engineering": 0.0,
            "AI Policy": 0.0,
            "General AI": 0.0,
            "Data Engineering": 0.0,
            "Startups": 0.0
        }}
    }}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a technical recruiter. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )

    data = json.loads(response.choices[0].message.content)
    return UserInterestProfile.model_validate(data)


def main():
    files = {
        "LinkedIn": "LinkedIn_Profile.pdf",
        "Resume": "Resume.pdf"
    }

    all_results = {}

    for label, path in files.items():
        print(f"\n--- Processing {label} ---")
        if not os.path.exists(path):
            print(f"  [!] {path} not found. Skipping.")
            continue

        # Step 1: Benchmark both extractors
        print(f"  Step 1: Benchmarking PDF text extraction...")
        txt_plumb, lat_plumb = extract_with_pdfplumber(path)
        txt_pypdf, lat_pypdf = extract_with_pypdf(path)

        print(f"    pdfplumber : {lat_plumb:.3f}s | {len(txt_plumb)} chars")
        print(f"    pypdf      : {lat_pypdf:.3f}s | {len(txt_pypdf)} chars")

        # Step 2: Detect document type
        best_text = txt_pypdf if len(txt_pypdf) >= len(txt_plumb) else txt_plumb
        doc_type = detect_document_type(best_text)
        print(f"  Step 2: Detected as '{doc_type}'")

        # Step 3: Extract profile via LLM
        print(f"  Step 3: Extracting interest profile via LLM...")
        profile = build_profile_via_llm(best_text, doc_type)

        # Step 4: Save output
        output_file = f"Enhancements_Prototype/Data/{label.lower()}_profile.json"
        with open(output_file, "w") as f:
            f.write(profile.model_dump_json(indent=2))

        print(f"  Saved: {output_file}")
        all_results[label] = profile.model_dump()

    # Summary
    print("\n" + "=" * 50)
    print("COLD START EXTRACTION SUMMARY")
    print("=" * 50)
    for label, res in all_results.items():
        top_cat = max(res["category_weights"], key=res["category_weights"].get)
        top_val = res["category_weights"][top_cat]
        print(f"  {label}: {res['name']} | {res['job_title']}")
        print(f"    Top category: {top_cat} ({top_val})")
        print(f"    Skills: {', '.join(res['technical_skills'][:8])}")
        print(f"    Bio: {res['bio_summary'][:100]}...")


if __name__ == "__main__":
    main()
