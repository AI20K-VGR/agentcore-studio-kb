import asyncio
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, "apps/studio/src")

from dotenv import load_dotenv

load_dotenv()

from studio_app.providers.factory import build_embedding  # noqa: E402

BENCH = Path(
    "/private/tmp/claude-501/-Users-nguyendonganh-agentcore-studio-kit/"
    "768f885a-db4e-44a7-9050-235af71ab048/scratchpad/bench"
)
CONFIGS = ["200_50", "500_100", "850_170"]


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("–", "-").replace("—", "-").replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"').replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)


async def main() -> None:
    embedding = build_embedding()  # cache DB đã có sẵn 50 query này từ bước trước -> không tốn call thật mới
    qa = json.loads((BENCH / "qa_set_100.json").read_text(encoding="utf-8"))
    queries = [q["question"] for q in qa]
    qvecs = await embedding.embed(queries)

    chunks_by_cfg = {cfg: json.loads((BENCH / f"chunks_{cfg}.json").read_text(encoding="utf-8")) for cfg in CONFIGS}

    per_query = {cfg: [] for cfg in CONFIGS}
    for qi, q in enumerate(qa):
        qvec = qvecs[qi]
        norm_snip = _normalize(q["expected_snippet"])

        for cfg in CONFIGS:
            chunks = chunks_by_cfg[cfg]
            scored = [(c, cos(qvec, c["vector"])) for c in chunks]

            hit_scores = [(c, s) for c, s in scored if norm_snip in _normalize(c["text"])]
            nonhit_scores = [(c, s) for c, s in scored if norm_snip not in _normalize(c["text"])]

            best_hit = max(hit_scores, key=lambda t: t[1]) if hit_scores else None
            best_nonhit = max(nonhit_scores, key=lambda t: t[1]) if nonhit_scores else None

            margin = (best_hit[1] - best_nonhit[1]) if (best_hit and best_nonhit) else None

            per_query[cfg].append(
                {
                    "query_idx": qi,
                    "question": q["question"],
                    "source_doc": q["doc"],
                    "expected_answer": q["expected_answer"],
                    "n_hit_chunks_in_corpus": len(hit_scores),
                    "best_hit_chunk_id": best_hit[0]["chunk_id"] if best_hit else None,
                    "best_hit_score": round(best_hit[1], 4) if best_hit else None,
                    "best_distractor_chunk_id": best_nonhit[0]["chunk_id"] if best_nonhit else None,
                    "best_distractor_score": round(best_nonhit[1], 4) if best_nonhit else None,
                    "margin": round(margin, 4) if margin is not None else None,
                    "separated_correctly": (margin is not None and margin > 0),
                }
            )

    summary = {}
    for cfg in CONFIGS:
        rows = per_query[cfg]
        margins = [r["margin"] for r in rows if r["margin"] is not None]
        n = len(rows)
        n_sep = sum(r["separated_correctly"] for r in rows)
        margins_sorted = sorted(margins)
        median = margins_sorted[len(margins_sorted) // 2] if margins_sorted else None
        summary[cfg] = {
            "n_queries": n,
            "n_separated_correctly": n_sep,
            "separated_rate": round(n_sep / n, 4),
            "mean_margin": round(sum(margins) / len(margins), 4) if margins else None,
            "median_margin": round(median, 4) if median is not None else None,
            "min_margin": round(min(margins), 4) if margins else None,
            "max_margin": round(max(margins), 4) if margins else None,
            "n_negative_margin": sum(1 for m in margins if m < 0),
        }
        print(f"[{cfg}] {json.dumps(summary[cfg], ensure_ascii=False, indent=2)}")

    (BENCH / "separation_summary_100q.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    for cfg in CONFIGS:
        (BENCH / f"separation_detail_100q_{cfg}.json").write_text(
            json.dumps(per_query[cfg], ensure_ascii=False, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    asyncio.run(main())
