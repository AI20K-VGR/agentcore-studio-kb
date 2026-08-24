import json
import re
import unicodedata
from pathlib import Path

BENCH = Path(
    "/private/tmp/claude-501/-Users-nguyendonganh-agentcore-studio-kit/"
    "768f885a-db4e-44a7-9050-235af71ab048/scratchpad/bench"
)
TARGET_LEN = 150  # từ — kéo dài snippet lên ~150 từ (gần bằng cửa sổ 200/50, để thật sự stress-test)


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("–", "-").replace("—", "-").replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"').replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def find_word_span(doc_words: list[str], snippet_words: list[str]) -> tuple[int, int] | None:
    """Tìm vị trí (theo chỉ số từ) của snippet trong doc_words — so khớp CHUẨN HOÁ từng từ liên tiếp."""
    norm_doc = [_normalize(w) for w in doc_words]
    norm_snip = [_normalize(w) for w in snippet_words]
    n, m = len(norm_doc), len(norm_snip)
    for i in range(n - m + 1):
        if norm_doc[i : i + m] == norm_snip:
            return i, i + m
    return None


def main() -> None:
    qa = json.loads((BENCH / "qa_set_100.json").read_text(encoding="utf-8"))

    last20_idx = list(range(80, 100))
    updated = []
    failed = []

    for idx in last20_idx:
        item = qa[idx]
        src = item["doc"]
        doc_text = (BENCH / f"{src}.extracted.txt").read_text(encoding="utf-8")
        doc_words = doc_text.split()
        snip_words = item["expected_snippet"].split()

        span = find_word_span(doc_words, snip_words)
        if span is None:
            failed.append(idx)
            print(f"[{idx}] KHÔNG tìm thấy vị trí snippet trong doc — bỏ qua: {item['expected_snippet'][:60]!r}")
            continue

        i, j = span
        cur_len = j - i
        extra = max(0, TARGET_LEN - cur_len)
        before = extra // 2
        after = extra - before

        new_i = max(0, i - before)
        new_j = min(len(doc_words), j + after)
        # nếu bị chặn 1 phía (đầu/cuối văn bản), bù thêm cho phía kia
        if new_i == 0:
            new_j = min(len(doc_words), new_j + (before - i))
        if new_j == len(doc_words):
            new_i = max(0, new_i - (after - (len(doc_words) - j)))

        long_snippet = " ".join(doc_words[new_i:new_j])
        item["expected_snippet_long"] = long_snippet
        item["expected_snippet_long_word_count"] = new_j - new_i
        updated.append(idx)
        print(f"[{idx}] gốc {cur_len} từ → kéo dài {new_j - new_i} từ (doc={src})")

    (BENCH / "qa_set_100.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nĐã kéo dài {len(updated)}/20 câu, thất bại {len(failed)}: {failed}")


if __name__ == "__main__":
    main()
