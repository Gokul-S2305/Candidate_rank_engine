"""
Candidate Scorer v2 — Talent DNA Architecture
Single-pass, CPU-only, no external APIs.
Full 100K runs well within the 5-min budget.

Pipeline per candidate:
  1. Honeypot check (fast exit)
  2. Disqualifiers (fast exit)
  3. Talent DNA computation (8 dimensions)
  4. Skill Truth Verification
  5. Decision Confidence
  6. Final weighted score
"""

from datetime import datetime
from engines.jd_intelligence import (
    MUST_HAVE_SKILLS, STRONG_POSITIVE_SKILLS, SOFT_POSITIVE_SKILLS,
    CONSULTING_COMPANIES, BAD_TITLE_TOKENS, PRODUCT_INDUSTRIES,
    TIER_1_LOCATIONS, TIER_2_LOCATIONS,
    YOE_IDEAL_MIN, YOE_IDEAL_MAX, YOE_STRETCH_MIN, YOE_STRETCH_MAX,
    NOTICE_IDEAL, NOTICE_ACCEPTABLE, NOTICE_PENALISED,
    TENURE_MIN_MONTHS, REFERENCE_DATE,
)
from engines.honeypot   import detect_honeypot
from engines.talent_dna import compute_dna, dna_composite_score
from engines.skill_truth import verify_skills
from engines.confidence import compute_confidence

# ── Precompile lookups ────────────────────────────────────────────────────────
_CONSULTING_SET = frozenset(CONSULTING_COMPANIES)
_MUST_SET       = frozenset(MUST_HAVE_SKILLS)
_STRONG_SET     = frozenset(STRONG_POSITIVE_SKILLS)
_SOFT_SET       = frozenset(SOFT_POSITIVE_SKILLS)
_BAD_TITLE_SET  = frozenset(BAD_TITLE_TOKENS)
_PRODUCT_SET    = frozenset(PRODUCT_INDUSTRIES)


def _text_contains_any(text: str, keywords: frozenset) -> list[str]:
    return [kw for kw in keywords if kw in text]


def score_candidate(candidate: dict) -> dict:
    profile  = candidate.get("profile", {})
    sigs     = candidate.get("redrob_signals", {})
    career   = candidate.get("career_history", [])
    skills   = candidate.get("skills", [])

    # ── 1. HONEYPOT CHECK ────────────────────────────────────────────────────
    is_honeypot, honeypot_reason = detect_honeypot(candidate)
    if is_honeypot:
        return _honeypot_result(honeypot_reason)

    # ── 2. DISQUALIFIERS ─────────────────────────────────────────────────────
    all_companies_lower = [j.get("company", "").lower() for j in career]
    is_pure_consulting = bool(all_companies_lower) and all(
        any(co in comp for co in _CONSULTING_SET)
        for comp in all_companies_lower
    )
    if is_pure_consulting:
        return _disqualified(0.01, "pure consulting background", candidate)

    title_lower = profile.get("current_title", "").lower()
    if any(bt in title_lower for bt in _BAD_TITLE_SET):
        return _disqualified(0.02, f"title '{profile.get('current_title','')}' outside domain", candidate)

    # ── 3. TEXT CORPORA ───────────────────────────────────────────────────────
    career_text    = " ".join(j.get("description", "").lower() for j in career)
    skill_names_lower = set()
    skill_dur_map: dict[str, int] = {}
    for s in skills:
        sname = s["name"].lower()
        skill_names_lower.add(sname)
        skill_dur_map[sname] = s.get("duration_months", 0)
    all_text = career_text + " " + " ".join(skill_names_lower)

    # ── 4. TALENT DNA ─────────────────────────────────────────────────────────
    dna = compute_dna(candidate)
    dna_score = dna_composite_score(dna)

    # ── 5. SKILL TRUTH VERIFICATION ──────────────────────────────────────────
    skill_verification = verify_skills(candidate)
    vscore = skill_verification["verified_skill_score"]

    # ── 6. LEGACY SIGNALS (kept for backward-compat & reasoning) ─────────────
    matched_must   = _text_contains_any(all_text, _MUST_SET)
    matched_strong = _text_contains_any(all_text, _STRONG_SET)
    matched_soft   = _text_contains_any(all_text, _SOFT_SET)

    depth_score = 0.0
    for sname, dur in skill_dur_map.items():
        if any(kw in sname for kw in _MUST_SET):
            depth_score += min(dur / 36.0, 1.0)
        elif any(kw in sname for kw in _STRONG_SET):
            depth_score += min(dur / 48.0, 0.5)

    raw_skill  = len(matched_must)*3.0 + len(matched_strong)*1.5 + len(matched_soft)*0.5 + depth_score
    skill_score = min(raw_skill / 16.0, 1.0)

    yoe = profile.get("years_of_experience", 0)
    if YOE_IDEAL_MIN <= yoe <= YOE_IDEAL_MAX:           yoe_score = 1.0
    elif YOE_STRETCH_MIN <= yoe < YOE_IDEAL_MIN or YOE_IDEAL_MAX < yoe <= YOE_STRETCH_MAX:
                                                         yoe_score = 0.7
    elif yoe > YOE_STRETCH_MAX:                          yoe_score = 0.5
    else:                                                yoe_score = 0.3

    past_tenures   = [j.get("duration_months", 0) for j in career if not j.get("is_current")]
    avg_tenure     = sum(past_tenures)/len(past_tenures) if past_tenures else TENURE_MIN_MONTHS
    product_months = sum(j.get("duration_months", 0) for j in career if j.get("industry","").lower() in _PRODUCT_SET)

    # Availability
    notice = int(sigs.get("notice_period_days", 90))
    if   notice <= NOTICE_IDEAL:      notice_score = 1.0
    elif notice <= NOTICE_ACCEPTABLE: notice_score = 0.75
    elif notice <= NOTICE_PENALISED:  notice_score = 0.50
    else:                              notice_score = 0.20

    location_lower = profile.get("location", "").lower()
    country_lower  = profile.get("country", "").lower()
    relocate       = bool(sigs.get("willing_to_relocate", False))
    if any(city in location_lower for city in TIER_1_LOCATIONS):    loc_score = 1.0
    elif any(city in location_lower for city in TIER_2_LOCATIONS):  loc_score = 0.85
    elif country_lower == "india":  loc_score = 0.65 if relocate else 0.45
    else:                           loc_score = 0.30 if relocate else 0.10
    availability_score = 0.55 * notice_score + 0.45 * loc_score

    # Behavioral
    last_active_str = sigs.get("last_active_date", "2024-01-01")
    days_inactive = 0
    try:
        last_active   = datetime.strptime(last_active_str, "%Y-%m-%d").date()
        days_inactive = max(0, (REFERENCE_DATE - last_active).days)
        activity_score = max(0.0, 1.0 - days_inactive / 180.0)
    except ValueError:
        activity_score = 0.3

    resp_rate      = float(sigs.get("recruiter_response_rate", 0))
    interview_rate = float(sigs.get("interview_completion_rate", 0))
    open_flag      = 1.0 if sigs.get("open_to_work_flag") else 0.3
    offer_rate     = sigs.get("offer_acceptance_rate", -1)
    offer_score    = float(offer_rate) if offer_rate >= 0 else 0.5
    github         = sigs.get("github_activity_score", -1)
    github_score   = float(github)/100.0 if github >= 0 else 0.2
    behavioral_score = (0.30*resp_rate + 0.20*interview_rate + 0.20*activity_score +
                        0.15*open_flag + 0.10*offer_score + 0.05*github_score)

    # ── 7. FINAL SCORE ────────────────────────────────────────────────────────
    # DNA composite replaces the old raw skill+career+yoe combination.
    # Verified skill score is a multiplier on skill alignment.
    # Legacy availability and behavioral kept as-is.

    # Skill score boosted by verification evidence
    verified_skill = skill_score * (0.7 + 0.3 * vscore)

    final_score = (
        0.35 * dna_score           +   # DNA composite (technical, execution, trust, risk...)
        0.25 * verified_skill      +   # Skill alignment × verification
        0.14 * yoe_score           +   # Experience band
        0.13 * behavioral_score    +   # Redrob platform signals
        0.08 * availability_score  +   # Notice + location
        0.03 * dna.get("professional", 0) +  # Leadership/startup/complexity
        0.02 * (sigs.get("profile_completeness_score", 50) / 100.0)
    )

    # Reachability multiplier
    if resp_rate < 0.15 and days_inactive > 150:
        final_score *= 0.6

    # Risk penalty from DNA (high risk = low risk DNA score)
    if dna.get("risk", 1.0) < 0.40:
        final_score *= (0.8 + 0.2 * dna["risk"])

    final_score = round(final_score, 6)

    # ── 8. CONFIDENCE ────────────────────────────────────────────────────────
    base_result = {
        "final_score":        final_score,
        "is_honeypot":        False,
        "honeypot_reason":    "",
        "skill_score":        round(skill_score, 4),
        "verified_skill_score": round(verified_skill, 4),
        "yoe_score":          round(yoe_score, 4),
        "career_score":       round(dna.get("execution", 0), 4),
        "behavioral_score":   round(behavioral_score, 4),
        "availability_score": round(availability_score, 4),
        "dna":                dna,
        "dna_score":          round(dna_score, 4),
        "skill_verification": skill_verification,
        "matched_must":       matched_must,
        "matched_strong":     matched_strong[:6],
        "top_verified_skills": skill_verification.get("top_verified_skills", []),
        "notice_days":        notice,
        "location":           profile.get("location", ""),
        "yoe":                yoe,
        "resp_rate":          resp_rate,
        "last_active":        last_active_str,
        "open_to_work":       bool(sigs.get("open_to_work_flag")),
        "avg_tenure_months":  round(avg_tenure, 1),
        "product_months":     product_months,
        "title":              profile.get("current_title", ""),
        "company":            profile.get("current_company", ""),
    }

    confidence = compute_confidence(candidate, base_result, dna, skill_verification)
    base_result.update(confidence)
    return base_result


def _honeypot_result(reason: str) -> dict:
    return {
        "final_score": 0.001, "is_honeypot": True, "honeypot_reason": reason,
        "skill_score": 0, "verified_skill_score": 0, "yoe_score": 0,
        "career_score": 0, "behavioral_score": 0, "availability_score": 0,
        "dna": {}, "dna_score": 0, "skill_verification": {},
        "matched_must": [], "matched_strong": [], "top_verified_skills": [],
        "confidence_score": 0, "confidence_label": "low", "confidence_reason": "Honeypot detected",
        "notice_days": 0, "location": "", "yoe": 0, "resp_rate": 0,
        "last_active": "", "open_to_work": False, "avg_tenure_months": 0,
        "product_months": 0, "title": "", "company": "",
    }


def _disqualified(score: float, reason: str, candidate: dict) -> dict:
    profile = candidate.get("profile", {})
    return {
        "final_score": score, "is_honeypot": False, "honeypot_reason": "",
        "disqualify_reason": reason,
        "skill_score": 0, "verified_skill_score": 0, "yoe_score": 0,
        "career_score": 0, "behavioral_score": 0, "availability_score": 0,
        "dna": {}, "dna_score": 0, "skill_verification": {},
        "matched_must": [], "matched_strong": [], "top_verified_skills": [],
        "confidence_score": 0, "confidence_label": "low", "confidence_reason": f"Disqualified: {reason}",
        "notice_days": 0, "location": profile.get("location", ""),
        "yoe": profile.get("years_of_experience", 0),
        "resp_rate": 0, "last_active": "", "open_to_work": False,
        "avg_tenure_months": 0, "product_months": 0,
        "title": profile.get("current_title", ""),
        "company": profile.get("current_company", ""),
    }
