"""Cost table per-run — bảng CLI thay cho cost dashboard (bút DE, D19, #120; DESCOPE NẤC 4).

    docker compose -f docker-compose.test.yml up -d --wait
    export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test
    uv run --python 3.14 --package agentcore-studio-kb python packages/kb/scripts/cost_table.py [tenant]

In cost per-run cho một tenant. "Dashboard" tụt nấc thành **bảng CLI** (DESCOPE.md §3.2) — vẫn đọc **cùng
nguồn số** (`obs.trace_events` → `aggregate_run_cost`), KHÔNG mặt nào tự tính lại (§4.1). Pool non-owner
(`STUDIO_DATABASE_URL`, role `studio_app`) như `ingest_callisto.py`; chỉ ĐỌC, không dựng lại đường ghi.
"""

from __future__ import annotations

import asyncio
import os
import sys

from psycopg_pool import AsyncConnectionPool
from studio_kb.cost import PgCostReader
from studio_kb.doc_factory import resolve_tenant_id

_DSN_ENV = "STUDIO_DATABASE_URL"


async def _run(dsn: str, tenant: str) -> None:
    tenant_id = resolve_tenant_id(tenant)
    pool = AsyncConnectionPool(dsn, min_size=1, max_size=4, open=False)
    await pool.open(wait=True, timeout=10)
    try:
        reader = PgCostReader(pool)
        run_ids = await reader.list_run_ids(tenant_id)
        print(f"cost table — tenant {tenant} ({tenant_id}) — {len(run_ids)} run")
        print(f"  {'run_id':<24} {'events':>6} {'prompt':>8} {'completion':>11} {'cost':>12}")
        total = 0.0
        drift_runs: list[str] = []
        for run_id in run_ids:
            rc, mismatches = await reader.read_run_cost_with_drift(run_id, tenant_id)
            total += rc.cost
            flag = "  ⚠ giá lệch" if mismatches else ""
            print(
                f"  {rc.run_id:<24} {rc.event_count:>6} {rc.prompt_tokens:>8} "
                f"{rc.completion_tokens:>11} {rc.cost:>12.6f}{flag}"
            )
            if mismatches:
                drift_runs.append(run_id)
        print(f"  {'TỔNG':<24} {'':>6} {'':>8} {'':>11} {round(total, 6):>12.6f}")
        if drift_runs:
            print(
                f"⚠ CẢNH BÁO: {len(drift_runs)} run có event lệch nguồn giá (§4.1) — emit không dùng "
                f"cost_of? kiểm: {', '.join(drift_runs)}"
            )
    finally:
        await pool.close()


def main() -> None:
    dsn = os.environ.get(_DSN_ENV)
    if not dsn:
        raise SystemExit(
            f"{_DSN_ENV} chưa đặt — cần pg sống. Chạy trước:\n"
            "  docker compose -f docker-compose.test.yml up -d --wait\n"
            f"  export {_DSN_ENV}=postgresql://studio_app:changeme@localhost:5433/studio_test"
        )
    tenant = sys.argv[1] if len(sys.argv) > 1 else "ankor"
    asyncio.run(_run(dsn, tenant))


if __name__ == "__main__":
    main()
