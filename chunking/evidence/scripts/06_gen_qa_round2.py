import asyncio
import difflib
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

# Cùng tỉ lệ vòng 1 để giữ cân đối theo độ dài file.
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
BATCH = 3  # nhỏ hơn vòng 1 — prompt khó hơn/dài hơn, giảm rủi ro truncate

PROMPT_TMPL = """Bạn là công cụ sinh câu hỏi kiểm tra retrieval cho hệ thống RAG — VÒNG 2, MỨC KHÓ HƠN vòng 1.

Đọc tài liệu dưới đây (nguyên văn) và sinh ĐÚNG {n} câu hỏi factual MỚI, bám sự kiện CỤ THỂ, KHÁC
NHAU. Yêu cầu KHÓ HƠN vòng 1, cụ thể:

1. **Hỏi GIÁN TIẾP, KHÔNG diễn đạt gần giống câu gốc** — không dùng lại cụm từ/thứ tự chữ trong tài
   liệu, phải diễn đạt lại bằng từ ngữ khác, buộc phải hiểu ý nghĩa chứ không match từ khoá.
2. **Nhắm vào chi tiết ÍT NỔI BẬT hơn** — không hỏi lại các con số/sự kiện "đầu tiên đập vào mắt"
   (đầu đoạn, tiêu đề, in đậm) — ưu tiên chi tiết nằm giữa đoạn văn dài, điều khoản phụ, trường hợp
   ngoại lệ, điều kiện kèm theo.
3. **Trải rộng khắp tài liệu** — không dồn câu hỏi vào 1-2 đoạn đầu; cố gắng lấy sự kiện từ nhiều vị
   trí khác nhau (đầu/giữa/cuối tài liệu).
4. Có thể dùng câu hỏi dạng so sánh/điều kiện ("trong trường hợp nào thì...", "khác biệt giữa X và
   Y là gì") miễn NGƯỜI HỎI vẫn xác định được 1 đáp án CỤ THỂ, NGẮN — không hỏi mở/không có đáp án rõ.

BẮT BUỘC: TUYỆT ĐỐI KHÔNG hỏi lại (kể cả diễn đạt khác) bất kỳ sự kiện nào đã dùng ở các đoạn trích
sau (đã có câu hỏi rồi ở vòng 1 lẫn vòng 2, cấm trùng ý dù chỉ một phần):
{avoid_list}

Với MỖI câu hỏi, trả về đúng 3 trường:
- "question": câu hỏi tiếng Việt, GIÁN TIẾP như yêu cầu trên.
- "expected_answer": đáp án ngắn gọn.
- "expected_snippet": đoạn trích NGUYÊN VĂN, COPY CHÍNH XÁC TỪNG KÝ TỰ liên tục từ tài liệu (không
  diễn giải, không thêm "...", không sửa dấu câu/khoảng trắng), TỐI ĐA 25 từ, PHẢI chứa đáp án.

CHỈ trả JSON array hợp lệ, KHÔNG markdown, KHÔNG giải thích. Hình dạng:
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
    return re.sub(r"\s+", " ", s).strip()


def _extract_json(raw: str) -> list[dict[str, str]] | None:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        r = json.loads(cleaned[start : end + 1])
        return r if isinstance(r, list) else None
    except json.JSONDecodeError:
        return None


async def gen_for_doc(llm: object, src_name: str, n_target: int, round1_snippets: list[str]) -> list[dict[str, str]]:
    text = (BENCH / f"{src_name}.extracted.txt").read_text(encoding="utf-8")
    norm_text = _normalize(text)

    valid: list[dict[str, str]] = []
    avoid = list(round1_snippets)  # trùng với vòng 1 cũng bị cấm ngay từ đầu
    attempts = 0
    while len(valid) < n_target and attempts < 8:
        attempts += 1
        batch_n = min(BATCH, n_target - len(valid))
        avoid_str = "\n".join(f"- {s}" for s in avoid)
        prompt = PROMPT_TMPL.format(n=batch_n, doc=text, avoid_list=avoid_str)
        raw = await llm.complete(prompt)  # type: ignore[attr-defined]
        items = _extract_json(raw)
        if not items:
            print(f"  [{src_name}] lô {attempts}: parse thất bại")
            continue

        got = 0
        for it in items:
            q = str(it.get("question", ""))
            a = str(it.get("expected_answer", ""))
            snip = str(it.get("expected_snippet", ""))
            if not (q and a and snip):
                continue
            if _normalize(snip) not in norm_text:
                print(f"  [{src_name}] không verbatim, loại: {snip[:60]!r}")
                continue
            if any(difflib.SequenceMatcher(None, snip, s).ratio() > 0.85 for s in avoid):
                print(f"  [{src_name}] trùng snippet đã có, loại: {snip[:60]!r}")
                continue
            valid.append({"doc": src_name, "question": q, "expected_answer": a, "expected_snippet": snip})
            avoid.append(snip)
            got += 1
        print(
            f"  [{src_name}] lô {attempts}: xin {batch_n} · nhận {len(items)} · "
            f"hợp lệ +{got} (tổng {len(valid)}/{n_target})"
        )

    return valid


async def main() -> None:
    llm = build_llm()
    round1 = json.loads((BENCH / "qa_set_final.json").read_text(encoding="utf-8"))

    round2: list[dict[str, str]] = []
    for src_name, n in TARGET_N.items():
        print(f"[{src_name}] mục tiêu {n} câu (vòng 2)")
        r1_snips = [q["expected_snippet"] for q in round1 if q["doc"] == src_name]
        items = await gen_for_doc(llm, src_name, n, r1_snips)
        round2.extend(items)

    (BENCH / "qa_set_round2.json").write_text(json.dumps(round2, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTổng vòng 2: {len(round2)}")
    from collections import Counter

    print(Counter(q["doc"] for q in round2))


if __name__ == "__main__":
    asyncio.run(main())
