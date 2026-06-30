"""Smoke test — verifies all engines work end-to-end on a synthetic candidate."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from engines.scorer import score_candidate
from engines.reasoning import generate_reasoning
from engines.talent_dna import compute_dna
from engines.skill_truth import verify_skills
from engines.confidence import compute_confidence
from engines.honeypot import detect_anomalies

CANDIDATE = {
    "candidate_id": "CAND_TEST_001",
    "profile": {
        "anonymized_name": "Test Engineer",
        "headline": "Senior ML Engineer | Search & Retrieval | FAISS | Embeddings",
        "summary": "7 years building production retrieval systems at scale. Deep expertise in dense retrieval, FAISS, and semantic search. Shipped recommendation systems serving 10M+ users.",
        "location": "Hyderabad, Telangana",
        "country": "India",
        "years_of_experience": 7,
        "current_title": "Senior ML Engineer",
        "current_company": "Zomato",
        "current_company_size": "5001-10000",
        "current_industry": "Food Delivery",
    },
    "career_history": [
        {
            "company": "Zomato", "title": "Senior ML Engineer",
            "start_date": "2022-01-01", "end_date": None,
            "duration_months": 29, "is_current": True,
            "industry": "Food Delivery", "company_size": "5001-10000",
            "description": "Built production FAISS-based retrieval system for restaurant search serving 10M DAU. Led embedding pipeline using sentence transformers and BGE models. Implemented hybrid search with BM25 + dense retrieval.",
        },
        {
            "company": "Flipkart", "title": "ML Engineer",
            "start_date": "2019-06-01", "end_date": "2021-12-31",
            "duration_months": 30, "is_current": False,
            "industry": "E-commerce", "company_size": "10001+",
            "description": "Developed product ranking and recommendation systems using learning to rank (LambdaMART). Improved NDCG@10 by 12% through feature engineering and XGBoost model.",
        },
        {
            "company": "Mu Sigma", "title": "Data Scientist",
            "start_date": "2017-07-01", "end_date": "2019-05-31",
            "duration_months": 22, "is_current": False,
            "industry": "Analytics", "company_size": "1001-5000",
            "description": "Built NLP models for text classification. Delivered recommendation engine for retail client using collaborative filtering.",
        },
    ],
    "education": [
        {
            "institution": "IIT Hyderabad", "degree": "B.Tech",
            "field_of_study": "Computer Science",
            "start_year": 2013, "end_year": 2017,
            "grade": "8.9 CGPA", "tier": "tier_1",
        }
    ],
    "skills": [
        {"name": "FAISS",               "proficiency": "expert",        "endorsements": 12, "duration_months": 29},
        {"name": "Embeddings",          "proficiency": "expert",        "endorsements": 8,  "duration_months": 36},
        {"name": "Sentence Transformers","proficiency": "advanced",     "endorsements": 6,  "duration_months": 24},
        {"name": "PyTorch",             "proficiency": "advanced",      "endorsements": 10, "duration_months": 48},
        {"name": "Python",              "proficiency": "expert",        "endorsements": 15, "duration_months": 72},
        {"name": "Learning to Rank",    "proficiency": "advanced",      "endorsements": 5,  "duration_months": 30},
        {"name": "XGBoost",             "proficiency": "advanced",      "endorsements": 4,  "duration_months": 30},
        {"name": "BM25",                "proficiency": "intermediate",  "endorsements": 3,  "duration_months": 18},
        {"name": "Elasticsearch",       "proficiency": "intermediate",  "endorsements": 2,  "duration_months": 12},
        {"name": "RAG",                 "proficiency": "intermediate",  "endorsements": 2,  "duration_months": 10},
    ],
    "certifications": ["AWS ML Specialty", "Deep Learning Specialization - Coursera"],
    "languages": ["English", "Hindi"],
    "redrob_signals": {
        "profile_completeness_score": 92.0,
        "signup_date": "2025-06-01",
        "last_active_date": "2026-06-20",
        "open_to_work_flag": True,
        "profile_views_received_30d": 34,
        "applications_submitted_30d": 3,
        "recruiter_response_rate": 0.82,
        "avg_response_time_hours": 14.0,
        "skill_assessment_scores": {
            "NLP": 74.0,
            "Fine-tuning LLMs": 68.0,
            "Machine Learning": 81.0,
        },
        "connection_count": 412,
        "endorsements_received": 47,
        "notice_period_days": 30,
        "expected_salary_range_inr_lpa": {"min": 35, "max": 55},
        "preferred_work_mode": "hybrid",
        "willing_to_relocate": True,
        "github_activity_score": 71.0,
        "search_appearance_30d": 280,
        "saved_by_recruiters_30d": 6,
        "interview_completion_rate": 0.88,
        "offer_acceptance_rate": 0.67,
        "verified_email": True,
        "verified_phone": True,
        "linkedin_connected": True,
    },
}

def run():
    result   = score_candidate(CANDIDATE)
    dna      = result["dna"]
    skill_v  = result["skill_verification"]
    anomaly  = detect_anomalies(CANDIDATE)
    reasoning = generate_reasoning(CANDIDATE, result, rank=1)

    print("=" * 60)
    print("  SMOKE TEST — v2 Talent DNA Architecture")
    print("=" * 60)
    print(f"  Final Score       : {result['final_score']}")
    print(f"  DNA Score         : {result['dna_score']}")
    print(f"  Skill Score       : {result['skill_score']}")
    print(f"  Verified Skill    : {result['verified_skill_score']}")
    print(f"  Behavioral        : {result['behavioral_score']}")
    print(f"  Availability      : {result['availability_score']}")
    print()
    print("  ── Talent DNA ──────────────────────────────────────")
    for dim in ["technical","adaptability","professional","trust","risk","communication","innovation","execution"]:
        bar = "█" * int(dna.get(dim,0) * 20)
        print(f"  {dim:<14}: {dna.get(dim,0):.3f}  {bar}")
    print()
    print(f"  ── Skill Verification ──────────────────────────────")
    print(f"  Verified score    : {skill_v['verified_skill_score']}")
    print(f"  Top verified      : {skill_v['top_verified_skills']}")
    print()
    print(f"  ── Risk / Anomaly ──────────────────────────────────")
    print(f"  Anomaly score     : {anomaly['anomaly_score']}")
    print(f"  Flags             : {anomaly['anomaly_flags']}")
    print(f"  Honeypot          : {result['is_honeypot']}")
    print()
    print(f"  ── Confidence ──────────────────────────────────────")
    print(f"  Score             : {result['confidence_score']}")
    print(f"  Label             : {result['confidence_label']}")
    print(f"  Reason            : {result['confidence_reason']}")
    print()
    print(f"  ── Reasoning ───────────────────────────────────────")
    print(f"  {reasoning}")
    print()

    assert result["final_score"] > 0.70, f"Score too low: {result['final_score']}"
    assert result["confidence_label"] in ("high", "medium", "low")
    assert not result["is_honeypot"]
    assert len(reasoning) > 40
    assert dna["technical"] > 0.5
    print("  ✅ ALL ASSERTIONS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    run()
