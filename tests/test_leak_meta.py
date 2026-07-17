"""Anti-tamper meta-test (F5) — asserts `test_leak.py`'s real cross-tenant EXCLUSION assertions
are still present in source. Guards against someone quietly hollowing the leak-test out (or
swapping it for `pytest.raises(NotImplementedError)`) to fake green instead of implementing
`kb.search` honestly. This test itself must stay GREEN (not xfail)."""

from __future__ import annotations

from pathlib import Path

_LEAK_TEST_PATH = Path(__file__).parent / "test_leak.py"


def test_leak_file_still_has_t1_t6_assertions() -> None:
    source = _LEAK_TEST_PATH.read_text(encoding="utf-8")

    # T1 IDOR — the requesting tenant's own chunk must be INCLUDED (positive teeth so a
    # []-returning impl can't false-pass), the cross-tenant chunk must be EXCLUDED, and every
    # returned item must belong to the requesting tenant.
    assert 'assert "chunk-a-1" in result_chunk_ids' in source
    assert 'assert "chunk-b-1" not in result_chunk_ids' in source
    assert 'assert all(item.tenant == "tenant-a" for item in results)' in source

    # T6 label-spoof — a confidential chunk must be excluded from the search response.
    assert 'assert "chunk-confidential" not in result_chunk_ids' in source
