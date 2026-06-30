# Redrob Candidate Ranking Engine

Ranks the top 100 candidates from `candidates.jsonl` for the **Senior AI Engineer (Founding Team)** role at Redrob AI.

## Reproduce submission

```bash
python rank.py --candidates ./candidates.jsonl --out ./outputs/submission.csv
```

Runtime: ~30 seconds on CPU with 16 GB RAM. Passes `validate_submission.py` cleanly.

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/candidate-ranking-engine
cd candidate-ranking-engine
pip install -r requirements.txt
```

Python 3.9+ required. No GPU. No internet access during ranking.

## Run sandbox demo

```bash
streamlit run streamlit_app.py
```

Use the **Local file path** tab for the full `candidates.jsonl` (465 MB).  
Use the **Upload** tab for `sample_candidates.json` or any subset.

## Project structure

```
candidate-ranking-engine/
├── rank.py                        # Main CLI — run this to produce submission.csv
├── streamlit_app.py               # Sandbox demo UI
├── smoke_test.py                  # Quick sanity check (run after any code change)
├── requirements.txt
├── submission_metadata.yaml       # Fill in team details before submitting
├── .streamlit/
│   └── config.toml                # Raises upload limit to 500 MB
├── engines/
│   ├── jd_intelligence.py         # All JD-derived constants and thresholds
│   ├── scorer.py                  # Core scoring engine (integrates all engines)
│   ├── honeypot.py                # Honeypot detection + soft anomaly checks
│   ├── talent_dna.py              # 8-dimension candidate DNA representation
│   ├── skill_truth.py             # Skill verification against evidence sources
│   ├── confidence.py              # Per-candidate recommendation confidence
│   └── reasoning.py              # Evidence-backed reasoning generator
└── outputs/
    └── submission.csv             # Generated output (gitignored)
```

## Architecture — Talent DNA

Every candidate is converted into an 8-dimension DNA vector before scoring:

| Dimension | What it measures |
|-----------|-----------------|
| Technical | Skill depth and breadth vs JD must-haves + platform assessments |
| Execution | Product company time, tenure stability, pre-LLM retrieval signal |
| Trust | Recruiter engagement, platform verifications, offer acceptance |
| Risk | Inverse of anomaly signals — job-hopping, buzzword stuffing, salary mismatch |
| Professional | Leadership verbs, startup experience, cognitive complexity |
| Adaptability | Industry diversity, tech transitions, skill recency |
| Innovation | GitHub activity, assessment scores, skill breadth |
| Communication | Headline quality, summary depth, endorsements, connections |

## Scoring weights

| Component | Weight | Engine |
|-----------|--------|--------|
| DNA composite | 35% | `talent_dna.py` |
| Verified skill alignment | 25% | `skill_truth.py` × `scorer.py` |
| Years of experience | 14% | `scorer.py` |
| Behavioral signals | 13% | `scorer.py` |
| Availability | 8% | `scorer.py` |
| Professional DNA | 3% | `talent_dna.py` |
| Profile completeness | 2% | `scorer.py` |

## Honeypot + anomaly detection

**Layer 1 — Hard disqualification** (score → 0.001):
- Skill `duration_months` exceeds total experience
- Job duration exceeds calendar time elapsed
- Expert skills with zero months usage
- Career sum wildly exceeds stated experience
- Impossible signup recency

**Layer 2 — Soft risk signals** (feeds DNA risk dimension):
- Buzzword stuffing (many JD keywords, near-zero durations)
- Identical durations across all skills (copy-paste)
- Templated career descriptions (>70% word overlap)
- Proficiency inflation (>85% skills claimed expert/advanced)
- Salary-experience mismatch

## Skill Truth Verification

Validates claimed skills against 5 evidence sources:
1. Platform assessment score (strongest signal)
2. Career description mentions with duration
3. Skill endorsements
4. Certification references
5. Proficiency-duration consistency

## Decision Confidence

Every top-100 candidate receives a confidence label (high / medium / low) across 7 checks:
profile completeness, career description richness, skill verification quality,
platform verifications, DNA consistency, recruiter engagement, and score-to-evidence alignment.

## Compute constraints

| Constraint | Limit | Actual |
|------------|-------|--------|
| Runtime | ≤ 5 min | ~30s for 100K |
| Memory | ≤ 16 GB | < 500 MB |
| Compute | CPU only | ✅ |
| Network | Off | ✅ |

## Validate before submitting

```bash
python validate_submission.py outputs/submission.csv
```
