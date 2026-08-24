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
CONFIGS = ["500_100", "850_170"]
TOP_K = 5


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
    embedding = build_embedding()
    qa = json.loads((BENCH / "qa_set_final.json").read_text(encoding="utf-8"))
    queries = [q["question"] for q in qa]
    qvecs = await embedding.embed(queries)

    chunks_by_cfg = {cfg: json.loads((BENCH / f"chunks_{cfg}.json").read_text(encoding="utf-8")) for cfg in CONFIGS}

    results = {cfg: [] for cfg in CONFIGS}

    for qi, q in enumerate(qa):
        qvec = qvecs[qi]
        norm_snip = _normalize(q["expected_snippet"])

        for cfg in CONFIGS:
            chunks = chunks_by_cfg[cfg]
            scored = [(c, cos(qvec, c["vector"])) for c in chunks]
            scored.sort(key=lambda t: t[1], reverse=True)
            topk = scored[:TOP_K]

            # snippet-intact: đoạn trích gốc có nằm TRỌN trong ít nhất 1 chunk (bất kỳ đâu, không
            # chỉ trong top_k) của cấu hình này không — đo việc window có xé lẻ sự kiện qua ranh
            # giới cắt hay không, độc lập với việc retrieval có tìm ra nó hay không.
            snippet_intact_anywhere = any(norm_snip in _normalize(c["text"]) for c in chunks)

            top_entries = []
            first_hit_rank = None
            for rank, (c, score) in enumerate(topk, start=1):
                is_hit = norm_snip in _normalize(c["text"])
                if is_hit and first_hit_rank is None:
                    first_hit_rank = rank
                top_entries.append(
                    {
                        "rank": rank,
                        "chunk_id": c["chunk_id"],
                        "doc": c["doc"],
                        "score": round(score, 4),
                        "is_hit": is_hit,
                        "text_preview": c["text"][:220],
                    }
                )

            results[cfg].append(
                {
                    "query_idx": qi,
                    "question": q["question"],
                    "source_doc": q["doc"],
                    "expected_answer": q["expected_answer"],
                    "expected_snippet": q["expected_snippet"],
                    "snippet_intact_anywhere": snippet_intact_anywhere,
                    "first_hit_rank": first_hit_rank,
                    "hit_at_1": first_hit_rank == 1,
                    "hit_at_3": first_hit_rank is not None and first_hit_rank <= 3,
                    "hit_at_5": first_hit_rank is not None and first_hit_rank <= 5,
                    "top1_score": topk[0][1] if topk else None,
                    "n_chunks_total": len(chunks),
                    "top_k": top_entries,
                }
            )

    for cfg in CONFIGS:
        (BENCH / f"retrieval_results_{cfg}.json").write_text(
            json.dumps(results[cfg], ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ── tổng hợp ──
    summary = {}
    for cfg in CONFIGS:
        rs = results[cfg]
        n = len(rs)
        hit1 = sum(r["hit_at_1"] for r in rs)
        hit3 = sum(r["hit_at_3"] for r in rs)
        hit5 = sum(r["hit_at_5"] for r in rs)
        mrr = sum((1.0 / r["first_hit_rank"]) if r["first_hit_rank"] else 0.0 for r in rs) / n
        mean_top1 = sum(r["top1_score"] for r in rs if r["top1_score"] is not None) / n
        intact = sum(r["snippet_intact_anywhere"] for r in rs)
        summary[cfg] = {
            "n_queries": n,
            "n_chunks_corpus": rs[0]["n_chunks_total"],
            "hit@1": hit1,
            "hit@1_rate": round(hit1 / n, 4),
            "hit@3": hit3,
            "hit@3_rate": round(hit3 / n, 4),
            "hit@5": hit5,
            "hit@5_rate": round(hit5 / n, 4),
            "mrr@5": round(mrr, 4),
            "mean_top1_cosine": round(mean_top1, 4),
            "snippet_intact_rate": round(intact / n, 4),
        }
        print(f"[{cfg}] {json.dumps(summary[cfg], ensure_ascii=False, indent=2)}")

    (BENCH / "retrieval_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
