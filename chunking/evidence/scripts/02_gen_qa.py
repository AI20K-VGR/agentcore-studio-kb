import asyncio
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, "apps/studio/src")

from dotenv import load_dotenv

load_dotenv()

from studio_app.providers.factory import build_llm  # noqa: E402

BENCH = Path(
    "/private/tmp/claude-501/-Users-nguyendonganh-agentcore-studio-kit/"
    "768f885a-db4e-44a7-9050-235af71ab048/scratchpad/bench"
)

TARGET_N = {
    "Chế độ lương thưởng - hr.md": 8,
    "Nội quy an toàn lao động - engineeringdocx.docx": 4,
    "Quy định nghỉ phép 2 - public.txt": 6,
    "Quy định bảo mật - engineering.md": 3,
    "nội quy lao động - public.docx": 10,
    "nội quy lao động 2- public.docx": 4,
    "quy chế lương thưởng - hr.docx": 5,
    "quy chế lương thưởng - hr.md": 4,
    "quy định nghỉ phép - public.txt": 4,
}
BATCH = 4  # <=4 câu/lời gọi — tránh output bị cắt cụt (đo được ở lần chạy trước: 8 câu/lời gọi bị truncate)

PROMPT_TMPL = (
    """Bạn là công cụ sinh bộ câu hỏi kiểm tra retrieval cho một hệ thống RAG. Đọc tài liệu dưới đây """
    """(nguyên văn, CHƯA bị cắt chunk) và sinh ra ĐÚNG {n} câu hỏi trắc nghiệm-sự-kiện (factual), mỗi câu """
    """bám 1 sự kiện CỤ THỂ, KHÁC NHAU trong tài liệu (số liệu, tên, mốc thời gian, quy định...). {avoid_clause}

Với MỖI câu hỏi, trả về đúng 3 trường:
- "question": câu hỏi tiếng Việt, tự nhiên, không lộ đáp án.
- "expected_answer": đáp án ngắn gọn (vài từ, ưu tiên số liệu/tên riêng nếu có).
- "expected_snippet": một đoạn trích NGUYÊN VĂN, COPY CHÍNH XÁC TỪNG KÝ TỰ liên tục từ tài liệu bên dưới """
    """(không diễn giải, không tự thêm dấu "...", không sửa dấu câu/khoảng trắng/gạch đầu dòng), """
    """TỐI ĐA 25 từ, PHẢI chứa đáp án.

CHỈ trả về JSON array hợp lệ, KHÔNG markdown, KHÔNG giải thích, KHÔNG suy luận trước khi trả JSON. Hình dạng:
[{{"question": "...", "expected_answer": "...", "expected_snippet": "..."}}]

TÀI LIỆU:
---
{doc}
---
"""
)


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("–", "-").replace("—", "-").replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"').replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _extract_json(raw: str) -> list[dict[str, str]] | None:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    # LLM đôi khi kèm text trước/sau JSON dù đã dặn — cắt tới cặp [ ] ngoài cùng.
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        result = json.loads(cleaned[start : end + 1])
        return result if isinstance(result, list) else None
    except json.JSONDecodeError:
        return None


async def gen_for_doc(
    llm: object, src_name: str, n_target: int
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[str]]:
    """Trả (candidates_raw, valid_qa, raw_responses) — gọi nhiều lô <=BATCH câu/lời gọi."""
    path = BENCH / f"{src_name}.extracted.txt"
    text = path.read_text(encoding="utf-8")
    norm_text = _normalize(text)

    all_candidates: list[dict[str, str]] = []
    valid: list[dict[str, str]] = []
    raw_responses: list[str] = []
    asked_questions: list[str] = []

    remaining = n_target
    attempts = 0
    while remaining > 0 and attempts < 6:  # trần 6 lượt/doc để không loop vô hạn nếu model liên tục lỗi
        attempts += 1
        batch_n = min(BATCH, remaining)
        avoid_clause = ""
        if asked_questions:
            avoid_clause = "TRÁNH lặp lại/gần giống các câu đã hỏi trước: " + " | ".join(asked_questions[-8:])
        prompt = PROMPT_TMPL.format(n=batch_n, doc=text, avoid_clause=avoid_clause)
        raw = await llm.complete(prompt)  # type: ignore[attr-defined]
        raw_responses.append(raw)
        items = _extract_json(raw)
        if items is None:
            print(f"  [{src_name}] lô {attempts}: JSON parse thất bại, bỏ qua lô này")
            continue

        got_this_round = 0
        for it in items:
            q = str(it.get("question", ""))
            a = str(it.get("expected_answer", ""))
            snip = str(it.get("expected_snippet", ""))
            all_candidates.append({"doc": src_name, "question": q, "expected_answer": a, "expected_snippet": snip})
            if not (q and a and snip):
                continue
            if _normalize(snip) in norm_text:
                valid.append({"doc": src_name, "question": q, "expected_answer": a, "expected_snippet": snip})
                asked_questions.append(q)
                got_this_round += 1
        remaining = n_target - len(valid)
        print(
            f"  [{src_name}] lô {attempts}: xin {batch_n} · nhận {len(items)} · "
            f"verbatim hợp lệ +{got_this_round} (tổng {len(valid)}/{n_target})"
        )

    return all_candidates, valid, raw_responses


async def main() -> None:
    llm = build_llm()
    all_qa: list[dict[str, str]] = []
    all_candidates: list[dict[str, str]] = []
    stats: dict[str, dict[str, int]] = {}

    for src_name, n in TARGET_N.items():
        print(f"[{src_name}] mục tiêu {n} câu")
        candidates, valid, raw_responses = await gen_for_doc(llm, src_name, n)
        all_candidates.extend(candidates)
        all_qa.extend(valid)
        stats[src_name] = {"requested": n, "candidates": len(candidates), "valid_snippet": len(valid)}
        (BENCH / f"_raw_{src_name.replace('/', '_')}.txt").write_text(
            "\n\n===LÔ MỚI===\n\n".join(raw_responses), encoding="utf-8"
        )

    (BENCH / "qa_set.json").write_text(json.dumps(all_qa, ensure_ascii=False, indent=2), encoding="utf-8")
    (BENCH / "qa_candidates_all.json").write_text(
        json.dumps(all_candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (BENCH / "qa_gen_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTổng QA hợp lệ (verbatim-checked): {len(all_qa)} / mục tiêu {sum(TARGET_N.values())}")


if __name__ == "__main__":
    asyncio.run(main())
