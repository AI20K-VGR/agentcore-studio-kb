"""Cache vector theo `sha256(model|dim|text)` — thứ làm bảng so provider TÁI LẬP ĐƯỢC TỪ `main` mà không cần
API key (`kb#38` DoD, và INV-4 "CI chạy 100% recorded fixtures").

## Vì sao nhị phân, không phải JSON

1100 text (800 chunk + 300 query) × 2048 chiều. Đo thật ba định dạng:

| định dạng | dung lượng |
|---|---|
| JSON float đầy đủ | 46.8 MB |
| JSON làm tròn 6 chữ số | 23.4 MB |
| **float32 nhị phân** | **9.0 MB** |
| float16 nhị phân | 4.5 MB |

Chọn **float32**: float16 chỉ giữ ~3 chữ số thập phân, đủ để lật thứ hạng của hai chunk có cosine
gần bằng nhau — mà THỨ HẠNG chính là thứ bộ eval này đo. Tiết kiệm 4.5 MB không đáng đổi lấy rủi ro
cache tự nó làm sai con số nó được sinh ra để bảo toàn.

## Vì sao `array` chứ không `numpy`

`numpy` CÓ trong venv workspace nhưng KHÔNG phải dependency khai báo của `agentcore-studio-kb`. CI
dựng bằng `uv sync --frozen`, nên dựa vào một package chỉ tình cờ có mặt là cách CI đỏ ở máy khác.
`array.array("f")` của stdlib làm đúng việc này.

## Bố cục file

    <tên>.bin          N × dim × 4 byte, float32 **little-endian** (chuẩn hoá tường minh, xem `_LE`)
    <tên>.index.json   {"model", "dim", "count", "keys": {sha256hex: chỉ số dòng}}

Tách index ra JSON để `git diff` còn đọc được phần siêu dữ liệu, và để thêm text mới chỉ cần nối
thêm vào cuối `.bin` — không phải viết lại toàn bộ.
"""

from __future__ import annotations

import hashlib
import json
import sys
from array import array
from pathlib import Path

_HERE = Path(__file__).resolve().parent
CACHE_DIR = _HERE / "cache"

_FLOAT32 = "f"
_BYTES_PER_FLOAT = 4
_LE = "little"
"""Byte-order ĐÓNG BĂNG của file `.bin`.

`array.tofile()` ghi theo byte-order của MÁY. Không ghim lại thì cache do máy little-endian ghi sẽ
đọc ra số vô nghĩa trên máy big-endian — hỏng CÂM (vector vẫn đúng số chiều, chỉ toàn giá trị rác),
đúng loại lỗi mà "recorded fixture" phải chống chứ không được mắc phải.
"""


def cache_key(model: str, dim: int, text: str) -> str:
    """Khoá cache = `sha256(model | dim | text)`.

    Gộp `model` và `dim` vào khoá chứ không chỉ băm `text`: cùng một câu qua `gemini-embedding-001`
    ở 2048 và ở 1536 là HAI vector khác nhau. Băm mỗi text thì lần đổi `dim` đầu tiên sẽ đọc trúng
    vector cũ sai số chiều — và nó chỉ lộ ra khi ai đó tình cờ đối chiếu lại.
    """
    return hashlib.sha256(f"{model}|{dim}|{text}".encode()).hexdigest()


class VectorCache:
    """Cache đọc-ghi cho MỘT (model, dim). Đọc toàn bộ vào RAM lúc mở (9 MB — rẻ hơn nhiều lần seek)."""

    def __init__(self, name: str, *, model: str, dim: int, cache_dir: Path | None = None) -> None:
        base = (cache_dir or CACHE_DIR) / name
        self._bin = base.with_suffix(".bin")
        self._index = base.with_suffix(".index.json")
        self.model = model
        self.dim = dim
        self._keys: dict[str, int] = {}
        self._rows: array[float] = array(_FLOAT32)
        self._load()

    def _load(self) -> None:
        if not self._index.exists() or not self._bin.exists():
            return
        meta = json.loads(self._index.read_text(encoding="utf-8"))
        if meta["model"] != self.model or meta["dim"] != self.dim:
            raise ValueError(
                f"cache {self._index.name} là của ({meta['model']}, dim={meta['dim']}), "
                f"không phải ({self.model}, dim={self.dim}) — đừng trộn hai không gian vector vào một file"
            )
        self._keys = meta["keys"]
        # So KÍCH THƯỚC FILE THẬT với con số index khai — không phải so với số float vừa đọc.
        # `fromfile(fh, n)` chỉ đọc đúng `n` float, nên một `.bin` DÀI HƠN index khai sẽ tự khớp với
        # chính nó và lọt qua mọi phép so sau khi đọc. Đó đúng là trạng thái một lần ghi đứt giữa
        # chừng để lại, và nó hỏng câm: mọi vector từ chỗ lệch trở đi thuộc về text khác.
        expected = len(self._keys) * self.dim * _BYTES_PER_FLOAT
        actual = self._bin.stat().st_size
        if actual != expected or meta["count"] != len(self._keys):
            raise ValueError(
                f"cache hỏng: {self._bin.name} nặng {actual} byte, index khai "
                f"{len(self._keys)} vector × {self.dim} chiều = {expected} byte (count={meta['count']})"
            )
        # Chỉ số dòng phải là SONG ÁNH với 0..N-1. Hai phép kiểm trên (kích thước file, `count`)
        # đều BẤT BIẾN dưới phép trùng chỉ số: sửa `index.json` cho hai khoá cùng trỏ dòng 0 thì
        # `len(keys)`, `count` và `.bin` đều không đổi — cache mở được, hai khoá đọc ra CÙNG một
        # vector, và một dòng mồ côi trong `.bin`. `index.json` là JSON >1000 dòng ĐÃ COMMIT mà mọi
        # lần re-record sẽ nối thêm vào; một lần giải conflict merge bằng tay là đủ gây ra đúng
        # trạng thái đó, và hậu quả là "mọi vector từ chỗ lệch trở đi thuộc về text khác".
        if sorted(self._keys.values()) != list(range(len(self._keys))):
            raise ValueError(f"cache hỏng: chỉ số dòng trong {self._index.name} không phải 0..N-1 (trùng hoặc thiếu)")
        with self._bin.open("rb") as fh:
            self._rows.fromfile(fh, len(self._keys) * self.dim)
        if sys.byteorder != _LE:  # pragma: no cover — CI/dev đều little-endian
            self._rows.byteswap()

    def __len__(self) -> int:
        return len(self._keys)

    def get(self, text: str) -> list[float] | None:
        row = self._keys.get(cache_key(self.model, self.dim, text))
        if row is None:
            return None
        return self._rows[row * self.dim : (row + 1) * self.dim].tolist()

    def put(self, text: str, vector: list[float]) -> None:
        """Thêm một vector. Đã có khoá thì BỎ QUA, không ghi đè — cache là bản ghi bất biến của một
        lần đo; ghi đè âm thầm sẽ làm hai lần chạy cho hai kết quả mà `git diff` chỉ thấy blob đổi."""
        if len(vector) != self.dim:
            raise ValueError(f"vector {len(vector)} chiều, cache khai {self.dim}")
        key = cache_key(self.model, self.dim, text)
        if key in self._keys:
            return
        self._keys[key] = len(self._keys)
        self._rows.extend(vector)

    def flush(self) -> None:
        """Ghi xuống đĩa. Ghi qua file tạm rồi `replace` — đứt giữa chừng (Ctrl-C, hết quota) không
        để lại `.bin` lệch với `.index.json`, vốn là một cache hỏng câm."""
        self._bin.parent.mkdir(parents=True, exist_ok=True)
        rows = self._rows
        if sys.byteorder != _LE:  # pragma: no cover
            rows = array(_FLOAT32, self._rows)
            rows.byteswap()
        tmp_bin = self._bin.with_suffix(".bin.tmp")
        with tmp_bin.open("wb") as fh:
            rows.tofile(fh)
        tmp_index = self._index.with_suffix(".json.tmp")
        tmp_index.write_text(
            json.dumps(
                {"model": self.model, "dim": self.dim, "count": len(self._keys), "keys": self._keys},
                ensure_ascii=False,
                indent=0,
            ),
            encoding="utf-8",
        )
        tmp_bin.replace(self._bin)
        tmp_index.replace(self._index)

    @property
    def size_bytes(self) -> int:
        return len(self._rows) * _BYTES_PER_FLOAT
