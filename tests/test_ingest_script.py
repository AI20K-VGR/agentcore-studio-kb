"""`scripts/ingest_callisto.py` — CLI ingest per-tenant (D13). Kiểm phần **glue** riêng của script,
KHÔNG lặp lại `test_pg_kb.py` (nơi đã chứng minh `KbIngest` idempotent/ fence).

Hai thứ chỉ script này có: (1) `ingest_all()` nối `load_callisto()` → `KbIngest` chạy trọn 140
chunk trên pool non-owner của fixture; (2) `main()` thiếu DSN phải **báo lỗi to**, không chạy câm.

Nạp module bằng `spec_from_file_location` như `test_mutation_sweep.py`: `scripts/` không phải package
nên không import thẳng được.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ingest_callisto.py"
_spec = importlib.util.spec_from_file_location("ingest_callisto", _SCRIPT)
assert _spec is not None and _spec.loader is not None
ingest_callisto = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ingest_callisto
_spec.loader.exec_module(ingest_callisto)


async def test_ingest_all_nap_tron_corpus(pool: object) -> None:
    """`ingest_all` phải nạp đúng 140 chunk (Callisto Handbook D12) qua pool non-owner. Số 140 neo
    vào `callisto-doc-schema.md` §8b; `test_doc_factory.py` là chuông chính khi corpus đổi."""
    written = await ingest_callisto.ingest_all(pool)  # type: ignore[arg-type]
    assert written == 140


async def test_ingest_all_idempotent_chay_lai_van_140(pool: object) -> None:
    """Chạy lại trên bảng đã có dữ liệu vẫn ra 140 (upsert `ON CONFLICT`), không vỡ, không nhân đôi
    số ghi — đây là tính chất demo dựa vào để lặp lệnh mà không phải dọn bảng."""
    assert await ingest_callisto.ingest_all(pool) == 140  # type: ignore[arg-type]
    assert await ingest_callisto.ingest_all(pool) == 140  # type: ignore[arg-type]


def test_main_thieu_dsn_bao_loi_to(monkeypatch: pytest.MonkeyPatch) -> None:
    """Thiếu `STUDIO_DATABASE_URL` → `SystemExit` có hướng dẫn, KHÔNG chạy câm rồi vỡ sâu trong pool.
    Không cần DB: fail trước khi chạm psycopg."""
    monkeypatch.delenv("STUDIO_DATABASE_URL", raising=False)
    with pytest.raises(SystemExit) as exc:
        ingest_callisto.main()
    assert "STUDIO_DATABASE_URL" in str(exc.value)
