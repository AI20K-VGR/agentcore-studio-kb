"""`scripts/ingest_callisto_v2.py` — CLI ingest corpus 2.0 qua `KbPipeline` (cutover Phase C). Kiểm
phần **glue** riêng của script, KHÔNG lặp `test_pipeline.py` (nơi đã chứng minh `index` idempotent/fence).

Hai thứ chỉ script này có: (1) `ingest_all()` nối `load_corpus_v2()` → `KbPipeline.embed_invoke`/`index`
chạy trọn 800 chunk trên pool non-owner của fixture; (2) `main()` thiếu DSN phải **báo lỗi to**.

Nạp module bằng `spec_from_file_location` như `test_ingest_script.py`: `scripts/` không phải package.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ingest_callisto_v2.py"
_spec = importlib.util.spec_from_file_location("ingest_callisto_v2", _SCRIPT)
assert _spec is not None and _spec.loader is not None
ingest_callisto_v2 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ingest_callisto_v2
_spec.loader.exec_module(ingest_callisto_v2)


async def test_ingest_all_nap_tron_corpus_2_0(pool: object) -> None:
    """`ingest_all` phải nạp đúng 800 chunk (80 doc 2.0) qua pool non-owner. Số 800 neo vào
    `docs/callisto-2.0/` (40 doc/tenant × ~10 chunk); `test_doc_factory_v2.py` là chuông khi corpus đổi."""
    written = await ingest_callisto_v2.ingest_all(pool)
    assert written == 800


async def test_ingest_all_idempotent_chay_lai_van_800(pool: object) -> None:
    """Chạy lại trên bảng đã có dữ liệu vẫn ra 800 (upsert `ON CONFLICT` trong `index`), không nhân đôi."""
    assert await ingest_callisto_v2.ingest_all(pool) == 800
    assert await ingest_callisto_v2.ingest_all(pool) == 800


def test_main_thieu_dsn_bao_loi_to(monkeypatch: pytest.MonkeyPatch) -> None:
    """Thiếu `STUDIO_DATABASE_URL` → `SystemExit` có hướng dẫn, KHÔNG chạy câm. Không cần DB."""
    monkeypatch.delenv("STUDIO_DATABASE_URL", raising=False)
    with pytest.raises(SystemExit) as exc:
        ingest_callisto_v2.main()
    assert "STUDIO_DATABASE_URL" in str(exc.value)
