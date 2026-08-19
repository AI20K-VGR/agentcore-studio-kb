"""Chọn ngưỡng tuyệt đối cho `decoy_fall` — **CHỈ trên validation set** (kb#38, sai sót #2).

    uv run --python 3.14 python packages/kb/tests/embedding-tests/tune_decoy_threshold.py

Chạy offline, không API key. In ra toàn bộ phép dẫn để ai cũng kiểm lại được từng bước, rồi so với
`H.ABSOLUTE_MAX["decoy_fall"]` đang commit.

## Vì sao phải có file này

Ngưỡng 0.35 của bản báo cáo trước được chọn bằng cách quét trên **chính 300 case dùng để báo cáo**
(`embedding_report.md` §Gate). Fit tham số vào nhiễu của tập mình sẽ công bố ⇒ số công bố đẹp hơn
thực tế một cách có hệ thống, và không còn tập độc lập nào để phát hiện. Đây là gạch DoD cuối cùng
của `kb#38` mà kb tự làm được.

## Luật chọn — giữ nguyên công thức cũ, chỉ đổi TẬP

`decoy_fall` **không dùng để CHỌN model** (model càng hiểu nghĩa càng dễ bị near-miss decoy kéo lên
hạng #1 — nó xếp một model ngẫu nhiên lên đầu bảng). Nó chỉ là **thanh chắn an toàn một chiều**:
bắt provider bị bẫy một cách bệnh hoạn. Nên ngưỡng phải nằm TRÊN mọi giá trị mà một provider lành
mạnh có thể ra, cộng đủ biên để gate không nhấp nháy vì nhiễu lấy mẫu:

    ngưỡng = max(decoy_fall quan sát được, mọi provider × mọi tầng gate) + 2·SE

với `SE = sqrt(p(1-p)/n)` tại chính `p` quan sát được — **cùng công thức bản trước dùng**, để chênh
lệch kết quả đến từ việc đổi tập chứ không từ việc đổi luật.

## Giới hạn đã biết

Chỉ 3 provider chấm được offline (`dim-8`, `hash1024`, `gemini-001`). `bge-m3`/`e5-large` cần
`torch` nên không vào được phép lấy max — mà ở bản đo tay trước, `bge-m3` CHÍNH LÀ một trong hai
provider giữ giá trị cao nhất. Ngưỡng dẫn ra ở đây vì thế có thể **thấp hơn** ngưỡng đúng. Ghi rõ
trong report; vá được khi nào cache cho hai provider kia được commit.
"""

from __future__ import annotations

import math

import _harness as H
from providers import GeminiEmbedding
from studio_kb.embeddings import derive_vector

TUNE_PART = "validation"
"""Tập được phép tune. Đổi sang `"test"`/`"all"` là tái phạm đúng sai sót #2 của kb#38."""

Z = 2.0
"""Số SE cộng thêm. 2·SE ≈ 95% một phía — đủ để một provider tệ-ngang-mức-tệ-nhất-đã-thấy vẫn qua
chắc chắn, thay vì rớt gate một cách ngẫu nhiên theo lô case."""


class Hash1024:
    """`derive_vector` với `dim=1024` — cùng công thức baseline, chỉ nhiều ô băm hơn.

    Có mặt ở đây vì nó chạy local, miễn phí, và ở bản đo tay nó là một trong hai provider giữ
    `decoy_fall` cao nhất. Bỏ nó khỏi phép lấy max là tự làm ngưỡng thấp đi."""

    name = "hash1024"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [derive_vector(t, dim=1024) for t in texts]


def offline_providers() -> dict[str, object]:
    out: dict[str, object] = {"dim-8": H.BaselineDim8(), "hash1024": Hash1024()}
    gemini = GeminiEmbedding()
    if len(gemini.cache):
        out[gemini.name] = gemini
    else:
        print("CẢNH BÁO: thiếu cache gemini — phép lấy max KHÔNG đầy đủ, ngưỡng dẫn ra sẽ thấp hơn thực tế.")
    return out


def gated_strata() -> tuple[str, ...]:
    """Tầng nào THỰC SỰ bị gate bằng `decoy_fall` — đọc từ `H.GATED_METRICS`, không gõ cứng."""
    return tuple(s for s, metrics in H.GATED_METRICS.items() if "decoy_fall" in metrics)


def derive() -> tuple[float, list[tuple[str, str, float, int]]]:
    """Trả `(ngưỡng, [(provider, tầng, decoy_fall, n)])`. Chỉ đọc `TUNE_PART`."""
    rows: list[tuple[str, str, float, int]] = []
    for name, provider in offline_providers().items():
        report = H.build_report(provider, TUNE_PART)
        for stratum in gated_strata():
            value = H.stratum_metric(report, stratum, "decoy_fall")
            if value is None:
                continue
            n = sum(1 for r in report.values() if r.stratum == stratum and r.decoy_fall is not None)
            rows.append((name, stratum, value, n))

    worst_p, worst_n = max(((v, n) for _, _, v, n in rows), default=(0.0, 1))
    se = math.sqrt(worst_p * (1 - worst_p) / worst_n) if worst_n else 0.0
    return worst_p + Z * se, rows


if __name__ == "__main__":
    threshold, rows = derive()
    print(f"decoy_fall trên `{TUNE_PART}` ({len(H.cases_for(TUNE_PART))} case)\n")
    print(f"{'provider':<28} {'tầng':<5} {'decoy_fall':>11} {'n':>4}")
    for name, stratum, value, n in sorted(rows, key=lambda r: -r[2]):
        print(f"{name:<28} {stratum:<5} {value:>11.4f} {n:>4}")

    worst_p, worst_n = max(((v, n) for _, _, v, n in rows))
    se = math.sqrt(worst_p * (1 - worst_p) / worst_n)
    print(f"\nmax quan sát = {worst_p:.4f} (n={worst_n})")
    print(f"SE = sqrt({worst_p:.4f}·{1 - worst_p:.4f}/{worst_n}) = {se:.4f}")
    print(f"ngưỡng = {worst_p:.4f} + {Z}·{se:.4f} = {threshold:.4f}")
    print(f"\nđang commit: ABSOLUTE_MAX['decoy_fall'] = {H.ABSOLUTE_MAX['decoy_fall']}")
