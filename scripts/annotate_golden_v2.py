"""Annotation harness cho golden-set **Callisto 2.0** — trace nhãn từ retrieval thật + máy-kiểm
uniqueness. Không embedding, không DB (StaticKbSearch chấm token-overlap tất định).

    # 1) Trace: chọn expected_citation từ retrieval THẬT trên corpus 2.0 (không gõ tay)
    uv run --package agentcore-studio-kb python packages/kb/scripts/annotate_golden_v2.py \
        --tenant ankor --roles hr --query "được làm việc từ xa tối đa mấy ngày một tuần"

    # 2) Verify-unique: cụm expected có DUY NHẤT trong (tenant, roles) và VẮNG ở tenant kia cùng role?
    uv run --package agentcore-studio-kb python packages/kb/scripts/annotate_golden_v2.py \
        --tenant ankor --roles hr --expect-phrase "tối đa 2 ngày/tuần"

Vì sao tách khỏi `annotate_golden.py` (1.0): (a) corpus khác (`load_corpus_v2` đọc
`docs/callisto-2.0/{tenant}/{role}-{name}.md`, không front-matter); (b) 2.0 **đối xứng gương** — 2
tenant cùng tên file + chia sẻ câu boilerplate nguyên văn, nên "grounded" thôi CHƯA đủ: một cụm rút từ
câu boilerplate grounded ở CẢ hai tenant → fence-leak vẫn PASS oan. Bởi vậy uniqueness phải là **máy
kiểm**, không mắt thường (ở 800 chunk không soi tay được).

Kỷ luật (khớp header golden 1.0): mọi `expected_citation` là `chunk_id` THẬT do `load_corpus_v2` phát;
mọi `expected` phải (1) grounded trong đúng chunk đó, (2) DUY NHẤT trong (expected_tenant,
expected_section_role), (3) VẮNG ở tenant kia cùng role (điều kiện làm phép thử fence có nghĩa).
`_contains_phrase` **import thẳng từ `studio_evalhub.harness`** — KHÔNG viết lại: nhãn phải khớp đúng
ngữ nghĩa harness sẽ chấm, một bản gần-đúng là cách tạo nhãn qua-check-này-mà-fail-harness.

Rank-verify (search có xếp expected vào top-k **ngữ nghĩa** không) **hoãn** sang parity gate — phụ
thuộc embedding thật, ngoài phạm vi Phase B.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from studio_evalhub.harness import _contains_phrase  # SSOT ground-check — không viết lại (xem docstring)
from studio_kb.doc_factory_core import TENANT_IDS, Chunk, resolve_tenant_id
from studio_kb.doc_factory_v2 import load_corpus_v2
from studio_kb.static_search import StaticKbSearch

CORPUS_2_0 = Path(__file__).resolve().parents[1] / "docs" / "callisto-2.0"
"""`packages/kb/docs/callisto-2.0/` — corpus 2.0 (80 doc, `{tenant}/{role}-{name}.md`)."""


def _load_kb() -> tuple[StaticKbSearch, list[Chunk]]:
    """StaticKbSearch tiêm chunk 2.0 (KHÔNG dùng `load_callisto` 1.0 mặc định). Trả cả list chunk thô
    để máy-kiểm uniqueness quét toàn corpus."""
    chunks = load_corpus_v2(CORPUS_2_0)
    return StaticKbSearch(chunks=chunks), chunks


async def _trace(kb: StaticKbSearch, tenant: str, roles: list[str], query: str, top_k: int) -> None:
    hits = await kb.search(query, resolve_tenant_id(tenant), roles, top_k)
    print(f"# TRACE tenant={tenant} roles={roles} query={query!r}")
    if not hits:
        print("# (rỗng) — scope này không token-khớp gì. Nếu là case REFUSAL thì đúng ý (expected_citation: []).")
    for rank, h in enumerate(hits, 1):
        snippet = h.text.replace("\n", " ")[:70]
        print(f"{rank:>2}. {h.chunk_id:<34} role={h.section_role:<12} score={h.score:.4f}  {snippet}")


def _verify_unique(chunks: list[Chunk], expected: str, tenant: str, roles: list[str]) -> bool:
    """Đếm chunk mà `_contains_phrase(chunk.text, expected)` đúng, tách theo scope. In verdict.

    ĐẠT khi: đúng 1 chunk in-scope (tenant người-giữ + role) VÀ 0 chunk ở tenant-kia-cùng-role.
    """
    want_tenant = resolve_tenant_id(tenant)
    allowed = set(roles)
    other_tenants = {resolve_tenant_id(s): s for s in TENANT_IDS if s != tenant}

    in_scope: list[str] = []
    other_same_role: list[str] = []
    elsewhere: list[str] = []
    for c in chunks:
        if not _contains_phrase(c.text, expected):
            continue
        if c.tenant_id == want_tenant and c.section_role in allowed:
            in_scope.append(c.chunk_id)
        elif c.tenant_id in other_tenants and c.section_role in allowed:
            other_same_role.append(c.chunk_id)
        else:
            elsewhere.append(c.chunk_id)

    print(f"# VERIFY-UNIQUE expected={expected!r} tenant={tenant} roles={roles}")
    print(f"#   in-scope ({tenant}+{roles}): {in_scope or '∅'}")
    print(f"#   tenant-kia cùng role       : {other_same_role or '∅'}")
    print(f"#   nơi khác (role/tenant khác): {elsewhere or '∅'}")
    ok = len(in_scope) == 1 and len(other_same_role) == 0
    print(
        f"#   => {'ĐẠT ✓' if ok else 'HỎNG ✗'} (cần đúng 1 in-scope, 0 tenant-kia-cùng-role) → citation {in_scope[:1]}"
    )
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tenant", required=True, choices=sorted(TENANT_IDS), help="slug tenant người hỏi")
    parser.add_argument("--roles", required=True, nargs="+", help="section_roles người hỏi giữ")
    parser.add_argument("--query", default=None, help="câu hỏi — bật chế độ trace")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--expect-phrase", default=None, help="cụm expected — bật máy-kiểm uniqueness")
    args = parser.parse_args()

    kb, chunks = _load_kb()
    if args.query is not None:
        asyncio.run(_trace(kb, args.tenant, args.roles, args.query, args.top_k))
    if args.expect_phrase is not None:
        ok = _verify_unique(chunks, args.expect_phrase, args.tenant, args.roles)
        raise SystemExit(0 if ok else 1)
    if args.query is None and args.expect_phrase is None:
        parser.error("cần --query (trace) hoặc --expect-phrase (verify-unique)")


if __name__ == "__main__":
    main()
