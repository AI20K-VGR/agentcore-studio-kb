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

SHORTFALL = {
    "Chế độ lương thưởng - hr.md": 6,  # 5 bù trùng + 1 ép về 50
    "Quy định nghỉ phép 2 - public.txt": 1,
    "nội quy lao động - public.docx": 3,  # 2 bù trùng + 1 ép về 50
    "nội quy lao động 2- public.docx": 1,
    "quy chế lương thưởng - hr.docx": 1,
}

PROMPT_TMPL = """Bạn là công cụ sinh bộ câu hỏi kiểm tra retrieval cho một hệ thống RAG. Đọc tài liệu dưới đây (nguyên văn, CHƯA bị cắt chunk) và sinh ra ĐÚNG {n} câu hỏi trắc nghiệm-sự-kiện (factual) MỚI, mỗi câu bám 1 sự kiện CỤ THỂ, KHÁC NHAU trong tài liệu.

BẮT BUỘC: KHÔNG được hỏi lại (kể cả diễn đạt khác) bất kỳ sự kiện nào đã dùng ở các đoạn trích sau (đã có câu hỏi rồi, cấm trùng):
{avoid_list}

Với MỖI câu hỏi, trả về đúng 3 trường:
- "question": câu hỏi tiếng Việt, tự nhiên, không lộ đáp án.
- "expected_answer": đáp án ngắn gọn (vài từ, ưu tiên số liệu/tên riêng nếu có).
- "expected_snippet": một đoạn trích NGUYÊN VĂN, COPY CHÍNH XÁC TỪNG KÝ TỰ liên tục từ tài liệu bên dưới (không diễn giải, không tự thêm dấu "...", không sửa dấu câu/khoảng trắng/gạch đầu dòng), TỐI ĐA 25 từ, PHẢI chứa đáp án.

CHỈ trả về JSON array hợp lệ, KHÔNG markdown, KHÔNG giải thích. Hình dạng:
[{{"question": "...", "expected_answer": "...", "expected_snippet": "..."}}]

TÀI LIỆU:
---
{doc}
---
"""


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
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        result = json.loads(cleaned[start : end + 1])
        return result if isinstance(result, list) else None
    except json.JSONDecodeError:
        return None


async def main() -> None:
    llm = build_llm()
    dedup = json.loads((BENCH / "qa_set_dedup.json").read_text(encoding="utf-8"))
    new_items: list[dict[str, str]] = []

    for src_name, need in SHORTFALL.items():
        text = (BENCH / f"{src_name}.extracted.txt").read_text(encoding="utf-8")
        norm_text = _normalize(text)
        used_snippets = [q["expected_snippet"] for q in dedup if q["doc"] == src_name]
        got = 0
        attempts = 0
        avoid_list_local = list(used_snippets)
        while got < need and attempts < 6:
            attempts += 1
            avoid_str = "\n".join(f"- {s}" for s in avoid_list_local)
            prompt = PROMPT_TMPL.format(n=need - got, doc=text, avoid_list=avoid_str)
            raw = await llm.complete(prompt)
            items = _extract_json(raw)
            if not items:
                print(f"[{src_name}] lô {attempts}: parse thất bại")
                continue
            for it in items:
                q, a, snip = str(it.get("question", "")), str(it.get("expected_answer", "")), str(it.get("expected_snippet", ""))
                if not (q and a and snip):
                    continue
                if _normalize(snip) not in norm_text:
                    print(f"[{src_name}] snippet không verbatim, loại: {snip[:60]!r}")
                    continue
                import difflib

                if any(difflib.SequenceMatcher(None, snip, s).ratio() > 0.85 for s in avoid_list_local):
                    print(f"[{src_name}] trùng snippet đã có, loại: {snip[:60]!r}")
                    continue
                new_items.append({"doc": src_name, "question": q, "expected_answer": a, "expected_snippet": snip})
                avoid_list_local.append(snip)
                got += 1
                if got >= need:
                    break
            print(f"[{src_name}] lô {attempts}: +{got}/{need}")

    dedup.extend(new_items)
    (BENCH / "qa_set_final.json").write_text(json.dumps(dedup, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTổng sau khi bù: {len(dedup)}")
    from collections import Counter

    print(Counter(q["doc"] for q in dedup))


if __name__ == "__main__":
    asyncio.run(main())
