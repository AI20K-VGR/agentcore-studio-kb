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
SRC = "nội quy lao động 2- public.docx"

PROMPT_TMPL = (
    """Bạn là công cụ sinh câu hỏi kiểm tra retrieval cho một hệ thống RAG. Đọc tài liệu dưới đây """
    """(nguyên văn) và sinh ĐÚNG 1 câu hỏi trắc nghiệm-sự-kiện MỚI.

BẮT BUỘC: KHÔNG hỏi lại (kể cả diễn đạt khác) bất kỳ sự kiện nào đã dùng ở các đoạn trích sau:
{avoid_list}

Trả về đúng 3 trường: "question", "expected_answer", "expected_snippet" (NGUYÊN VĂN, copy chính xác """
    """từng ký tự, tối đa 25 từ, phải chứa đáp án).
CHỈ trả JSON array 1 phần tử, không markdown, không giải thích.

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
    return re.sub(r"\s+", " ", s).strip()


def _extract_json(raw: str) -> list[dict[str, str]] | None:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start == -1 or end == -1:
        return None
    try:
        r = json.loads(cleaned[start : end + 1])
        return r if isinstance(r, list) else None
    except json.JSONDecodeError:
        return None


async def main() -> None:
    llm = build_llm()
    qa = json.loads((BENCH / "qa_set_final.json").read_text(encoding="utf-8"))
    text = (BENCH / f"{SRC}.extracted.txt").read_text(encoding="utf-8")
    norm_text = _normalize(text)

    avoid = [q["expected_snippet"] for q in qa if q["doc"] == SRC]
    # cộng cả snippet phía "nội quy lao động - public.docx" bản 1 để không lại trùng chéo
    avoid += [q["expected_snippet"] for q in qa if q["doc"] == "nội quy lao động - public.docx"]

    got = None
    for attempt in range(5):
        prompt = PROMPT_TMPL.format(doc=text, avoid_list="\n".join(f"- {s}" for s in avoid))
        raw = await llm.complete(prompt)
        items = _extract_json(raw)
        if not items:
            continue
        it = items[0]
        q = str(it.get("question", ""))
        a = str(it.get("expected_answer", ""))
        snip = str(it.get("expected_snippet", ""))
        if not (q and a and snip):
            continue
        if _normalize(snip) not in norm_text:
            print(f"lô {attempt}: không verbatim, loại: {snip[:60]!r}")
            continue
        if any(difflib.SequenceMatcher(None, snip, s).ratio() > 0.85 for s in avoid):
            print(f"lô {attempt}: vẫn trùng, loại: {snip[:60]!r}")
            continue
        got = {"doc": SRC, "question": q, "expected_answer": a, "expected_snippet": snip}
        break

    if got is None:
        raise SystemExit("Không sinh được câu thay thế sau 5 lần thử")

    qa[48] = got
    (BENCH / "qa_set_final.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Đã thay #48:", json.dumps(got, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
