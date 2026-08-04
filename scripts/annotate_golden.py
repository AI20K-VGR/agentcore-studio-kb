"""Annotation harness — gán nhãn golden-set bằng cách TRÍCH từ retrieval thật, không gõ tay (D12, DE).

    uv run --package agentcore-studio-kb python packages/kb/scripts/annotate_golden.py \
        --tenant ankor --roles public --query "làm việc từ xa mấy ngày một tuần"

    # kiểm 1 nhãn đã có: chunk kỳ vọng có nằm trong scope truy xuất không?
    uv run --package agentcore-studio-kb python packages/kb/scripts/annotate_golden.py \
        --tenant ankor --roles hr --query "ngân sách đào tạo" --expect ankor-training-001#c1

Vì sao có script này (`callisto-doc-schema.md` §8b, `docs/format.md` §10 / smoke-10 header):
golden-set D16 phải sinh **từ chính doc-factory** — mọi `expected_citation` chép từ `chunk_id` thật
do máy cắt phát ra, KHÔNG gõ tay. Gõ tay lệch một ký tự thì mọi case ra 0 điểm mà **không lỗi nào
nổi lên** (`format.md` §2). Kỷ luật D6 đã làm bằng tay ("chạy qua StaticKbSearch thật trước khi viết
nhãn"); script này biến kỷ luật đó thành công cụ để dựng 30 case (D16) không lệch.

Đây là **skeleton D12**, không phải bộ 30 case đủ (đó là DoD D16). Nó nuôi:
- **golden-set** (D16, AIE-2): mỗi dòng in ra là ứng viên `expected_citation` đã kiểm là truy xuất
  được TRONG scope — dán thẳng vào yaml, hết đường gõ sai.
- **expected chunks cho chunking×embedding** (D14, AIE-1): cùng đường trích, cùng `chunk_id` bền.

KHÔNG parse yaml ở đây (kb cố ý không kéo pyyaml — `doc_factory.parse_front_matter` docstring): script
chỉ ĐỌC corpus qua doc-factory và chạy StaticKbSearch, in ra ứng viên nhãn. Viết yaml vẫn là việc tay
có review — script chỉ bảo đảm `chunk_id` là thật.
"""

from __future__ import annotations

import argparse
import asyncio

from studio_kb.doc_factory import TENANT_IDS, resolve_tenant_id
from studio_kb.static_search import StaticKbSearch


async def _candidates(tenant: str, roles: list[str], query: str, top_k: int) -> list[tuple[str, str, float]]:
    kb = StaticKbSearch()
    hits = await kb.search(query, resolve_tenant_id(tenant), roles, top_k)
    return [(h.chunk_id, h.section_role, h.score) for h in hits]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tenant", required=True, choices=sorted(TENANT_IDS), help="slug tenant người hỏi")
    parser.add_argument("--roles", required=True, nargs="+", help="section_roles người hỏi giữ (server-quyết ở thật)")
    parser.add_argument("--query", required=True, help="câu hỏi")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--expect", default=None, help="chunk_id kỳ vọng — kiểm nó có nằm trong scope không")
    args = parser.parse_args()

    cands = asyncio.run(_candidates(args.tenant, args.roles, args.query, args.top_k))

    print(f"# tenant={args.tenant} roles={args.roles} query={args.query!r}")
    if not cands:
        print("# (rỗng) — scope này không token-khớp gì. Nếu đây là case REFUSAL thì đúng ý:")
        print("#   expected: refusal   expected_citation: []")
    for rank, (chunk_id, role, score) in enumerate(cands, 1):
        print(f"{rank:>2}. {chunk_id:<28} role={role:<12} score={score:.4f}")

    if args.expect is not None:
        found = any(chunk_id == args.expect for chunk_id, _, _ in cands)
        verdict = "TRUY XUẤT ĐƯỢC trong scope ✓" if found else "KHÔNG nằm trong scope ✗ (nhãn sẽ ra 0 điểm)"
        print(f"# --expect {args.expect}: {verdict}")
        raise SystemExit(0 if found else 1)


if __name__ == "__main__":
    main()
