"""
Decision Confidence Engine
Estimates how confident the system is in its recommendation for each candidate.
This is NOT the same as the score — a candidate can score 0.92 with 60% confidence
(sparse signals) or 0.78 with 95% confidence (rich, consistent evidence).

Confidence = f(signal_count, signal_consistency, data_completeness)

Output added to the result dict:
  confidence_score  — float 0.0–1.0
  confidence_label  — "high" | "medium" | "low"
  confidence_reason — short string explaining the confidence level
"""


def compute_confidence(
    candidate: dict,
    score_result: dict,
    dna: dict,
    skill_verification: dict,
) -> dict:
    """
    Returns confidence dict with score, label, and reason.
    """
    profile  = candidate.get("profile", {})
    sigs     = candidate.get("redrob_signals", {})
    career   = candidate.get("career_history", [])
    skills   = candidate.get("skills", [])

    signals_available  = 0
    signals_consistent = 0
    confidence_issues  = []
    confidence_boosts  = []

    # ── Signal 1: Profile completeness ───────────────────────────────────────
    completeness = sigs.get("profile_completeness_score", 50)
    signals_available += 1
    if completeness >= 80:
        signals_consistent += 1
        confidence_boosts.append("complete profile")
    elif completeness < 50:
        confidence_issues.append("incomplete profile")

    # ── Signal 2: Career evidence richness ───────────────────────────────────
    signals_available += 1
    desc_lengths = [len(j.get("description", "").split()) for j in career]
    avg_desc_words = sum(desc_lengths) / len(desc_lengths) if desc_lengths else 0
    if avg_desc_words >= 30:
        signals_consistent += 1
        confidence_boosts.append("detailed career descriptions")
    elif avg_desc_words < 10:
        confidence_issues.append("sparse career descriptions")

    # ── Signal 3: Skill verification quality ────────────────────────────────
    signals_available += 1
    vscore = skill_verification.get("verified_skill_score", 0)
    if vscore >= 0.6:
        signals_consistent += 1
        confidence_boosts.append("verified skill evidence")
    elif vscore < 0.3:
        confidence_issues.append("limited skill verification")

    # ── Signal 4: Behavioral signal richness ─────────────────────────────────
    signals_available += 1
    has_github   = sigs.get("github_activity_score", -1) >= 0
    has_assess   = bool(sigs.get("skill_assessment_scores"))
    has_linkedin = bool(sigs.get("linkedin_connected"))
    platform_signals = sum([has_github, has_assess, has_linkedin])
    if platform_signals >= 2:
        signals_consistent += 1
        confidence_boosts.append("multiple platform verifications")
    elif platform_signals == 0:
        confidence_issues.append("no platform verifications")

    # ── Signal 5: DNA consistency ─────────────────────────────────────────────
    signals_available += 1
    dna_vals = [dna.get(k, 0) for k in ["technical", "execution", "trust"]]
    dna_min, dna_max = min(dna_vals), max(dna_vals)
    dna_spread = dna_max - dna_min
    if dna_spread < 0.30:
        signals_consistent += 1
        confidence_boosts.append("consistent DNA profile")
    elif dna_spread > 0.60:
        confidence_issues.append("inconsistent DNA signals")

    # ── Signal 6: Recruiter engagement history ───────────────────────────────
    signals_available += 1
    resp_rate = float(sigs.get("recruiter_response_rate", 0))
    applications = sigs.get("applications_submitted_30d", 0)
    if resp_rate >= 0.5 and applications > 0:
        signals_consistent += 1
        confidence_boosts.append("active and responsive")
    elif resp_rate < 0.15:
        confidence_issues.append("low recruiter response rate")

    # ── Signal 7: Score magnitude vs data sparsity ───────────────────────────
    signals_available += 1
    final_score = score_result.get("final_score", 0)
    matched_must = len(score_result.get("matched_must", []))
    if final_score >= 0.70 and matched_must >= 2:
        signals_consistent += 1
        confidence_boosts.append("strong score with direct JD evidence")
    elif final_score >= 0.70 and matched_must == 0:
        confidence_issues.append("high score but no must-have skill matches")

    # ── Compute confidence score ─────────────────────────────────────────────
    raw_confidence = signals_consistent / signals_available if signals_available > 0 else 0.5

    # Bonus: many boosts = extra confidence
    if len(confidence_boosts) >= 4:
        raw_confidence = min(raw_confidence + 0.08, 1.0)

    # Penalty: critical issues
    if len(confidence_issues) >= 3:
        raw_confidence = max(raw_confidence - 0.15, 0.0)

    confidence_score = round(raw_confidence, 3)

    # ── Label ─────────────────────────────────────────────────────────────────
    if confidence_score >= 0.72:
        label = "high"
    elif confidence_score >= 0.45:
        label = "medium"
    else:
        label = "low"

    # ── Reason ───────────────────────────────────────────────────────────────
    if confidence_issues:
        reason = f"Confidence {label} — concern: {confidence_issues[0]}"
    elif confidence_boosts:
        reason = f"Confidence {label} — supported by {confidence_boosts[0]}"
    else:
        reason = f"Confidence {label} — moderate signal coverage"

    return {
        "confidence_score": confidence_score,
        "confidence_label": label,
        "confidence_reason": reason,
        "confidence_boosts": confidence_boosts,
        "confidence_issues": confidence_issues,
    }
