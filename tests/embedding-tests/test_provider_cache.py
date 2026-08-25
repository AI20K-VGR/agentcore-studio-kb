"""Khoá `_vector_cache.py` + `providers.py`.

Cache là thứ mọi con số provider API dựa vào, nên nó hỏng theo kiểu **câm**: sai byte-order, lệch
`.bin` với `.index.json`, hay đọc trúng vector của model khác đều cho ra danh sách float đúng số
chiều — chỉ là giá trị vô nghĩa. Không exception, không test đỏ, chỉ là bảng số tệ đi mà không ai
biết vì sao. Mọi bài ở đây nhắm đúng loại hỏng đó.

KHÔNG bài nào gọi mạng: `GeminiEmbedding` mặc định `allow_network=False`.
"""

from __future__ import annotations

import json
from pathlib import Path

import _harness as H
import pytest
from _vector_cache import VectorCache, cache_key
from providers import GEMINI_DIM, GEMINI_MODEL, GeminiEmbedding, MissingVectorError, l2_normalize
from record_provider_cache import golden_v2_texts, harness_texts, texts_to_record


@pytest.fixture
def tmp_cache(tmp_path: Path) -> VectorCache:
    return VectorCache("thu", model="m", dim=4, cache_dir=tmp_path)


def test_ghi_roi_doc_lai_dung_gia_tri(tmp_path: Path) -> None:
    """Round-trip qua ĐĨA (không phải qua RAM của cùng một object) — đây mới là đường CI thật đi:
    ghi một lần bằng script, đọc lại ở lần chạy khác."""
    cache = VectorCache("thu", model="m", dim=4, cache_dir=tmp_path)
    cache.put("xin chào", [0.5, -0.25, 0.125, 0.0])
    cache.flush()

    lai = VectorCache("thu", model="m", dim=4, cache_dir=tmp_path)
    assert lai.get("xin chào") == [0.5, -0.25, 0.125, 0.0]  # số biểu diễn đúng trong float32
    assert len(lai) == 1


def test_khoa_gom_ca_model_va_dim() -> None:
    """Cùng một câu, khác model hoặc khác số chiều ⇒ khoá KHÁC NHAU.

    Băm mỗi `text` thì lần đổi `dim` đầu tiên sẽ đọc trúng vector cũ sai số chiều — và nó chỉ lộ ra
    khi có ai tình cờ đối chiếu lại."""
    base = cache_key("m", 2048, "q")
    assert base != cache_key("m2", 2048, "q")
    assert base != cache_key("m", 1536, "q")
    assert base == cache_key("m", 2048, "q")


def test_doc_cache_cua_model_khac_thi_bao_loi(tmp_path: Path) -> None:
    """Mở cache đã ghi bằng (model, dim) khác ⇒ nổ ngay, không trộn hai không gian vector."""
    VectorCache("thu", model="m", dim=4, cache_dir=tmp_path).put("a", [1.0, 0, 0, 0])
    VectorCache("thu", model="m", dim=4, cache_dir=tmp_path).flush()
    VectorCache("thu", model="m", dim=4, cache_dir=tmp_path)  # đúng cặp → mở được

    with pytest.raises(ValueError, match="đừng trộn hai không gian vector"):
        VectorCache("thu", model="khac", dim=4, cache_dir=tmp_path)


def test_bin_lech_index_thi_bao_loi(tmp_path: Path) -> None:
    """`.bin` và `.index.json` lệch nhau ⇒ nổ lúc mở, không đọc ra vector rác.

    Đây là trạng thái để lại nếu một lần ghi bị đứt giữa chừng (Ctrl-C, hết quota) — `flush()` ghi
    qua file tạm chính vì vậy, nhưng cache do tay người sửa vẫn có thể lệch."""
    cache = VectorCache("thu", model="m", dim=4, cache_dir=tmp_path)
    cache.put("a", [1.0, 0.0, 0.0, 0.0])
    cache.put("b", [0.0, 1.0, 0.0, 0.0])
    cache.flush()

    index_path = tmp_path / "thu.index.json"
    meta = json.loads(index_path.read_text(encoding="utf-8"))
    meta["count"] = 1  # khai 1 vector, `.bin` có 2
    meta["keys"].pop("b" if "b" in meta["keys"] else next(iter(meta["keys"])))
    index_path.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(ValueError, match="cache hỏng"):
        VectorCache("thu", model="m", dim=4, cache_dir=tmp_path)


def test_hai_khoa_tro_cung_mot_dong_thi_bao_loi(tmp_path: Path) -> None:
    """Chỉ số dòng phải là SONG ÁNH với 0..N-1.

    Hai guard kia (kích thước file, `count`) đều BẤT BIẾN dưới phép trùng chỉ số — sửa `index.json`
    cho hai khoá cùng trỏ dòng 0 thì `len(keys)`, `count`, `.bin` đều y nguyên, cache mở được, hai
    khoá đọc ra CÙNG một vector và một dòng mồ côi trong `.bin`. Trigger không xa vời: `index.json`
    là JSON >1000 dòng đã commit mà mọi lần re-record sẽ nối thêm vào; một lần giải conflict merge
    bằng tay là đủ."""
    cache = VectorCache("thu", model="m", dim=4, cache_dir=tmp_path)
    cache.put("a", [1.0, 0.0, 0.0, 0.0])
    cache.put("b", [0.0, 1.0, 0.0, 0.0])
    cache.flush()

    index_path = tmp_path / "thu.index.json"
    meta = json.loads(index_path.read_text(encoding="utf-8"))
    keys = list(meta["keys"])
    meta["keys"][keys[1]] = meta["keys"][keys[0]]  # count, .bin, len(keys) đều KHÔNG đổi
    index_path.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(ValueError, match="không phải 0..N-1"):
        VectorCache("thu", model="m", dim=4, cache_dir=tmp_path)


def test_put_khong_ghi_de(tmp_cache: VectorCache) -> None:
    """Khoá đã có thì BỎ QUA. Ghi đè âm thầm làm hai lần chạy cho hai kết quả mà `git diff` chỉ thấy
    blob nhị phân đổi — không cách nào review."""
    tmp_cache.put("a", [1.0, 0.0, 0.0, 0.0])
    tmp_cache.put("a", [0.0, 0.0, 0.0, 9.0])
    assert tmp_cache.get("a") == [1.0, 0.0, 0.0, 0.0]
    assert len(tmp_cache) == 1


def test_put_sai_so_chieu_thi_bao_loi(tmp_cache: VectorCache) -> None:
    with pytest.raises(ValueError, match="cache khai 4"):
        tmp_cache.put("a", [1.0, 2.0])


def test_thieu_cache_thi_no_chu_khong_roi_ve_provider_khac(tmp_path: Path) -> None:
    """Text vắng mặt + `allow_network=False` ⇒ `MissingVectorError`.

    Bài quan trọng nhất file này. Rơi êm về `derive_vector` sẽ cho một lần chạy báo cáo số của
    `dim-8` dưới nhãn `gemini-embedding-001` mà CI vẫn xanh — đúng kiểu 'xanh giả' mà INV-4 và
    `kb#38` nhắm tới."""
    provider = GeminiEmbedding(
        cache=VectorCache("trong", model="google/gemini-embedding-001", dim=8, cache_dir=tmp_path)
    )
    with pytest.raises(MissingVectorError, match="chưa có trong cache"):
        provider.embed(["câu chưa từng embed"])


def test_cache_rong_tiem_vao_khong_bi_thay_bang_cache_mac_dinh(tmp_path: Path) -> None:
    """`kb#58`: cache vừa dựng (chưa có vector) là falsy — `cache or VectorCache(...)` từng vứt nó
    im lặng và quay về `CACHE_DIR` mặc định, tức fixture ĐÃ COMMIT. Hậu quả thật: một cache tiêm để
    TRÁNH đụng fixture lại ghi thẳng vào fixture, không gì báo (evidence: `kb#58`, +61 vector lẫn
    vào baseline của `evalhub#31`)."""
    name = f"{GEMINI_MODEL.rsplit('/', 1)[-1]}-d{GEMINI_DIM}"
    rong = VectorCache(name, model=GEMINI_MODEL, dim=GEMINI_DIM, cache_dir=tmp_path)
    assert not rong, "fixture phải THẬT SỰ rỗng, nếu không bài này rỗng nghĩa"
    assert GeminiEmbedding(cache=rong)._cache is rong


def test_l2_normalize_ra_vector_don_vi() -> None:
    out = l2_normalize([3.0, 4.0])
    assert out == [0.6, 0.8]
    assert l2_normalize([0.0, 0.0]) == [0.0, 0.0]  # không chia cho 0


def test_cache_da_commit_doc_duoc_va_dung_so_chieu() -> None:
    """Cache thật trong repo mở được, đúng `GEMINI_DIM`, và **vector đã chuẩn hoá**.

    Chuẩn hoá là bất biến của đường ghi (`GeminiEmbedding.embed` gọi `l2_normalize` trước khi `put`).
    Bài này chốt nó ở phía dữ liệu: một lần re-record quên chuẩn hoá sẽ đỏ ở đây, chứ không lặng lẽ
    chờ tới ngày ai đó đổi `<=>` sang `<#>`."""
    provider = GeminiEmbedding()
    assert provider.cache.dim == GEMINI_DIM

    # Lấy query THẬT của case đầu tiên, không phải một câu bịa: cache được ghi từ đúng tập này nên
    # câu này chắc chắn có mặt. Câu bịa sẽ khiến bài rơi vào `skip`, mà skip không phải pass.
    queries = [c.query for c in H.load_cases()[:20]]
    vectors = provider.embed(queries)
    assert len(vectors) == len(queries)
    for query, vector in zip(queries, vectors, strict=True):
        assert len(vector) == GEMINI_DIM, query
        assert sum(x * x for x in vector) == pytest.approx(1.0, abs=1e-4), query


def test_embed_giu_dung_thu_tu_va_khong_gap_doi_text_trung() -> None:
    """Trả về ĐÚNG thứ tự `texts` truyền vào, kể cả khi có text lặp.

    `embed` dedupe trước khi hỏi cache/API (800 chunk corpus 2.0 có câu lặp). Dedupe mà quên dựng
    lại theo thứ tự gốc là lệch vector cho MỌI case sau đó — hỏng câm, số vẫn ra một bảng đẹp."""
    provider = GeminiEmbedding()
    a, b = (c.query for c in H.load_cases()[:2])
    out = provider.embed([a, b, a])
    assert len(out) == 3
    assert out[0] == out[2] != out[1]
    assert out[0] == provider.embed([a])[0]


def test_cache_da_commit_CO_MAT_va_phu_du_moi_text_DA_KHAI() -> None:
    """Cache đã commit PHẢI có mặt và PHẢI phủ đủ. `skip` ở đây chính là xanh-giả.

    Đo được trước khi có bài này: bỏ `cache/gemini-embedding-001-d2048.bin` ra khỏi cây (clone
    thiếu, fetch hỏng, hay một dòng `.gitignore`) ⇒ `pytest` cho **741 passed, 2 skipped, exit 0**
    và `compare_providers.py` in ra một bảng chỉ còn `baseline-dim8`, exit 0, không một dòng cảnh
    báo. Đúng hình dạng fail-open mà `MissingVectorError` sinh ra để chặn, chỉ dịch lên một tầng:
    không phải "số của dim-8 dưới nhãn gemini", mà "gemini vắng mặt dưới một bảng trông bình thường".

    Kiểm PHỦ ĐỦ chứ không phải chỉ đếm một con số cứng: khẳng định cache chứa đúng mọi text mà
    `texts_to_record()` khai. Con số cứng sẽ mục ngay lần thêm case tiếp theo, còn phép phủ này
    tự đúng theo bộ case hiện tại — và bắt được cả ca cache CÓ mặt nhưng ghi thiếu giữa chừng.

    `texts_to_record()` nay là HỢP của nhiều bề mặt (`harness_texts` + `golden_v2_texts`), rộng hơn
    thứ `build_report` hỏi tới — nên tên bài nói "text ĐÃ KHAI", không nói "text harness cần".
    """
    cache = GeminiEmbedding().cache
    assert len(cache), "cache đã commit KHÔNG mở được — kiểm `cache/*.bin` có trong cây làm việc không"

    can = list(dict.fromkeys(texts_to_record()))
    thieu = [t for t in can if cache.get(t) is None]
    assert not thieu, f"cache thiếu {len(thieu)}/{len(can)} text harness cần, vd: {thieu[0][:60]!r}"


def test_cache_phu_query_golden_2_0_va_vector_da_chuan_hoa() -> None:
    """Query của golden-set 2.0 PHẢI embed được offline — bài này là hàng rào cho khoảng trống AIE-2
    báo ở kb#40.

    Trạng thái trước khi có bài này (đo, không suy đoán): 22 query phân biệt của
    `GOLDEN_CASES_V2`, **0 có trong cache**, trùng 0 với query của bộ 300 case. Nên mọi đường chấm
    golden 2.0 qua `gemini-embedding-001` — provider ĐÃ CHỐT — đều nổ `MissingVectorError`. Đó là
    fail-closed chạy đúng thiết kế (`record_provider_cache` bản đầu tự khai "không hơn"), nhưng
    giới hạn ấy không được viết ở đâu cả nên chỉ lộ ra khi có người đâm vào.

    Kiểm cả **chuẩn hoá L2** trên đúng nhóm vector mới, không chỉ sự có mặt:
    `test_cache_da_commit_doc_duoc_va_dung_so_chieu` chỉ lấy mẫu 20 query đầu của bộ benchmark, nên
    một lần re-record đi vòng qua `GeminiEmbedding.embed` (bỏ `l2_normalize`) sẽ để lại 22 vector
    chưa chuẩn hoá mà không bài nào thấy.
    """
    provider = GeminiEmbedding()  # allow_network=False — chỉ đọc cache đã commit
    queries = list(dict.fromkeys(golden_v2_texts()))
    assert queries, "golden 2.0 rỗng — sai đường lấy case, không phải cache thiếu"

    thieu = [q for q in queries if provider.cache.get(q) is None]
    assert not thieu, (
        f"cache thiếu {len(thieu)}/{len(queries)} query golden 2.0, vd: {thieu[0][:60]!r} — "
        "chạy `record_provider_cache.py` rồi commit lại `cache/`"
    )

    for query, vector in zip(queries, provider.embed(queries), strict=True):
        assert len(vector) == GEMINI_DIM, query
        assert sum(x * x for x in vector) == pytest.approx(1.0, abs=1e-4), query


def test_texts_to_record_la_hop_cua_dung_hai_be_mat() -> None:
    """`texts_to_record` = `harness_texts` + `golden_v2_texts`, không thiếu bề mặt nào.

    Tách hàm ra rồi quên nối vào `texts_to_record` thì bài phủ-đủ ở trên vẫn xanh (nó chấm theo
    chính `texts_to_record`) trong khi cache lại thiếu đúng phần vừa tách — hỏng câm. Bài này khoá
    phép hợp đó.
    """
    hop = set(texts_to_record())
    assert set(harness_texts()) <= hop
    assert set(golden_v2_texts()) <= hop
    assert hop == set(harness_texts()) | set(golden_v2_texts())
