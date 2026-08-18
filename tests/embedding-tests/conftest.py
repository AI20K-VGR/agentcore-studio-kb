"""Fixtures cho bộ eval embedding. Logic thuần ở `_harness.py`.

`embedding_provider` là seam model-agnostic: mặc định baseline dim-8; model ứng viên override fixture
này (conftest riêng / plugin) để chấm trên CÙNG harness và so với baseline đóng băng.
"""

from __future__ import annotations

import _harness as H
import pytest


@pytest.fixture(scope="session")
def embedding_provider() -> object:
    """Provider embedding-under-test. Mặc định baseline dim-8 (`derive_vector`)."""
    return H.BaselineDim8()


@pytest.fixture(scope="session")
def report(embedding_provider: object) -> dict[str, H.CaseResult]:
    """Chấm toàn bộ case một lần cho provider → {case_id: CaseResult}. Cả test per-case lẫn gate đọc
    từ đây (order-independent)."""
    return H.build_report(embedding_provider)


@pytest.fixture(scope="session")
def corpus_texts(embedding_provider: object) -> dict[str, str]:
    """{chunk_id: text} của corpus 2.0 — để test integrity soi token trùng (near-miss)."""
    _, texts = H.build_retriever(embedding_provider)
    return texts
