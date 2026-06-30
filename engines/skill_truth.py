"""
Skill Truth Verification Engine
Validates claimed skills against available evidence.
Does NOT disqualify — produces a verification score that boosts
well-evidenced skills and modestly discounts unverified claims.

Evidence sources (in order of weight):
  1. Platform assessment score for that skill
  2. Career description mentions with duration
  3. Endorsements on the skill
  4. Certifications referencing the skill
  5. Proficiency level consistency with duration

Output: verified_skill_score (0.0–1.0) and a per-skill evidence dict.
"""

from engines.jd_intelligence import MUST_HAVE_SKILLS, STRONG_POSITIVE_SKILLS

_MUST_SET   = frozenset(MUST_HAVE_SKILLS)
_STRONG_SET = frozenset(STRONG_POSITIVE_SKILLS)

# Skill → assessment label mappings (how Redrob names assessments)
_ASSESS_ALIASES = {
    "nlp":              ["NLP", "Natural Language Processing"],
    "machine learning": ["Machine Learning", "ML"],
    "fine-tuning":      ["Fine-tuning LLMs", "LLM Fine-tuning"],
    "pytorch":          ["PyTorch", "Deep Learning"],
    "tensorflow":       ["TensorFlow", "Deep Learning"],
    "retrieval":        ["Information Retrieval", "Search"],
    "recommendation":   ["Recommendation Systems"],
    "ranking":          ["Learning to Rank", "Ranking"],
}


def verify_skills(candidate: dict) -> dict:
    """
    Returns:
      verified_skill_score  — float 0.0–1.0 (overall evidence quality)
      skill_evidence        — dict of {skill_name: evidence_level}
      top_verified_skills   — list of skill names with strong evidence
    """
    skills  = candidate.get("skills", [])
    career  = candidate.get("career_history", [])
    sigs    = candidate.get("redrob_signals", {})
    certs   = candidate.get("certifications", [])

    career_text = " ".join(j.get("description", "").lower() for j in career)
    assess_scores = sigs.get("skill_assessment_scores", {})
    cert_names = " ".join(str(c).lower() for c in certs)

    skill_evidence = {}
    total_score = 0.0
    jd_relevant_count = 0

    for s in skills:
        sname     = s["name"]
        sname_low = sname.lower()
        dur       = s.get("duration_months", 0)
        endorse   = s.get("endorsements", 0)
        prof      = s.get("proficiency", "beginner")

        is_relevant = (
            any(kw in sname_low for kw in _MUST_SET) or
            any(kw in sname_low for kw in _STRONG_SET)
        )
        if not is_relevant:
            continue

        jd_relevant_count += 1
        evidence_score = 0.0

        # Evidence 1: Platform assessment (strongest)
        assess_val = _find_assessment(sname_low, assess_scores)
        if assess_val is not None:
            evidence_score += 0.40 * (assess_val / 100.0)

        # Evidence 2: Career description mentions with duration
        mention_bonus = 0.0
        if sname_low in career_text or any(kw in career_text for kw in sname_low.split()):
            if dur >= 24:
                mention_bonus = 0.35
            elif dur >= 12:
                mention_bonus = 0.25
            elif dur > 0:
                mention_bonus = 0.15
            else:
                mention_bonus = 0.05  # mentioned but no duration
        evidence_score += mention_bonus

        # Evidence 3: Endorsements
        endorse_score = min(endorse / 10.0, 1.0) * 0.15
        evidence_score += endorse_score

        # Evidence 4: Certification references
        if sname_low in cert_names or any(kw in cert_names for kw in sname_low.split()):
            evidence_score += 0.10

        # Evidence 5: Proficiency vs duration consistency
        prof_ok = _proficiency_consistent(prof, dur)
        if prof_ok:
            evidence_score = min(evidence_score + 0.05, 1.0)
        else:
            evidence_score *= 0.75  # slight discount for inconsistent claims

        skill_evidence[sname] = round(min(evidence_score, 1.0), 3)
        total_score += skill_evidence[sname]

    if jd_relevant_count == 0:
        return {
            "verified_skill_score": 0.2,
            "skill_evidence": {},
            "top_verified_skills": [],
        }

    verified_skill_score = min(total_score / max(jd_relevant_count, 1), 1.0)

    # Top verified: skills with evidence > 0.5, sorted by evidence
    top_verified = sorted(
        [sname for sname, ev in skill_evidence.items() if ev >= 0.50],
        key=lambda x: skill_evidence[x],
        reverse=True,
    )[:4]

    return {
        "verified_skill_score": round(verified_skill_score, 4),
        "skill_evidence":        skill_evidence,
        "top_verified_skills":   top_verified,
    }


def _find_assessment(skill_lower: str, assess_scores: dict) -> float | None:
    """Match a skill name to its platform assessment score."""
    # Direct match
    for label, score in assess_scores.items():
        if skill_lower in label.lower() or label.lower() in skill_lower:
            return float(score)
    # Alias match
    for skill_kw, aliases in _ASSESS_ALIASES.items():
        if skill_kw in skill_lower:
            for alias in aliases:
                if alias in assess_scores:
                    return float(assess_scores[alias])
    return None


def _proficiency_consistent(proficiency: str, duration_months: int) -> bool:
    """Check if stated proficiency is plausible given duration."""
    thresholds = {
        "beginner":     0,
        "intermediate": 6,
        "advanced":     18,
        "expert":       36,
    }
    required = thresholds.get(proficiency.lower(), 0)
    return duration_months >= required
