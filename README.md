# Redrob Candidate Ranking Engine

An explainable, recruiter-centric AI ranking engine that identifies the **Top 100 candidates** for the **Senior AI Engineer (Founding Team)** role at Redrob AI from over **100,000 candidate profiles**.

The system goes beyond keyword matching by combining **Talent DNA modeling, verified skill intelligence, behavioral analysis, anomaly detection, and evidence-backed reasoning** to produce recruiter-ready rankings.

---

# Live Sandbox Demo

🌐 **Demo:** https://candidaterankengine.streamlit.app/

The Streamlit application allows recruiters to:

- Upload candidate datasets
- Paste or upload Job Descriptions
- Generate Top-100 ranked candidates
- View evidence-backed reasoning
- Download the final ranked CSV
- Inspect candidate scores and Talent DNA

---

# Repository Setup

```bash
git clone https://github.com/Gokul-S2305/Candidate_rank_engine
cd Candidate_rank_engine
pip install -r requirements.txt
```

**Requirements**

- Python 3.9+
- CPU only
- No GPU required
- No internet required during ranking

---

# Generate Submission

```bash
python rank.py --candidates ./candidates.jsonl --out ./outputs/submission.csv
```

Runtime:

- ~30 seconds for 100K candidates
- Memory usage <500 MB
- Fully deterministic

---

# Sandbox Demo

Run locally:

```bash
streamlit run streamlit_app.py
```

Supports

- Full `candidates.jsonl` dataset (465 MB)
- Sample candidate subsets
- Local file upload
- Job Description upload/paste
- Downloadable ranked output

---

# Project Structure

```
candidate-ranking-engine/
│
├── rank.py
├── streamlit_app.py
├── smoke_test.py
├── requirements.txt
├── README.md
├── submission_metadata.yaml
│
├── .streamlit/
│   └── config.toml
│
├── engines/
│   ├── jd_intelligence.py
│   ├── scorer.py
│   ├── talent_dna.py
│   ├── skill_truth.py
│   ├── honeypot.py
│   ├── confidence.py
│   └── reasoning.py
│
└── outputs/
    └── submission.csv
```

---

# System Architecture

```
Candidate Dataset
        │
        ▼
JD Intelligence Engine
        │
        ▼
Talent DNA Generator
        │
        ▼
Skill Truth Verification
        │
        ▼
Behavioral Intelligence
        │
        ▼
Honeypot & Risk Detection
        │
        ▼
Confidence Engine
        │
        ▼
Composite Scoring Engine
        │
        ▼
Evidence-backed Reasoning
        │
        ▼
Top-100 Candidate Ranking
```

---

# Talent DNA Architecture

Every candidate is transformed into an **8-dimensional Talent DNA vector** before ranking.

| Dimension | Description |
|------------|-------------|
| **Technical DNA** | Technical skill depth, breadth, production relevance, platform assessments |
| **Execution DNA** | Product-company experience, tenure stability, delivery maturity |
| **Trust DNA** | Recruiter engagement, profile verification, offer acceptance |
| **Risk DNA** | Job hopping, buzzword stuffing, salary mismatch, anomaly detection |
| **Professional DNA** | Leadership, ownership, startup mindset, cognitive complexity |
| **Adaptability DNA** | Technology transitions, learning ability, industry diversity |
| **Innovation DNA** | GitHub activity, certifications, assessments, research signals |
| **Communication DNA** | Profile quality, headline, summary richness, endorsements |

---

# Scoring Framework

| Component | Weight |
|------------|--------|
| Talent DNA Composite | 35% |
| Verified Skill Alignment | 25% |
| Experience Intelligence | 14% |
| Behavioral Intelligence | 13% |
| Availability | 8% |
| Professional DNA | 3% |
| Profile Completeness | 2% |

Final score is normalized to produce deterministic rankings.

---

# JD Intelligence

The Job Description is converted into structured intelligence including

- Must-have skills
- Preferred skills
- Experience requirements
- Startup preference
- Product-company preference
- Notice period preference
- Location preference
- Behavioral expectations

This enables semantic matching beyond keyword overlap.

---

# Skill Truth Verification

Instead of trusting self-declared skills, every important skill is validated using multiple evidence sources.

Evidence sources include

- Platform assessments
- Career descriptions
- Skill durations
- Certifications
- Endorsements
- Proficiency consistency

This produces a confidence score for every claimed skill.

---

# Honeypot & Risk Detection

The engine performs two levels of anomaly detection.

## Hard Validation

Automatically rejects profiles with impossible data such as

- Skill duration exceeding career duration
- Impossible employment timelines
- Expert skills with zero experience
- Unrealistic total experience
- Invalid account activity

## Soft Risk Detection

Detects suspicious recruiter patterns including

- Buzzword stuffing
- Copy-pasted descriptions
- Artificial skill inflation
- Salary-experience mismatch
- Low evidence consistency

Risk contributes to the final Talent DNA rather than immediately disqualifying candidates.

---

# Confidence Engine

Each recommendation receives a confidence score based on

- Profile completeness
- Skill verification
- Platform verification
- Recruiter engagement
- DNA consistency
- Evidence richness
- Score reliability

Confidence labels

- High
- Medium
- Low

This provides transparency for recruiters.

---

# Explainable AI

Every ranked candidate includes recruiter-friendly reasoning explaining

- Why the candidate matches the role
- Evidence supporting each recommendation
- Product-company relevance
- Verified technical strengths
- Recruiter signals
- Any notable concerns

No reasoning is generated without supporting evidence from the profile.

---

# Performance

| Constraint | Requirement | Achieved |
|------------|-------------|----------|
| Runtime | ≤ 5 min | ~30 sec |
| Memory | ≤16 GB | <500 MB |
| CPU Only | Yes | ✅ |
| Offline Ranking | Yes | ✅ |
| Deterministic | Yes | ✅ |

---

# Output

The engine generates a valid submission file:

```
candidate_id,rank,score,reasoning
```

Fully compatible with the official evaluation pipeline.

---

# Validate Submission

```bash
python validate_submission.py outputs/submission.csv
```

---

# Key Features

- Explainable AI ranking
- Talent DNA representation
- Recruiter-centric scoring
- Skill Truth Verification
- Honeypot detection
- Confidence estimation
- Evidence-backed reasoning
- Modular architecture
- Deterministic execution
- Streamlit sandbox demo
- Offline CPU execution
- Official submission compatible
