import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# 1. Define Test Company Profiles from Reference3.md
COMPANIES = [
    {
        "company_id": "comp_aiinfra",
        "name": "VectorScale (AI Infrastructure Startup)",
        "expertise_description": "We build high-performance vector databases for AI applications. Our blog covers embedding optimization, HNSW indexing, retrieval-augmented generation, and production ML infrastructure.",
        "existing_blog_topics": [
            "How to optimize HNSW index parameters for 10M+ vectors",
            "RAG pipeline architecture: lessons from production",
            "Embedding model selection guide for enterprise search",
            "Vector database benchmarks: Qdrant vs Pinecone vs Weaviate"
        ]
    },
    {
        "company_id": "comp_cybersec",
        "name": "ShieldAI (Cybersecurity Company)",
        "expertise_description": "Enterprise cybersecurity platform specializing in LLM security, prompt injection defense, API security, and zero-trust architecture.",
        "existing_blog_topics": [
            "Prompt injection attacks: a taxonomy and defense guide",
            "Securing LLM APIs in production environments",
            "Zero-trust architecture for AI microservices",
            "Red-teaming GPT-4: what we found"
        ]
    },
    {
        "company_id": "comp_fintech",
        "name": "PayFlow (Fintech Startup)",
        "expertise_description": "AI-powered payment processing and fraud detection. Our blog covers financial AI, real-time transaction scoring, regulatory compliance automation, and machine learning for risk assessment.",
        "existing_blog_topics": [
            "How we reduced fraud by 40% with ensemble ML models",
            "Real-time transaction scoring at 10K TPS",
            "PCI-DSS compliance automation with AI agents",
            "Building a feature store for financial ML"
        ]
    }
]

def main():
    print("PROTOTYPE S1: COMPANY PROFILE VECTORS STARTING...")
    
    # 2. Initialize the semantic model
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    company_vectors = []
    vector_results = []

    # 3. Vectorize each company
    for comp in COMPANIES:
        print(f"  Vectorizing profile for: {comp['name']}...")
        
        # Combine expertise + history for a "Deep Knowledge Representation"
        full_context = comp['expertise_description'] + " " + " ".join(comp['existing_blog_topics'])
        
        # Build the vector
        vector = model.encode(full_context)
        company_vectors.append(vector)
        
        # Save as a JSON serializable version for our report
        vector_results.append({
            "company_id": comp['company_id'],
            "name": comp['name'],
            "authority_vector": vector.tolist()
        })

    # 4. VERIFICATION: Compare inter-company similarity
    print("\n--- SIMILARITY MATRIX (Semantic Separation) ---")
    sim_matrix = cosine_similarity(company_vectors)
    
    for i in range(len(COMPANIES)):
        for j in range(i+1, len(COMPANIES)):
            sim = sim_matrix[i][j]
            print(f"{COMPANIES[i]['name'][:10]} <--> {COMPANIES[j]['name'][:10]}: {sim:.4f}")

    # 5. SAVE DATA
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "Data", "company_authority_vectors.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(vector_results, f, indent=2)

    print(f"\nCOMPLETED: Authority vectors saved to SEO_Prototype/Data/company_authority_vectors.json")

if __name__ == "__main__":
    main()
