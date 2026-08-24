import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, "packages/kb/src")
sys.path.insert(0, "apps/studio/src")

from dotenv import load_dotenv

load_dotenv()

from studio_app.providers.factory import build_embedding  # noqa: E402
from studio_kb.chunk_window import cut_window  # noqa: E402

BENCH = Path(
    "/private/tmp/claude-501/-Users-nguyendonganh-agentcore-studio-kit/"
    "768f885a-db4e-44a7-9050-235af71ab048/scratchpad/bench"
)
DATA_DIR = Path("packages/kb/data")
_TENANT = UUID("a0000000-0000-0000-0000-000000000001")

CONFIGS = {
    "200_50": {"size": 200, "overlap": 50},
    "500_100": {"size": 500, "overlap": 100},
    "850_170": {"size": 850, "overlap": 170},
}


async def main() -> None:
    embedding = build_embedding()
    manifest = json.loads((BENCH / "manifest.json").read_text(encoding="utf-8"))

    for cfg_name, params in CONFIGS.items():
        all_chunks = []
        for src_name in manifest:
            text = (BENCH / f"{src_name}.extracted.txt").read_text(encoding="utf-8")
            doc_id = src_name  # ổn định, không cần slug — chỉ dùng nội bộ benchmark
            chunks = cut_window(text, doc_id, _TENANT, "bench", size=params["size"], overlap=params["overlap"])
            for c in chunks:
                all_chunks.append({"doc": src_name, "chunk_id": c.chunk_id, "text": c.text, "n_words": len(c.text.split())})

        print(f"[{cfg_name}] tổng {len(all_chunks)} chunk từ {len(manifest)} file")

        # embed theo lô <=90 (khớp _BATCH thật của GatewayEmbedding, nhưng embed() tự batch nội bộ
        # rồi — gọi thẳng 1 lần với toàn bộ list, để provider tự chia lô)
        texts = [c["text"] for c in all_chunks]
        vectors = await embedding.embed(texts)
        for c, v in zip(all_chunks, vectors, strict=True):
            c["vector"] = v

        out_path = BENCH / f"chunks_{cfg_name}.json"
        out_path.write_text(json.dumps(all_chunks, ensure_ascii=False), encoding="utf-8")
        dims = {len(c["vector"]) for c in all_chunks}
        print(f"[{cfg_name}] đã embed xong, dim={dims}, ghi {out_path.name}")


if __name__ == "__main__":
    asyncio.run(main())
