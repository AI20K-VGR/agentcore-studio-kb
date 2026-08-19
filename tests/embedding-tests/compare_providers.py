"""So các provider embedding trên CÙNG harness — script tái lập được, commit vào repo (`kb#38`).

    uv run --python 3.14 python packages/kb/tests/embedding-tests/compare_providers.py
    uv run --python 3.14 python packages/kb/tests/embedding-tests/compare_providers.py --part validation

Chạy **offline** từ `main`: vector của provider API đọc từ `cache/` đã commit, không cần API key,
không gọi mạng. Đây chính là gạch DoD của `kb#38` mà bản báo cáo trước không có — số cũ sinh bằng
một script không nằm trong PR, nên không ai review được và không ai chạy lại được.

## Vì sao số ở đây KHỚP số gate CI enforce

`kb#38` đòi "gọi qua đúng `conftest.py::embedding_provider` / cùng đường mà `test_embedding_gate.py`
dùng — không dùng bản 'tương đương' viết tay". Script này gọi thẳng `H.build_report` và
`H.stratum_metric`, đúng hai hàm mà fixture `report` (`conftest.py`) và `test_embedding_gate.py`
dùng. Không có bản sao công thức nào ở đây.

`test_compare_providers.py::test_so_khop_fixture_report` khoá điều đó lại: nó chấm baseline qua
fixture `report` của conftest rồi so từng case với kết quả script này — lệch là CI đỏ.

## Vì sao mặc định chấm trên `--part test`

Tập `test` là 202 case KHÔNG dùng để tune tham số nào (xem `validation-split.json`). Báo cáo số
cuối trên tập đã tune là đúng sai sót phương pháp #2 của `kb#38`. Muốn xem số trên tập kia thì
`--part validation`, nhưng **đừng dán số đó vào report như kết quả cuối**.
"""

from __future__ import annotations

import argparse

import _harness as H
from providers import GeminiEmbedding, MissingVectorError

STRATA = ("S1", "S2", "S3", "S4", "S5")
HEADLINE = ("hit1", "hit3", "hit5", "mrr5", "decoy_fall")


def available_providers() -> dict[str, object]:
    """Provider chấm được **offline**. `bge-m3`/`e5-large` KHÔNG có ở đây: chúng cần
    `sentence-transformers`+`torch`, mà kb cố ý không kéo hai package đó vào dependency. Số của
    chúng trong `embedding_report.md` vẫn là số đo tay — giới hạn đã biết, ghi rõ trong report."""
    out: dict[str, object] = {"baseline-dim8": H.BaselineDim8()}
    gemini = GeminiEmbedding()  # allow_network=False — chỉ đọc cache đã commit
    if len(gemini.cache):
        out[gemini.name] = gemini
    else:
        # NÓI RA khi bỏ một provider. Im lặng ở đây là fail-open: clone thiếu `cache/*.bin` sẽ in
        # ra một bảng chỉ còn baseline mà TRÔNG VẪN BÌNH THƯỜNG, exit 0, không một dòng cảnh báo.
        # Nhánh `except MissingVectorError` ở `main()` không với tới ca này vì provider đã bị loại
        # từ trước khi kịp chấm.
        print(f"CẢNH BÁO: bỏ {gemini.name} — cache rỗng/không mở được. Bảng dưới THIẾU provider này.")
    return out


def macro(report: dict[str, H.CaseResult], metric: str) -> float | None:
    """Trung bình có trọng số theo `n` mỗi tầng, trên các tầng metric này áp dụng được.

    Weighted chứ không phải trung bình-của-trung-bình: các tầng KHÔNG bằng nhau về số case
    (S1=65 … S4=55), nên trung bình đơn sẽ ngầm khuếch đại tầng nhỏ."""
    total = num = 0.0
    for stratum in STRATA:
        value = H.stratum_metric(report, stratum, metric)
        if value is None:
            continue
        n = sum(1 for r in report.values() if r.stratum == stratum)
        num += value * n
        total += n
    return num / total if total else None


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"


def render(reports: dict[str, dict[str, H.CaseResult]], part: str) -> str:
    names = list(reports)
    n_cases = len(next(iter(reports.values()))) if reports else 0
    lines = [f"## So provider — `--part {part}` ({n_cases} case)", ""]

    lines += ["### Macro (weighted theo n mỗi tầng)", "", "| metric | " + " | ".join(names) + " |"]
    lines.append("|---|" + "---:|" * len(names))
    for metric in HEADLINE:
        lines.append(f"| {metric} | " + " | ".join(_fmt(macro(reports[n], metric)) for n in names) + " |")

    for metric in HEADLINE:
        lines += ["", f"### {metric} theo tầng", "", "| tầng | " + " | ".join(names) + " |"]
        lines.append("|---|" + "---:|" * len(names))
        for stratum in STRATA:
            row = [_fmt(H.stratum_metric(reports[n], stratum, metric)) for n in names]
            if all(cell == "—" for cell in row):
                continue
            lines.append(f"| {stratum} | " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", default="test", choices=("test", "validation", "all"))
    args = parser.parse_args()

    reports: dict[str, dict[str, H.CaseResult]] = {}
    for name, provider in available_providers().items():
        try:
            reports[name] = H.build_report(provider, args.part)
        except MissingVectorError as exc:  # cache thiếu → nói rõ, KHÔNG lặng lẽ bỏ provider
            print(f"BỎ QUA {name}: {exc}")
    print(render(reports, args.part))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
