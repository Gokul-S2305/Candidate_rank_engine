#!/usr/bin/env python3
"""
rank.py — Main ranking pipeline
Usage: python rank.py --candidates ./candidates.jsonl --out ./submission.csv

Constraints satisfied:
  ✅ ≤5 minutes wall-clock on CPU
  ✅ ≤16 GB RAM
  ✅ CPU only, no GPU
  ✅ No network (no external API calls)
  ✅ Produces valid CSV per submission_spec.md
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

# Local imports
sys.path.insert(0, str(Path(__file__).parent))
from engines.scorer import score_candidate
from engines.reasoning import generate_reasoning


def load_candidates(path: str):
    """Stream-load candidates from JSONL or JSON file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Candidates file not found: {path}")

    candidates = []
    if p.suffix == ".jsonl":
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    candidates.append(json.loads(line))
    elif p.suffix == ".json":
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                candidates = data
            else:
                candidates = [data]
    else:
        raise ValueError(f"Unsupported file type: {p.suffix} (must be .jsonl or .json)")

    return candidates


def run_pipeline(candidates_path: str, output_path: str, verbose: bool = True):
    t0 = time.time()

    # ── Step 1: Load ──────────────────────────────────────────────────────────
    if verbose:
        print(f"[1/4] Loading candidates from {candidates_path}...")
    candidates = load_candidates(candidates_path)
    t1 = time.time()
    if verbose:
        print(f"      Loaded {len(candidates):,} candidates in {t1-t0:.1f}s")

    # ── Step 2: Score all candidates ─────────────────────────────────────────
    if verbose:
        print(f"[2/4] Scoring {len(candidates):,} candidates...")

    scored = []
    honeypots_caught = 0
    disqualified = 0

    for c in candidates:
        result = score_candidate(c)
        if result.get("is_honeypot"):
            honeypots_caught += 1
        elif result["final_score"] <= 0.02:
            disqualified += 1
        scored.append((c["candidate_id"], result["final_score"], result, c))

    t2 = time.time()
    if verbose:
        print(f"      Scored in {t2-t1:.1f}s | honeypots caught: {honeypots_caught} | disqualified: {disqualified}")

    # ── Step 3: Sort and select top 100 ──────────────────────────────────────
    if verbose:
        print(f"[3/4] Ranking and selecting top 100...")

    scored.sort(key=lambda x: x[1], reverse=True)

    # Tie-break: equal scores → candidate_id ascending (per spec)
    scored.sort(key=lambda x: (-x[1], x[0]))

    top100 = scored[:100]
    t3 = time.time()

    # ── Step 4: Generate reasoning and write CSV ──────────────────────────────
    if verbose:
        print(f"[4/4] Generating reasoning and writing CSV to {output_path}...")

    rows = []
    for rank, (cid, score, score_result, candidate) in enumerate(top100, start=1):
        reasoning = generate_reasoning(candidate, score_result, rank)
        rows.append({
            "candidate_id": cid,
            "rank": rank,
            "score": round(score, 6),
            "reasoning": reasoning,
        })

    # Write CSV
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["candidate_id", "rank", "score", "reasoning"],
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)

    t4 = time.time()
    total = t4 - t0

    if verbose:
        print(f"\n{'='*55}")
        print(f"  ✅ Done in {total:.1f}s ({total/60:.1f} min)")
        print(f"  Output: {out_path}")
        print(f"  Top 5 candidates:")
        for r in rows[:5]:
            print(f"    Rank {r['rank']:3d} | {r['candidate_id']} | score={r['score']:.4f}")
            print(f"           {r['reasoning'][:90]}...")
        print(f"{'='*55}")

    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Rank candidates against the Redrob Senior AI Engineer JD"
    )
    parser.add_argument(
        "--candidates",
        default="./candidates.jsonl",
        help="Path to candidates.jsonl (or .json for sample)",
    )
    parser.add_argument(
        "--out",
        default="./submission.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    args = parser.parse_args()

    run_pipeline(
        candidates_path=args.candidates,
        output_path=args.out,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
