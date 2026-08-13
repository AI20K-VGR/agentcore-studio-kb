"""Anti-tamper meta-test (F5) — asserts `test_leak.py`'s real cross-tenant EXCLUSION assertions
are still present in source. Guards against someone quietly hollowing the leak-test out (or
swapping it for `pytest.raises(NotImplementedError)`) to fake green instead of implementing
`kb.search` honestly. This test itself must stay GREEN (not xfail)."""

from __future__ import annotations

from pathlib import Path

_LEAK_TEST_PATH = Path(__file__).parent / "test_leak.py"
_NO_BYPASS_PATH = Path(__file__).parent / "test_no_bypass.py"


def test_leak_file_still_has_t1_t6_assertions() -> None:
    leak_source = _LEAK_TEST_PATH.read_text(encoding="utf-8")

    # T1 IDOR — the requesting tenant's own chunk must be INCLUDED (positive teeth so a
    # []-returning impl can't false-pass), the cross-tenant chunk must be EXCLUDED, and every
    # returned item must belong to the requesting tenant.
    # (Tên field theo D-13 #25: `item.tenant_id` UUID — răng không đổi, chỉ đổi tên/kiểu.)
    assert 'assert "chunk-a-1" in result_chunk_ids' in leak_source
    assert 'assert "chunk-b-1" not in result_chunk_ids' in leak_source
    assert "assert all(item.tenant_id == TENANT_A for item in results)" in leak_source

    # T6 label-spoof — closed UPSTREAM at the interpreter (`interpreter.py:324-325`, engine #111); the
    # kb-layer placeholder in `test_leak.py` was retired (D20). Its kb-lane teeth moved to
    # `test_no_bypass.py`, so repoint the anti-tamper here: an hr-only caller must still SEE the hr
    # chunk (positive tooth) and NEVER the finance chunk (the silent role-leak vector). Guard those
    # strings so nobody hollows the no-bypass proof.
    no_bypass_source = _NO_BYPASS_PATH.read_text(encoding="utf-8")
    assert 'assert "ankor-salary-001#c1" in ids' in no_bypass_source
    assert 'assert "ankor-budget-001#c1" not in ids' in no_bypass_source
    assert 'assert all(h.section_role == "hr" for h in hits)' in no_bypass_source
