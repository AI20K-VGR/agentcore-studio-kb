"""kb.* schema DDL seam (schema-per-quadrant, Decision #4).

`ensure_all_schemas()` (apps/studio/src/studio_app/core/schema.py, Phase 3) direct-imports this
module and calls `ddl()` via the ADMIN (`studio_owner`) pool — that ownership is what lets `FORCE
ROW LEVEL SECURITY` below bite the owner too, instead of the owner silently bypassing the fence.

Fence mechanism (F10, plan.md Decision #3): `ENABLE`+`FORCE ROW LEVEL SECURITY` plus a policy with
BOTH `USING` (reads) and `WITH CHECK` (writes) keyed off `current_setting('app.tenant_id', true)`
— the `true` argument makes an unset setting resolve to `NULL` rather than raising, and
`tenant_id = NULL` is never true in SQL, so an unset session sees/writes 0 rows (fail-closed, not
"everything"). `CREATE EXTENSION vector` is deliberately NOT here — it runs once, as the
`postgres` superuser, from `docker/postgres-init/01-extensions.sql` (Phase 3): both `studio_owner`
and `studio_app` are `NOSUPERUSER` and cannot create extensions at boot.
"""

from __future__ import annotations

# Embedding vector dimension — pinned HERE (not in apps/studio) because quadrant packages may
# import ONLY `studio_contracts` (.importlinter layers-contract) and must never import
# `studio_app`. Matches `FakeEmbedding.dim` (apps/studio/src/studio_app/providers/fakes.py, the
# CI-fixture EmbeddingService double P4 ships). AIE-1's graded `EmbeddingService` (stub-local +
# gateway, R-SPEC A1#5/A4) must produce vectors of this same width when it lands; re-pin this
# constant + `FakeEmbedding.dim` together if that width ever changes `[PRIOR]`.
EMBEDDING_DIM = 8

_KB_DDL = f"""
CREATE SCHEMA IF NOT EXISTS kb;

CREATE TABLE IF NOT EXISTS kb.chunks (
    chunk_id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    tenant_id TEXT NOT NULL,
    section_role TEXT NOT NULL,
    text TEXT NOT NULL,
    embedding vector({EMBEDDING_DIM}),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS kb_chunks_embedding_hnsw_idx
    ON kb.chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS kb_chunks_tenant_id_idx ON kb.chunks (tenant_id);

ALTER TABLE kb.chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb.chunks FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS kb_chunks_tenant_isolation ON kb.chunks;
CREATE POLICY kb_chunks_tenant_isolation ON kb.chunks
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
"""


def ddl() -> str:
    """Return this quadrant's idempotent DDL — safe to execute any number of times (`CREATE ...
    IF NOT EXISTS` throughout; the policy is `DROP ... IF EXISTS` then recreated identically)."""
    return _KB_DDL
