"""Local test-infra override, scoped to THIS directory only.

Windows defaults `asyncio` to `ProactorEventLoop`, which `psycopg` async refuses ("Psycopg cannot
use the 'ProactorEventLoop' to run in async mode"). The kit-root `conftest.py` (repo cha) không có
fix này, và `apps/studio/tests/conftest.py`/`packages/workbench/tests/conftest.py` chỉ áp dụng cho
thư mục của chúng (pytest merge `conftest.py` theo cây thư mục, không lan ngang sang
`packages/kb/tests/`) — nên `test_rls_framework.py` trước giờ luôn treo/lỗi `PoolTimeout` khi có
DSN thật trên Windows, chưa từng thật sự chạy để lộ ra (phát hiện trong lúc dựng test cho kb#47
review). Thêm cùng fixture ở đây, cùng mẫu đã áp cho `apps/studio`/`packages/workbench`.
"""

from __future__ import annotations

import asyncio
import sys

import pytest


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()
