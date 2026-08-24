import json
import sys
from pathlib import Path

sys.path.insert(0, "packages/kb/src")

from studio_kb.extract import extract_text  # noqa: E402

DATA_DIR = Path("packages/kb/data")
OUT_DIR = Path(
    "/private/tmp/claude-501/-Users-nguyendonganh-agentcore-studio-kit/"
    "768f885a-db4e-44a7-9050-235af71ab048/scratchpad/bench"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

docs = {}
for f in sorted(DATA_DIR.iterdir()):
    if f.suffix not in {".md", ".txt", ".docx"}:
        continue
    raw = f.read_bytes()
    text = extract_text(f.name, raw)
    words = len(text.split())
    docs[f.name] = {"words": words, "chars": len(text)}
    safe_name = f.name.replace("/", "_")
    (OUT_DIR / f"{safe_name}.extracted.txt").write_text(text, encoding="utf-8")
    print(f"{f.name}: {words} từ, {len(text)} ký tự")

(OUT_DIR / "manifest.json").write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nTổng: {sum(d['words'] for d in docs.values())} từ, {len(docs)} file")
