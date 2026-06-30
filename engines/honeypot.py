"""
Risk Intelligence + Honeypot Detector v2
Two-layer defence:
  Layer 1 — Honeypot: hard impossibilities → score 0.001 (never reaches top 100)
  Layer 2 — Anomaly: soft risk signals → fed into DNA risk dimension

Honeypot checks (5, unchanged from v1 — conservative by design):
  1. Skill duration > total experience
  2. Job duration > calendar time elapsed
  3. Expert skills with zero months usage
  4. Career sum >> stated experience
  5. Impossible signup recency

New anomaly checks (soft, used by DNA risk engine):
  6. Buzzword stuffing (skill list has >80% must/strong keywords with no depth)
  7. All skills at identical duration (copy-paste signal)
  8. Career descriptions are suspiciously identical (templated)
  9. Proficiency inflation (all skills = expert or advanced)
  10. Salary wildly misaligned with experience band
"""

from engines.jd_intelligence import (
    MUST_HAVE_SKILLS, STRONG_POSITIVE_SKILLS, REFERENCE_DATE,
    YOE_IDEAL_MIN, YOE_IDEAL_MAX,
)

_MUST_SET   = frozenset(MUST_HAVE_SKILLS)
_STRONG_SET = frozenset(STRONG_POSITIVE_SKILLS)


def detect_honeypot(candidate: dict) -> tuple[bool, str]:
    """
    Layer 1: hard impossibilities only.
    Returns (is_honeypot, reason).
    """
    profile = candidate.get("profile", {})
    career  = candidate.get("career_history", [])
    skills  = candidate.get("skills", [])
    sigs    = candidate.get("redrob_signals", {})

    yoe = profile.get("years_of_experience", 0)
    total_exp_months = yoe * 12

    # Check 1: skill duration > total experience
    for s in skills:
        dur = s.get("duration_months", 0)
        if dur > total_exp_months + 18:
            return True, (
                f"skill '{s['name']}' used {dur}mo but total exp "
                f"only {total_exp_months:.0f}mo"
            )

    # Check 2: job duration > calendar time elapsed
    for job in career:
        start_str  = job.get("start_date", "")
        dur_months = job.get("duration_months", 0)
        if start_str and not job.get("is_current", False):
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
                actual   = (
                    (REFERENCE_DATE.year  - start_dt.year)  * 12 +
                    (REFERENCE_DATE.month - start_dt.month)
                )
                if dur_months > actual + 6:
                    return True, (
                        f"job duration {dur_months}mo claimed "
                        f"but only {actual}mo elapsed"
                    )
            except ValueError:
                pass

    # Check 3: expert skills with zero months
    expert_zero = sum(
        1 for s in skills
        if s.get("proficiency") == "expert" and s.get("duration_months", 0) == 0
    )
    if expert_zero >= 3:
        return True, f"{expert_zero} expert-level skills with 0 months duration"

    # Check 4: career sum >> stated experience
    sum_career = sum(j.get("duration_months", 0) for j in career)
    if sum_career > total_exp_months * 1.5 + 24:
        return True, (
            f"sum of job durations {sum_career}mo >> "
            f"stated exp {total_exp_months:.0f}mo"
        )

    # Check 5: impossible signup recency
    signup_str = sigs.get("signup_date", "")
    if signup_str:
        try:
            from datetime import datetime
            signup_dt = datetime.strptime(signup_str, "%Y-%m-%d").date()
            months_on = (
                (REFERENCE_DATE.year  - signup_dt.year)  * 12 +
                (REFERENCE_DATE.month - signup_dt.month)
            )
            if yoe > 20 and months_on < 3:
                return True, (
                    f"claimed {yoe}yr exp but signup only {months_on}mo ago"
                )
        except ValueError:
            pass

    return False, ""


def detect_anomalies(candidate: dict) -> dict:
    """
    Layer 2: soft risk signals. Returns anomaly scores 0.0–1.0
    (higher = more anomalous). Used by talent_dna.py risk dimension.
    """
    profile = candidate.get("profile", {})
    career  = candidate.get("career_history", [])
    skills  = candidate.get("skills", [])
    sigs    = candidate.get("redrob_signals", {})

    anomaly_score  = 0.0
    anomaly_flags  = []

    # Anomaly 6: buzzword stuffing
    # Many JD keywords listed but zero/low combined duration_months
    jd_kw_skills = [
        s for s in skills
        if any(kw in s["name"].lower() for kw in _MUST_SET | _STRONG_SET)
    ]
    if jd_kw_skills:
        total_dur = sum(s.get("duration_months", 0) for s in jd_kw_skills)
        avg_dur   = total_dur / len(jd_kw_skills)
        if len(jd_kw_skills) >= 6 and avg_dur < 6:
            anomaly_score += 0.30
            anomaly_flags.append("buzzword stuffing: many JD keywords, near-zero duration")

    # Anomaly 7: identical durations (copy-paste)
    if len(skills) >= 5:
        durations = [s.get("duration_months", 0) for s in skills]
        unique_durs = len(set(durations))
        if unique_durs <= 2 and len(durations) >= 8:
            anomaly_score += 0.20
            anomaly_flags.append("all skills share identical duration values")

    # Anomaly 8: templated career descriptions
    if len(career) >= 2:
        descs = [j.get("description", "").strip().lower() for j in career if j.get("description")]
        if len(descs) >= 2:
            # Simple word-overlap similarity between first two descriptions
            words_a = set(descs[0].split())
            words_b = set(descs[1].split())
            if words_a and words_b:
                overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
                if overlap > 0.70:
                    anomaly_score += 0.25
                    anomaly_flags.append(
                        f"career descriptions {overlap:.0%} similar — possible templating"
                    )

    # Anomaly 9: proficiency inflation
    if skills:
        high_prof = sum(
            1 for s in skills
            if s.get("proficiency", "") in ("expert", "advanced")
        )
        if high_prof / len(skills) > 0.85 and len(skills) >= 6:
            anomaly_score += 0.15
            anomaly_flags.append(
                f"{high_prof}/{len(skills)} skills claimed expert/advanced"
            )

    # Anomaly 10: salary-experience mismatch
    sal = sigs.get("expected_salary_range_inr_lpa", {})
    yoe = profile.get("years_of_experience", 0)
    if sal:
        sal_min = sal.get("min", 0)
        # Entry-level experience expecting senior salary = likely mismatch
        if yoe < 3 and sal_min > 40:
            anomaly_score += 0.15
            anomaly_flags.append(
                f"salary floor ₹{sal_min}L misaligned with {yoe}yr experience"
            )
        # Experienced candidate expecting very low salary = suspicious
        elif yoe > 8 and sal_min < 10:
            anomaly_score += 0.10
            anomaly_flags.append(
                f"salary floor ₹{sal_min}L unusually low for {yoe}yr experience"
            )

    return {
        "anomaly_score": round(min(anomaly_score, 1.0), 3),
        "anomaly_flags": anomaly_flags,
    }


def honeypot_score_penalty(is_honeypot: bool) -> float:
    return 0.001 if is_honeypot else 1.0
