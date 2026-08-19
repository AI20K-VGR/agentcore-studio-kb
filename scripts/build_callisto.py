"""Doc-factory "1 lệnh 2 deliverable" (D16, DE) — issue #105: KB **và** golden-set từ CÙNG nguồn.

    uv run --python 3.14 --package agentcore-studio-kb python packages/kb/scripts/build_callisto.py

Vì sao gộp một entrypoint (#105 "1 script 2 deliverable: KB + golden-set"): golden-set phải sinh **từ
chính doc-factory** — nếu KB và golden đi hai đường tay rời nhau thì không gì buộc `expected_citation`
trong golden là `chunk_id` doc-factory **thật**. Lệnh này đọc corpus qua `load_callisto()` (cùng nguồn
mọi recorder khác dùng) rồi phát:

  1. **KB** — re-record `golden/embeddings-callisto-v0.json` (`build_fixture`/`dump_fixture`, cùng
     `derive_vector`) + in manifest (số doc / chunk / per-tenant / per-role). Đây là fixture đường
     ingest (`ingest_callisto.py`) nạp vào `kb.chunks`.
  2. **golden-set** — re-emit `golden/callisto-golden-30-v1.yaml` (`golden_set.render_yaml`).

Cả hai recorder đọc **cùng** `load_callisto()`, nên `chunk_id` khớp từng ký tự **do kiến tạo** — đó là
điều "từ CHÍNH doc-factory" đòi. Không claim "một lần gọi hàm duy nhất" (mỗi recorder tự `load_callisto`
riêng vì đó là đường đọc duy nhất của chúng); claim đúng là **cùng NGUỒN corpus + cùng công thức**.

Cuối lệnh kiểm bất biến rẻ: mọi `expected_citation` của golden-set ∈ tập `chunk_id` corpus (chống nhãn
trỏ chunk chết). Kiểm nhãn ĐẦY ĐỦ (grounded / duy-nhất / fence / teeth) là `tests/test_golden_set.py`.

**Không** dựng schema / không ghi DB ở đây (DDL = composition-root; ingest DB = `ingest_callisto.py` khi
có Docker) — giữ đúng ranh: script này chỉ phát artifact recorded, không đụng hạ tầng.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from studio_kb.doc_factory import load_callisto
from studio_kb.embeddings import FIXTURE_PATH, build_fixture, dump_fixture
from studio_kb.golden_set import GOLDEN_CASES, render_yaml

_GOLDEN_PATH = Path(__file__).resolve().parents[1] / "src" / "studio_kb" / "golden" / "callisto-golden-30-v1.yaml"


def main() -> None:
    chunks = load_callisto()
    chunk_ids = {c.chunk_id for c in chunks}
    docs = {cid.split("#", 1)[0] for cid in chunk_ids}
    per_tenant = Counter(c.tenant_id for c in chunks)
    per_role = Counter(c.section_role for c in chunks)

    # ── Deliverable 1: KB (embeddings fixture cho đường ingest) ──────────────────────────────────
    fixture = build_fixture()
    FIXTURE_PATH.write_text(dump_fixture(fixture), encoding="utf-8")
    vectors = fixture["vectors"]
    assert isinstance(vectors, dict)
    print(f"[KB]     {FIXTURE_PATH.name} — {len(vectors)} chunk, {fixture['dim']} chiều")
    print(f"[KB]     manifest — {len(docs)} doc / {len(chunks)} chunk / {len(per_tenant)} tenant")
    for role, n in sorted(per_role.items()):
        print(f"[KB]       role {role:<12} {n} chunk")

    # ── Deliverable 2: golden-set (nhãn từ cùng corpus) ─────────────────────────────────────────
    _GOLDEN_PATH.write_text(render_yaml(), encoding="utf-8")
    positives = sum(1 for case in GOLDEN_CASES if not case.is_refusal)
    refusals = len(GOLDEN_CASES) - positives
    print(f"[golden] {_GOLDEN_PATH.name} — {positives} case dương + {refusals} âm")

    # ── Bất biến rẻ: expected_citation của golden ∈ corpus (nhãn không trỏ chunk chết) ───────────
    cited = {cid for case in GOLDEN_CASES for cid in case.expected_citation}
    missing = sorted(cited - chunk_ids)
    if missing:
        raise SystemExit(f"expected_citation trỏ chunk KHÔNG có trong corpus: {missing}")
    print(f"[check]  {len(cited)} expected_citation đều ∈ corpus doc-factory ✓")


if __name__ == "__main__":
    main()
