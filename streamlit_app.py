import csv
import io
import json
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from engines.scorer import score_candidate
from engines.reasoning import generate_reasoning

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Candidate Ranker — Redrob",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .stMetric label { font-size: 0.78rem; color: #888; }
    .stMetric [data-testid="stMetricValue"] { font-size: 1.4rem; font-weight: 600; }
    .candidate-card {
        background: #fafafa;
        color: #111111;
        border: 1px solid #eee;
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 12px;
    }
    .rank-badge {
        display: inline-block;
        background: #1a1a2e;
        color: white;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .score-pill {
        display: inline-block;
        background: #e8f5e9;
        color: #2e7d32;
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-left: 8px;
    }
    .tag {
        display: inline-block;
        background: #f0f4ff;
        color: #3949ab;
        border-radius: 4px;
        padding: 1px 8px;
        font-size: 0.72rem;
        margin: 2px 2px 0 0;
    }
    .concern-tag {
        display: inline-block;
        background: #fff3e0;
        color: #e65100;
        border-radius: 4px;
        padding: 1px 8px;
        font-size: 0.72rem;
        margin: 2px 2px 0 0;
    }
    .reasoning-text {
        font-size: 0.85rem;
        color: #444;
        line-height: 1.6;
        margin-top: 8px;
        border-left: 3px solid #e0e0e0;
        padding-left: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ── JD loader ─────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_jd_docx(docx_bytes: bytes) -> dict:
    from docx import Document
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(docx_bytes)
        tmp_path = tmp.name
    doc = Document(tmp_path)
    os.unlink(tmp_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    full_text = "\n".join(paragraphs)
    title = company = location = experience = ""
    for p in paragraphs[:10]:
        if p.startswith("Job Description:"):
            title = p.replace("Job Description:", "").strip()
        elif p.startswith("Company:"):
            company = p.replace("Company:", "").strip()
        elif p.startswith("Location:"):
            location = p.replace("Location:", "").strip()
        elif p.startswith("Experience Required:"):
            experience = p.replace("Experience Required:", "").strip()
    return {
        "title": title or "Senior AI Engineer",
        "company": company or "Redrob AI",
        "location": location,
        "experience": experience,
        "full_text": full_text,
    }


@st.cache_data(show_spinner=False)
def load_candidates_from_bytes(raw_bytes: bytes, filename: str) -> list:
    raw = raw_bytes.decode("utf-8")
    if filename.endswith(".jsonl") or (raw.lstrip().startswith("{") and "\n{" in raw[:500]):
        return [json.loads(line) for line in raw.splitlines() if line.strip()]
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, list) else [parsed]


@st.cache_data(show_spinner=False)
def load_candidates_from_path(file_path: str) -> list:
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    candidates = []
    if p.suffix == ".jsonl":
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    candidates.append(json.loads(line))
    else:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            candidates = data if isinstance(data, list) else [data]
    return candidates


@st.cache_data(show_spinner=False)
def run_scoring(candidate_ids_and_json: str) -> list:
    """Cache scoring results keyed by a fingerprint string."""
    # This is called with a stable key; actual candidates passed separately
    pass  # see run_scoring_real below


def run_scoring_real(candidates: list) -> list:
    scored = []
    for c in candidates:
        result = score_candidate(c)
        scored.append((c["candidate_id"], result["final_score"], result, c))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("## Candidate Ranking")
st.markdown("Upload a job description and provide a candidates file to rank the best matches.")
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# JD UPLOAD
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("**Job Description (.docx)**")
jd_file = st.file_uploader(
    "job_description",
    type=["docx"],
    label_visibility="collapsed",
    key="jd_upload",
)

if not jd_file:
    st.info("Upload the job description .docx file to continue.")
    st.stop()

jd_info = load_jd_docx(jd_file.read())

# JD summary strip
j1, j2, j3, j4 = st.columns(4)
j1.markdown(f"**Role**  \n{jd_info['title']}")
j2.markdown(f"**Company**  \n{jd_info['company']}")
j3.markdown(f"**Location**  \n{jd_info['location'] or '—'}")
j4.markdown(f"**Experience**  \n{jd_info['experience'] or '—'}")

with st.expander("View full job description"):
    st.text(jd_info["full_text"])

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# CANDIDATES — two modes
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("**Candidates**")
st.caption(
    "The full `candidates.jsonl` is 465 MB. "
    "Use **Local path** if running on your own machine. "
    "Use **Upload** for the sample file or any subset."
)

tab_path, tab_upload = st.tabs(["Local file path", "Upload file"])

candidates = None
load_error = None

with tab_path:
    st.markdown("Enter the absolute path to your `candidates.jsonl` or `candidates.json` file.")
    file_path_input = st.text_input(
        "File path",
        placeholder="/path/to/candidates.jsonl",
        label_visibility="collapsed",
    )
    if file_path_input:
        if st.button("Load from path", use_container_width=False):
            try:
                with st.spinner("Loading…"):
                    candidates = load_candidates_from_path(file_path_input.strip())
                st.session_state["candidates"] = candidates
                st.session_state["cands_source"] = Path(file_path_input.strip()).name
            except Exception as e:
                load_error = str(e)

with tab_upload:
    st.caption("Max upload size: 500 MB (set in `.streamlit/config.toml`). Use for `sample_candidates.json` or any subset.")
    cands_file = st.file_uploader(
        "candidates_upload",
        type=["json", "jsonl"],
        label_visibility="collapsed",
        key="cands_upload",
    )
    if cands_file:
        try:
            with st.spinner("Reading…"):
                candidates = load_candidates_from_bytes(cands_file.read(), cands_file.name)
            st.session_state["candidates"] = candidates
            st.session_state["cands_source"] = cands_file.name
        except Exception as e:
            load_error = str(e)

# Restore from session if available (prevents re-load on widget interaction)
if candidates is None and "candidates" in st.session_state:
    candidates = st.session_state["candidates"]

if load_error:
    st.error(f"Could not load candidates: {load_error}")
    st.stop()

if candidates is None:
    st.info("Provide a candidates file above to continue.")
    st.stop()

source_name = st.session_state.get("cands_source", "candidates")
st.caption(f"✓ {len(candidates):,} candidates loaded from `{source_name}`")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# RANK
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner(f"Ranking {len(candidates):,} candidates…"):
    t0 = time.time()
    scored = run_scoring_real(candidates)
    elapsed = time.time() - t0

top_n = min(100, len(scored))

# Summary metrics
honeypots    = sum(1 for _, _, r, _ in scored if r.get("is_honeypot"))
disqualified = sum(1 for _, s, _, _ in scored if 0 < s <= 0.02)
in_contention = sum(1 for _, s, _, _ in scored if s > 0.02)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Candidates", f"{len(candidates):,}")
m2.metric("In contention", f"{in_contention:,}")
m3.metric("Disqualified", f"{disqualified:,}")
m4.metric("Flagged profiles", f"{honeypots}")
m5.metric("Ranked in", f"{elapsed:.1f}s")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# BUILD ROWS
# ─────────────────────────────────────────────────────────────────────────────
rows = []
for rank_idx, (cid, score, score_result, candidate) in enumerate(scored[:top_n], start=1):
    reasoning = generate_reasoning(candidate, score_result, rank_idx)
    profile = candidate.get("profile", {})
    sigs = candidate.get("redrob_signals", {})
    rows.append({
        "rank": rank_idx,
        "candidate_id": cid,
        "score": round(score, 4),
        "title": profile.get("current_title", ""),
        "company": profile.get("current_company", ""),
        "yoe": profile.get("years_of_experience", 0),
        "location": profile.get("location", ""),
        "notice": sigs.get("notice_period_days", "-"),
        "resp_rate": sigs.get("recruiter_response_rate", 0),
        "open_to_work": sigs.get("open_to_work_flag", False),
        "matched_must": score_result.get("matched_must", []),
        "matched_strong": score_result.get("matched_strong", [])[:3],
        "reasoning": reasoning,
    })

# ─────────────────────────────────────────────────────────────────────────────
# VIEW TOGGLE
# ─────────────────────────────────────────────────────────────────────────────
col_title, col_toggle = st.columns([3, 1])
with col_title:
    st.markdown(f"#### Top {top_n} candidates")
with col_toggle:
    view = st.radio("view", ["Cards", "Table"], horizontal=True, label_visibility="collapsed")

# ── CARDS ─────────────────────────────────────────────────────────────────────
if view == "Cards":
    for r in rows[:20]:
        must_tags   = "".join(f'<span class="tag">✓ {s}</span>' for s in r["matched_must"][:4])
        strong_tags = "".join(f'<span class="tag">{s}</span>'   for s in r["matched_strong"][:3])
        concerns = []
        if isinstance(r["notice"], int) and r["notice"] > 60:
            concerns.append(f"{r['notice']}d notice")
        if r["resp_rate"] < 0.25:
            concerns.append("low response rate")
        if not r["open_to_work"]:
            concerns.append("not open to work")
        concern_html = "".join(f'<span class="concern-tag">⚠ {c}</span>' for c in concerns)
        avail = "🟢" if (isinstance(r["notice"], int) and r["notice"] <= 30) else \
                "🟡" if (isinstance(r["notice"], int) and r["notice"] <= 60) else "🔴"

        st.markdown(f"""
<div class="candidate-card">
  <span class="rank-badge">#{r['rank']}</span>
  <span class="score-pill">{r['score']:.3f}</span>
  <span style="font-size:0.82rem;color:#888;margin-left:8px;">{avail} {r['notice']}d notice</span>
  <div style="margin-top:8px;">
    <strong style="font-size:1rem;color:#111111;">{r['title']}</strong>
    <span style="color:#666;font-size:0.9rem;"> · {r['company']}</span>
  </div>
  <div style="color:#888;font-size:0.82rem;margin-top:2px;">{r['yoe']} yrs &nbsp;·&nbsp; {r['location']}</div>
  <div style="margin-top:8px;">{must_tags}{strong_tags}{concern_html}</div>
  <div class="reasoning-text">{r['reasoning']}</div>
</div>
""", unsafe_allow_html=True)

    if top_n > 20:
        st.caption(f"Showing top 20 cards — switch to Table to see all {top_n}.")

# ── TABLE ─────────────────────────────────────────────────────────────────────
else:
    df = pd.DataFrame([{
        "Rank":      r["rank"],
        "ID":        r["candidate_id"],
        "Score":     r["score"],
        "Title":     r["title"],
        "Company":   r["company"],
        "YoE":       r["yoe"],
        "Location":  r["location"],
        "Notice":    r["notice"],
        "Resp Rate": round(r["resp_rate"], 2),
        "Reasoning": r["reasoning"],
    } for r in rows])

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=520,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=1, format="%.3f"
            ),
            "Reasoning": st.column_config.TextColumn("Reasoning", width="large"),
        },
    )

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────
buf = io.StringIO()
writer = csv.DictWriter(buf, fieldnames=["candidate_id", "rank", "score", "reasoning"])
writer.writeheader()
for r in rows:
    writer.writerow({
        "candidate_id": r["candidate_id"],
        "rank":         r["rank"],
        "score":        r["score"],
        "reasoning":    r["reasoning"],
    })

col_dl, col_info = st.columns([1, 3])
with col_dl:
    st.download_button(
        label="Download submission.csv",
        data=buf.getvalue().encode("utf-8"),
        file_name="submission.csv",
        mime="text/csv",
        use_container_width=True,
    )
with col_info:
    st.caption(
        f"{len(rows)} candidates · scores {rows[-1]['score']:.3f}–{rows[0]['score']:.3f} "
        f"· {elapsed:.1f}s"
    )
