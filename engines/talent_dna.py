"""
Talent DNA Engine
Converts every candidate into a structured DNA vector — 8 dimensions.
Each dimension is independently scored 0.0–1.0.
The DNA is used by scorer.py to produce a richer final score.

DNA dimensions:
  technical       — skill depth and breadth vs JD must-haves
  adaptability    — career transitions, domain diversity, growth trajectory
  professional    — leadership, ownership, startup fit, cognitive complexity
  trust           — recruiter engagement, platform verification, reliability
  risk            — anomaly and fabrication signals (inverse: high = low risk)
  communication   — headline quality, summary depth, endorsements, connections
  innovation      — GitHub activity, skill recency, assessment scores
  execution       — tenure stability, delivery evidence, production experience
"""

from datetime import datetime
from engines.jd_intelligence import (
    MUST_HAVE_SKILLS, STRONG_POSITIVE_SKILLS, PRODUCT_INDUSTRIES,
    CONSULTING_COMPANIES, REFERENCE_DATE, TENURE_MIN_MONTHS,
)

_MUST_SET    = frozenset(MUST_HAVE_SKILLS)
_STRONG_SET  = frozenset(STRONG_POSITIVE_SKILLS)
_PRODUCT_SET = frozenset(PRODUCT_INDUSTRIES)
_CONSULT_SET = frozenset(CONSULTING_COMPANIES)

# Leadership/ownership keywords found in career descriptions
_LEADERSHIP_KW = {
    "led", "lead", "managed", "built", "architected", "designed", "founded",
    "owned", "drove", "established", "launched", "created", "spearheaded",
    "headed", "directed", "mentored", "principal", "staff", "senior staff",
}
_STARTUP_SIZES = {"1-10", "11-50", "51-200", "51-100", "101-200"}
_COMPLEXITY_KW = {
    "scale", "scaled", "billion", "million", "distributed", "real-time",
    "latency", "throughput", "high availability", "fault tolerant",
    "microservices", "infrastructure", "platform", "framework",
}


def compute_dna(candidate: dict) -> dict:
    """
    Returns a DNA dict with 8 float scores (0.0–1.0) and metadata.
    Fast: designed to run on 100K candidates without compute concern.
    """
    profile  = candidate.get("profile", {})
    sigs     = candidate.get("redrob_signals", {})
    career   = candidate.get("career_history", [])
    skills   = candidate.get("skills", [])
    edu      = candidate.get("education", [])
    certs    = candidate.get("certifications", [])

    career_text_full = " ".join(j.get("description", "").lower() for j in career)
    skill_names_lower = {s["name"].lower() for s in skills}
    skill_dur_map = {s["name"].lower(): s.get("duration_months", 0) for s in skills}
    all_text = career_text_full + " " + " ".join(skill_names_lower)

    # ── 1. TECHNICAL DNA ─────────────────────────────────────────────────────
    must_hits   = sum(1 for kw in _MUST_SET   if kw in all_text)
    strong_hits = sum(1 for kw in _STRONG_SET if kw in all_text)
    depth = sum(
        min(dur / 36.0, 1.0) for sname, dur in skill_dur_map.items()
        if any(kw in sname for kw in _MUST_SET)
    )
    assess_scores = sigs.get("skill_assessment_scores", {})
    assess_avg = (sum(assess_scores.values()) / len(assess_scores) / 100.0
                  if assess_scores else 0.3)
    technical = min(
        (must_hits * 3.0 + strong_hits * 1.5 + depth + assess_avg) / 14.0, 1.0
    )

    # ── 2. ADAPTABILITY DNA ──────────────────────────────────────────────────
    # Measures: industry diversity, tech transitions, career growth direction
    industries = {j.get("industry", "").lower() for j in career if j.get("industry")}
    industry_diversity = min(len(industries) / 4.0, 1.0)

    # Tech transition: moved from non-AI role to AI role in career
    titles_lower = [j.get("title", "").lower() for j in career]
    ai_titles = {"ml", "ai", "data", "nlp", "search", "ranking", "retrieval", "recommendation"}
    had_non_ai_before_ai = False
    seen_non_ai = False
    for title in reversed(titles_lower):  # oldest first
        is_ai = any(kw in title for kw in ai_titles)
        if not is_ai:
            seen_non_ai = True
        elif seen_non_ai:
            had_non_ai_before_ai = True
            break
    transition_score = 0.8 if had_non_ai_before_ai else 0.4

    # Skill recency: any must-have or strong skill added in last 24 months
    recent_skills = sum(
        1 for sname, dur in skill_dur_map.items()
        if dur <= 24 and any(kw in sname for kw in _MUST_SET | _STRONG_SET)
    )
    recency_score = min(recent_skills / 3.0, 1.0)

    adaptability = 0.40 * industry_diversity + 0.35 * transition_score + 0.25 * recency_score

    # ── 3. PROFESSIONAL DNA ──────────────────────────────────────────────────
    # Leadership: action verbs in career descriptions
    leadership_hits = sum(
        1 for kw in _LEADERSHIP_KW if kw in career_text_full
    )
    leadership_score = min(leadership_hits / 6.0, 1.0)

    # Startup experience: spent time at small/early companies
    startup_months = sum(
        j.get("duration_months", 0) for j in career
        if any(sz in str(j.get("company_size", "")) for sz in _STARTUP_SIZES)
    )
    startup_score = min(startup_months / 24.0, 1.0)

    # Cognitive complexity: scale/distributed systems evidence
    complexity_hits = sum(1 for kw in _COMPLEXITY_KW if kw in career_text_full)
    complexity_score = min(complexity_hits / 5.0, 1.0)

    # Company size progression (growing responsibility = professional signal)
    sizes = []
    for j in career:
        sz = str(j.get("company_size", ""))
        for bracket, val in [("10001", 5), ("5001", 4), ("1001", 3), ("201", 2), ("51", 1), ("11", 0.5)]:
            if bracket in sz:
                sizes.append(val)
                break

    professional = (
        0.40 * leadership_score +
        0.30 * startup_score +
        0.30 * complexity_score
    )

    # ── 4. TRUST DNA ────────────────────────────────────────────────────────
    resp_rate       = float(sigs.get("recruiter_response_rate", 0))
    interview_rate  = float(sigs.get("interview_completion_rate", 0))
    offer_rate      = sigs.get("offer_acceptance_rate", -1)
    offer_score     = float(offer_rate) if offer_rate >= 0 else 0.5
    verified_email  = 1.0 if sigs.get("verified_email")  else 0.0
    verified_phone  = 1.0 if sigs.get("verified_phone")  else 0.0
    linkedin        = 0.8 if sigs.get("linkedin_connected") else 0.3
    saved_30d       = min(sigs.get("saved_by_recruiters_30d", 0) / 5.0, 1.0)

    trust = (
        0.28 * resp_rate +
        0.20 * interview_rate +
        0.15 * offer_score +
        0.12 * verified_email +
        0.08 * verified_phone +
        0.08 * linkedin +
        0.09 * saved_30d
    )

    # ── 5. RISK DNA (inverse: 1.0 = no risk) ────────────────────────────────
    from engines.honeypot import detect_anomalies
    anomalies     = detect_anomalies(candidate)
    anomaly_pen   = anomalies["anomaly_score"] * 0.40  # max 0.40 from anomalies

    risk_penalties = anomaly_pen

    # Short avg tenure (hopping)
    past_tenures = [j.get("duration_months", 0) for j in career if not j.get("is_current")]
    avg_tenure = sum(past_tenures) / len(past_tenures) if past_tenures else TENURE_MIN_MONTHS
    if avg_tenure < 12:
        risk_penalties += 0.30
    elif avg_tenure < TENURE_MIN_MONTHS:
        risk_penalties += 0.15

    # Entire career consulting
    all_cos = [j.get("company", "").lower() for j in career]
    if all_cos and all(any(co in comp for co in _CONSULT_SET) for comp in all_cos):
        risk_penalties += 0.40

    # Salary expectation vs role (flight risk)
    sal = sigs.get("expected_salary_range_inr_lpa", {})
    if sal:
        sal_min = sal.get("min", 0)
        if sal_min > 80:
            risk_penalties += 0.15

    # Response time: very slow = hard to close
    avg_resp_hrs = sigs.get("avg_response_time_hours", 0)
    if avg_resp_hrs > 96:
        risk_penalties += 0.15

    risk = max(0.0, 1.0 - risk_penalties)

    # ── 6. COMMUNICATION DNA ────────────────────────────────────────────────
    headline = profile.get("headline", "")
    summary  = profile.get("summary", "")
    headline_quality = min(len(headline.split()) / 8.0, 1.0) if headline else 0.0
    summary_depth    = min(len(summary.split()) / 60.0, 1.0) if summary else 0.0
    endorsements = min(sigs.get("endorsements_received", 0) / 20.0, 1.0)
    connections  = min(sigs.get("connection_count", 0) / 300.0, 1.0)
    profile_views = min(sigs.get("profile_views_received_30d", 0) / 30.0, 1.0)

    communication = (
        0.25 * headline_quality +
        0.30 * summary_depth +
        0.20 * endorsements +
        0.15 * connections +
        0.10 * profile_views
    )

    # ── 7. INNOVATION DNA ───────────────────────────────────────────────────
    github = sigs.get("github_activity_score", -1)
    github_score = float(github) / 100.0 if github >= 0 else 0.2

    # Assessment score average (platform-verified skills)
    assess_innovation = assess_avg  # reuse from technical

    # Certifications (signal of continuous learning)
    cert_score = min(len(certs) / 3.0, 1.0)

    # Skill breadth (total unique skills across must+strong)
    breadth = sum(
        1 for sname in skill_names_lower
        if any(kw in sname for kw in _MUST_SET | _STRONG_SET)
    )
    breadth_score = min(breadth / 8.0, 1.0)

    innovation = (
        0.35 * github_score +
        0.25 * assess_innovation +
        0.20 * breadth_score +
        0.20 * cert_score
    )

    # ── 8. EXECUTION DNA ────────────────────────────────────────────────────
    # Product company time (shipped to real users)
    product_months = sum(
        j.get("duration_months", 0) for j in career
        if j.get("industry", "").lower() in _PRODUCT_SET
    )
    product_score = min(product_months / 36.0, 1.0)

    # Pre-LLM era production experience
    pre_llm = 0.0
    for j in career:
        start_str = j.get("start_date", "")
        if start_str:
            try:
                yr = int(start_str[:4])
                if yr <= 2022:
                    desc = j.get("description", "").lower()
                    if any(kw in desc for kw in ["retrieval", "ranking", "search", "recommendation", "embedding", "nlp"]):
                        pre_llm = 1.0
                        break
            except ValueError:
                pass

    # Tenure score
    tenure_score = min(avg_tenure / TENURE_MIN_MONTHS, 1.0)

    execution = (
        0.50 * product_score +
        0.30 * tenure_score +
        0.20 * pre_llm
    )

    return {
        "technical":     round(technical,     4),
        "adaptability":  round(adaptability,  4),
        "professional":  round(professional,  4),
        "trust":         round(trust,         4),
        "risk":          round(risk,          4),
        "communication": round(communication, 4),
        "innovation":    round(innovation,    4),
        "execution":     round(execution,     4),
        # metadata for reasoning engine
        "_leadership_hits":  leadership_hits,
        "_startup_months":   startup_months,
        "_industry_count":   len(industries),
        "_assess_scores":    assess_scores,
        "_avg_tenure":       round(avg_tenure, 1),
        "_product_months":   product_months,
        "_pre_llm":          pre_llm,
        "_breadth":          breadth,
    }


def dna_composite_score(dna: dict, weights: dict = None) -> float:
    """
    Weighted composite of DNA dimensions.
    Default weights tuned to NDCG@10 being 50% of the hackathon metric.
    """
    if weights is None:
        weights = {
            "technical":     0.32,
            "execution":     0.18,
            "trust":         0.14,
            "risk":          0.12,
            "professional":  0.10,
            "adaptability":  0.07,
            "innovation":    0.05,
            "communication": 0.02,
        }
    return round(
        sum(dna.get(k, 0) * w for k, w in weights.items()), 6
    )
