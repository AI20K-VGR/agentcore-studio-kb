import asyncio
import json
import math
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

sys.path.insert(0, "apps/studio/src")

from dotenv import load_dotenv

load_dotenv()

from studio_app.providers.factory import build_embedding  # noqa: E402

BENCH = Path(
    "/private/tmp/claude-501/-Users-nguyendonganh-agentcore-studio-kit/"
    "768f885a-db4e-44a7-9050-235af71ab048/scratchpad/bench"
)
CONFIGS = ["200_50", "500_100", "850_170"]
TOP_K = 5


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("–", "-").replace("—", "-").replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"').replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)


async def main() -> None:
    embedding = build_embedding()
    qa = json.loads((BENCH / "qa_set_100.json").read_text(encoding="utf-8"))
    subset_idx = [i for i in range(80, 100) if "expected_snippet_long" in qa[i]]
    print(f"Số câu test (có snippet dài): {len(subset_idx)}")

    queries = [qa[i]["question"] for i in subset_idx]
    qvecs = await embedding.embed(queries)

    chunks_by_cfg = {cfg: json.loads((BENCH / f"chunks_{cfg}.json").read_text(encoding="utf-8")) for cfg in CONFIGS}

    all_results: dict[str, list[dict[str, Any]]] = {cfg: [] for cfg in CONFIGS}

    for local_i, qi in enumerate(subset_idx):
        item = qa[qi]
        qvec = qvecs[local_i]
        norm_snip_short = _normalize(item["expected_snippet"])
        norm_snip_long = _normalize(item["expected_snippet_long"])

        for cfg in CONFIGS:
            chunks = chunks_by_cfg[cfg]
            scored = [(c, cos(qvec, c["vector"])) for c in chunks]
            scored.sort(key=lambda t: t[1], reverse=True)
            topk = scored[:TOP_K]

            intact_short_anywhere = any(norm_snip_short in _normalize(c["text"]) for c in chunks)
            intact_long_anywhere = any(norm_snip_long in _normalize(c["text"]) for c in chunks)

            first_hit_rank_short = None
            first_hit_rank_long = None
            for rank, (c, _score) in enumerate(topk, start=1):
                ctext = _normalize(c["text"])
                if norm_snip_short in ctext and first_hit_rank_short is None:
                    first_hit_rank_short = rank
                if norm_snip_long in ctext and first_hit_rank_long is None:
                    first_hit_rank_long = rank

            all_results[cfg].append(
                {
                    "query_idx": qi,
                    "question": item["question"],
                    "source_doc": item["doc"],
                    "long_snippet_word_count": item["expected_snippet_long_word_count"],
                    "intact_short_anywhere": intact_short_anywhere,
                    "intact_long_anywhere": intact_long_anywhere,
                    "hit_at_1_short": first_hit_rank_short == 1,
                    "hit_at_1_long": first_hit_rank_long == 1,
                    "hit_at_5_short": first_hit_rank_short is not None and first_hit_rank_short <= 5,
                    "hit_at_5_long": first_hit_rank_long is not None and first_hit_rank_long <= 5,
                    "n_chunks_total": len(chunks),
                }
            )

    for cfg in CONFIGS:
        (BENCH / f"long_snippet_results_{cfg}.json").write_text(
            json.dumps(all_results[cfg], ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(
        f"\n{'cfg':<10} {'n':>4} {'intact_short':>13} {'intact_long':>12} "
        f"{'hit1_short':>11} {'hit1_long':>10} {'hit5_short':>11} {'hit5_long':>10}"
    )
    summary = {}
    for cfg in CONFIGS:
        rows = all_results[cfg]
        n = len(rows)
        intact_short = sum(r["intact_short_anywhere"] for r in rows)
        intact_long = sum(r["intact_long_anywhere"] for r in rows)
        h1s = sum(r["hit_at_1_short"] for r in rows)
        h1l = sum(r["hit_at_1_long"] for r in rows)
        h5s = sum(r["hit_at_5_short"] for r in rows)
        h5l = sum(r["hit_at_5_long"] for r in rows)
        summary[cfg] = {
            "n": n,
            "intact_short_rate": round(intact_short / n, 3),
            "intact_long_rate": round(intact_long / n, 3),
            "hit1_short_rate": round(h1s / n, 3),
            "hit1_long_rate": round(h1l / n, 3),
            "hit5_short_rate": round(h5s / n, 3),
            "hit5_long_rate": round(h5l / n, 3),
        }
        print(
            f"{cfg:<10} {n:>4} {intact_short / n:>13.1%} {intact_long / n:>12.1%} "
            f"{h1s / n:>11.1%} {h1l / n:>10.1%} {h5s / n:>11.1%} {h5l / n:>10.1%}"
        )

    (BENCH / "long_snippet_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(main())
