# Bảy provider embedding: dim-8 · hash-1024 · BGE-M3 · e5-large · Gemini-001 · Gemini-2 · Qwen3-8B

Viết lại HOÀN TOÀN, thay thế báo cáo 5-provider cũ (dim-8/hash512/bge-m3/e5-large/gemini-embedding-001
ở `top_k=10`, đo trước khi `Chunk.embedding_input` có tiêu đề tài liệu + lọc boilerplate). Hai lý do
số cũ không dùng lại được (đã ghi ở bản trước, không lặp lại ở đây): sai `top_k` (10 thay vì production
thật) và sai chuỗi đem embed (`.text` trần thay vì `embedding_input`). Bản này đo lại từ đầu trên
harness hiện tại, với **6 metric mới thay cho `recall`/`clean` cũ** (xem §Metric), `hash-1024` thay
cho `hash-512`, và `gemini-embedding-001` đo lại ở `output_dimensionality=2048` (bản cũ dùng 1024).

**Năm provider CHÍNH** (dim-8 · hash-1024 · bge-m3 · e5-large · gemini-001) đo trước, có đủ bảng
per-tầng + gate. **Hai provider BỔ SUNG** (`gemini-embedding-2`, `qwen3-embedding-8b`) đo sau qua
OpenRouter — kết quả ở §Provider bổ sung, cùng harness/corpus/case nên so trực tiếp được.

## §Tái lập — cách chạy lại mọi con số ở mục này (kb#38)

Phản hồi đóng PR#33: *"script chấm không nằm trong repo → không ai review được, không ai chạy lại
được."* Mục này là phần **đã khép** phản hồi đó. Mọi số trong §Tái lập chạy lại được từ `main`,
**offline, không API key, không tốn tiền**:

```
uv run --python 3.14 python packages/kb/tests/embedding-tests/compare_providers.py
uv run --python 3.14 python packages/kb/tests/embedding-tests/compare_providers.py --part all
```

Vector của `gemini-embedding-001` đọc từ `cache/gemini-embedding-001-d2048.bin` (1088 vector
float32 = 8.9 MB, đã commit). Ghi lại cache — bước DUY NHẤT ra mạng — cần `OPEN_ROUTER_API_KEY`:

```
uv run --python 3.14 python packages/kb/tests/embedding-tests/record_provider_cache.py
```

`compare_providers.py` gọi thẳng `H.build_report`/`H.stratum_metric` — **đúng hai hàm** mà fixture
`report` (`conftest.py`) và `test_embedding_gate.py` dùng, không có bản sao công thức nào.
`test_compare_providers.py::test_so_khop_fixture_report` so từng case giữa hai đường; lệch một case
là CI đỏ.

### Tách validation / test

`validation-split.json` — **98 case validation / 202 case test**, phân tầng 33%, seed `20260819`,
sinh bằng `make_validation_split.py` và ĐÓNG BĂNG trong repo. Mọi tham số/ngưỡng phải tune trên
`validation`; bảng dưới đây báo cáo trên `test`. Đây là gạch 3 của `kb#38` (sai sót phương pháp #2:
ngưỡng `decoy_fall` 0.35 ở §Gate được chọn bằng cách quét trên chính tập báo cáo — **số 0.35 đó vẫn
chưa được chọn lại trên validation**, xem §Còn để mở).

### Bảng tái lập được — `--part test` (202 case)

| metric | `baseline-dim8` | `gemini-embedding-001` @2048 |
|---|---:|---:|
| Hit@1 | 0.0247 | **0.5370** |
| Hit@3 | 0.1049 | **0.6790** |
| Hit@5 | 0.1420 | **0.8025** |
| MRR@5 | 0.0618 | **0.6288** |
| Decoy Fall (S3+S4) | 0.0390 | **0.0649** |

### Phát hiện: đo lại qua OpenRouter KHÔNG ra đúng số đo tay

Chạy cùng pipeline trên cả 300 case (`--part all`) để so trực tiếp với bảng đo tay ở §Macro:

| metric | đo tay (Google trực tiếp) | tái lập (OpenRouter) | lệch |
|---|---:|---:|---:|
| Hit@1 | 0.5726 | 0.5519 | −0.021 |
| Hit@3 | 0.7137 | 0.7012 | −0.013 |
| Hit@5 | 0.7801 | 0.8050 | **+0.025** |
| MRR@5 | 0.6492 | 0.6391 | −0.010 |
| Decoy Fall | 0.0783 | 0.0870 | +0.009 |

**`baseline-dim8` thì khớp TUYỆT ĐỐI cả 5 metric tới 4 chữ số** (0.0207 · 0.0954 · 0.1245 · 0.0557 ·
0.0435). Đó là phép khử biến quan trọng: đường harness giống hệt nhau, nên chênh lệch nằm hoàn toàn
ở **chính vector Gemini**, không phải ở cách chấm.

Nguyên nhân khả dĩ, chưa tách bạch được: hai đường phục vụ khác nhau (free-tier Google trực tiếp vs
OpenRouter→Google), hoặc bản thân API không tất định. KHÔNG phải do chuẩn hoá (cosine bất biến với
tỉ lệ) và khó do float32 (lệch tới 2 điểm là quá lớn cho sai số làm tròn).

Mọi chênh lệch trên đều **dưới ngưỡng ~6 điểm (2 SE)** mà chính báo cáo này đặt ra ở mục dưới, nên
không cái nào đọc được là "khác biệt thật". Nhưng đó chính là điều đáng ghi: **không có pipeline tái
lập được thì không thể biết một bảng số dao động bao nhiêu giữa hai lần chạy** — và bản báo cáo
trước đã dùng chênh lệch cỡ này để xếp hạng provider.

### Giới hạn còn lại của mục này

`bge-m3` và `multilingual-e5-large` **KHÔNG** có trong bảng tái lập: chúng cần
`sentence-transformers`+`torch`, mà kb cố ý không kéo hai package đó vào dependency. Số của chúng ở
các mục dưới vẫn là **số đo tay**, chưa khép được phản hồi của PR#33.

## Sai số cần biết TRƯỚC khi đọc mọi bảng

n = **241 case** cho S1–S4 (S5 không có Hit@k). Sai số chuẩn của một tỉ lệ quanh 0.70 là
**SE ≈ 0.030**. Nghĩa là: **chênh lệch dưới ~3 điểm phần trăm giữa hai provider KHÔNG phải phát hiện**
— nó nằm trong nhiễu lấy mẫu. Chỉ chênh lệch từ ~6 điểm (2 SE) trở lên mới nên đọc là khác biệt thật.
Nhiều so sánh trong báo cáo này (đặc biệt reranker-vs-reranker, và ba provider mạnh nhất so với nhau)
nằm dưới ngưỡng đó — đã chú thích tại chỗ.

## Corpus & bộ case (dùng chung cho cả 7 provider)

- Corpus 2.0: **800 chunk** trên **80 tài liệu**, 2 tenant (`ankor`/`borea`, 400 chunk mỗi bên; 4 role
  `engineering`/`finance`/`hr`/`public`, 200 chunk mỗi role).
- Bộ case: **300 case**, 5 tầng S1–S5 (~60 case/tầng) — `tests/embedding-tests/cases/*.json`.
- Chuỗi đem embed: `Chunk.embedding_input` (= `embed_text`, có tiêu đề tài liệu + đã lọc boilerplate;
  fallback `.text` nếu rỗng) — **cùng chuỗi đường ghi thật dùng** (`KbIngest.write`), không phải
  `.text` trần. Xem `doc_factory_v2._cut_document`/`_strip_boilerplate`.
- Retrieval mô phỏng `PgKbSearch`: cosine, lọc `{tenant_id, section_roles}` TRƯỚC khi xếp hạng, luôn
  lấy **top-5** (`MAX_K`) rồi cắt còn top-1/3 cho hai metric kia — không retrieve lại ở k khác nhau.

## Metric — 6 con số, MỖI CON SỐ MỘT NGHĨA CỐ ĐỊNH (không đổi nghĩa theo tầng như `recall`/`clean` cũ)

| Metric | Công thức | Tầng áp dụng | Chiều tốt |
|---|---|---|:---:|
| **Hit@1** | chunk cần thiết có ở HẠNG #1 không (1.0/0.0) | S1–S4 | cao |
| **Hit@3** | … trong top-3 | S1–S4 | cao |
| **Hit@5** | … trong top-5 | S1–S4 | cao |
| **MRR@5** | 1/hạng của chunk đúng đầu tiên trong top-5; 0 nếu trượt hẳn | S1–S4 | cao |
| **Decoy Fall Rate** | hạng #1 có TRÚNG ĐÚNG chunk DE gán nhãn bẫy (`decoy_hint`) không | chỉ S3, S4 | **thấp** |
| **Max Cosine Mean** | trung bình cosine của hạng #1 mỗi case | mọi tầng, kể cả S5 | **thấp** ở S5*, tham khảo ở S1–S4 |

\* Ở S5 (negative — không có `expected_citation`) không có gì để "trúng", nên Hit@k/MRR@5 = **N/A**
(không phải 0 — 0 sẽ đọc nhầm thành "trượt", trong khi thực ra câu hỏi không áp dụng). Metric duy nhất
còn ý nghĩa là **Max Cosine Mean thấp = mô hình không tự tin bừa khi không có đáp án** — đây chính là
gate "clean" của bản báo cáo cũ, chỉ bỏ phép nghịch đảo `1 − top_sim` cho dễ đọc trực tiếp.

**Hit@3 khớp `top_k` mặc định production** (`packages/kb/../workbench/builder.py:219,292` — node
`kb-retrieve` hardcode `"top_k": 3`); **Hit@5 khớp fallback của `KbRetrieveExecutor`**
(`src/studio_kb/search.py`). Cả hai đều là call-site thật, không phải số chọn cho "có ngữ cảnh".

**Decoy Fall Rate hẹp hơn tên gọi** — chỉ bắt "hạng #1 trúng ĐÚNG chunk DE đã gán nhãn là bẫy gần
giống", KHÔNG phải "hạng #1 sai bất kỳ chunk nào". Chỉ S3 (near-miss cùng role) và S4 (cross-role) khai
`decoy_hint` (S1/S2/S5 luôn `None`/N/A). `test_embedding_cases.py` chỉ kiểm decoy là chunk thật cùng
tenant, KHÔNG kiểm nó là đối thủ trùng-token mạnh nhất trong corpus — DFR thấp không tự động nghĩa là
"ít bị nhiễu nói chung", có thể chỉ là nhãn decoy chưa phải bẫy mạnh nhất (xem phát hiện ở §Kết luận).

**Max Cosine Mean chỉ GATE (chặn CI) ở S5** — dù được đo/ghi đủ cho cả S1–S5. Lý do KHÔNG gate ở
S1–S4: `dim-8` (8 chiều) có cosine bị **thổi phồng giả tạo** do quá ít chiều để hai văn bản bất kỳ
(liên quan hay không) tách xa nhau về góc — đo trực tiếp: mọi cặp (query, chunk) trong một scope 100
chunk đều rơi vào dải cosine 0.37–0.83 ở dim-8, kể cả 99 chunk hoàn toàn sai chủ đề; ở dim-1024 dải đó
kéo dài 0.02–0.29 (chunk sai bị đẩy về gần 0 thật). Gate "cao hơn dim-8" ở S1–S4 sẽ luôn ĐỎ cho các
provider ngữ nghĩa dù chúng đúng hơn dim-8 hàng chục điểm phần trăm ở Hit@k — vì đang so một hiện
tượng hình học (số chiều), không so độ tự tin thật. Quyết định giữ nguyên: chỉ gate ở S5.

## Bảy provider là gì

| Provider | Công thức | Chiều | Nơi chạy | Ngữ nghĩa? | Tải/setup | Embed 800+300 |
|---|---|---:|---|:---:|---:|---:|
| `dim-8` | `derive_vector` — băm token vào 8 ô, đếm, L2-normalize (`studio_kb/embeddings.py`) | 8 | local, CPU | Không | — | 0.07s |
| `hash1024` | CÙNG hàm `derive_vector`, chỉ đổi `dim=8`→`dim=1024` | 1024 | local, CPU | Không | — | 1.77s |
| `bge-m3` | `BAAI/bge-m3` qua `sentence-transformers`, dense học sẵn, đa ngôn ngữ | 1024 | local, MPS | Có | 12.2s | 15.3s |
| `multilingual-e5-large` | `intfloat/multilingual-e5-large` qua `sentence-transformers` | 1024 | local, MPS | Có | 9.5s | 15.6s |
| `gemini-embedding-001` | Google Gemini Embedding API, `output_dimensionality=2048` (Matryoshka, cắt từ 3072 gốc) | 2048 | API (Google, free-tier trực tiếp) | Có | — | 209s\* |
| `gemini-embedding-2` | Cùng dòng, bản mới hơn (context 8192 vs 2048) — gọi qua OpenRouter, `$0.20/M token` | 2048 | API (OpenRouter→Google) | Có | — | **44.9s** |
| `qwen3-embedding-8b` | `Qwen/Qwen3-Embedding-8B` (8B tham số, context 32K) — qua OpenRouter, `$0.01/M token` | 2048 | API (OpenRouter→DeepInfra) | Có | — | **91.1s** |

\* Thời gian `gemini-embedding-001` KHÔNG phải latency inference thật — phần lớn là chờ giới hạn tốc
độ CỦA ĐƯỜNG GỌI FREE-TIER TRỰC TIẾP đã dùng để đo (xem §Vận hành, có đính chính). Không nên đọc con
số này như "API chậm hơn model local ~14 lần" — qua OpenRouter (trả phí, không giới hạn ngày), cùng
model chạy xong 1100 lượt trong <1 phút, ngang tốc độ `gemini-embedding-2`/`qwen3-embedding-8b`.

**Xử lý bất đối xứng query↔document** — mỗi provider một cách, đều theo tài liệu chính thức của nó:

| Provider | Cách phân biệt query vs document |
|---|---|
| `multilingual-e5-large` | prefix trong text: `"passage: "` cho corpus, `"query: "` cho câu hỏi |
| `gemini-embedding-001` / `-2` | tham số API `task_type=RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY` |
| `qwen3-embedding-8b` | document KHÔNG prefix; query dùng `"Instruct: {task}\nQuery: {q}"` (model card nói +1–5%) |
| `bge-m3` | không cần gì cả (đối xứng) |

Mọi provider bất đối xứng đều phân biệt hai lượt gọi **theo KÍCH THƯỚC BATCH** (800 vs 300), không
theo thứ tự gọi — thứ tự không bền nếu ai đó gọi lại `build_retriever`/`build_report` ngoài kịch bản
1-lần-mỗi-cái; provider raise nếu gặp batch không phải 800/300, không âm thầm đoán. `bge-m3`/`e5-large`
chạy trên **MPS** (GPU Apple Silicon local), `normalize_embeddings=True`.

Script chấm KHÔNG nằm trong repo `kb` (không thêm `sentence-transformers`/`torch`/`google-genai` vào
dependency của package — theo tiền lệ bản báo cáo trước): chạy tay, ngoài luồng, import thẳng
`_harness`/`studio_kb`. `gemini-embedding-001` cache kết quả theo `sha256(text)` (ghi liên tục, không
embed lại text đã có) — cần thiết vì đã dính quota giữa chừng, xem §Vận hành.

## §Vận hành — chi phí vận hành thật đo được lần này, không phải suy đoán

**Đính chính quan trọng (sau khi viết bản đầu của mục này): quota dưới đây là giới hạn của ĐƯỜNG GỌI cụ
thể (free-tier key gọi thẳng Google AI Studio), KHÔNG phải giới hạn của bản thân model
`gemini-embedding-001`.** `google/gemini-embedding-001` cũng gọi được qua OpenRouter
(`/api/v1/embeddings`, xác nhận trực tiếp từ trang model — `$0.15/M token`, KHÔNG phải free-tier, KHÔNG
có giới hạn ngày kiểu trên) — đúng cách đã dùng để đo `gemini-embedding-2`/`qwen3-embedding-8b` ở dưới,
chạy xong 1100 lượt trong <1 phút, 0 lỗi quota. Tức là **toàn bộ sự cố quota mô tả dưới đây là chi phí
của việc dùng free-tier key trực tiếp, không phải chi phí bắt buộc phải trả để dùng model này** — có
đường khác (trả phí nhẹ qua OpenRouter) né được hoàn toàn.

Vẫn giữ lại mô tả sự cố (đã xảy ra thật, đáng ghi làm bài học vận hành cho AI dùng free-tier key trực
tiếp), nhưng không dùng nó để kết luận "gemini-embedding-001 rủi ro quota hơn provider khác" nữa —
kết luận đó SAI, sửa lại ở phần Kết luận bên dưới.

`gemini-embedding-001` free-tier (đường gọi trực tiếp, KHÔNG phải qua OpenRouter) dính **HAI** loại
giới hạn khác nhau khi chấm batch này:

1. **Giới hạn theo phút** (100 request/phút) — batch 100 text trong 1 lần gọi bị tính là 100 request,
   chạm ngưỡng ngay. Giải quyết bằng cách chia batch ~90 text/lần + nghỉ 65s giữa các lần gọi.
2. **Giới hạn theo NGÀY** (1000 request/ngày, free-tier) — dính **giữa chừng thật**, đúng lúc vừa
   embed xong 800 chunk corpus và bắt đầu 300 query (chạm mốc 1000 tổng cộng). Loại này retry theo
   phút KHÔNG cứu được — phải đổi sang API key khác để chạy tiếp 300 query còn lại.

Đây KHÔNG phải lý thuyết suy diễn — là sự cố thật gặp phải khi chấm batch này bằng đường gọi trực tiếp
(báo cáo bản trước cũng từng ghi nhận hiện tượng tương tự: "2 lần đổi API key vì hết quota ngày").
`bge-m3`/`e5-large` không gặp giới hạn nào tương tự vì chạy hoàn toàn local; `gemini-embedding-001`
qua OpenRouter cũng không gặp — chỉ đường gọi free-tier trực tiếp mới dính.

## Kết quả theo tầng — từng metric

### Hit@1

| tầng | dim-8 | hash1024 | bge-m3 | e5-large | gemini-001 |
|---|---:|---:|---:|---:|---:|
| S1 | 0.0308 | 0.5692 | 0.6615 | 0.6308 | 0.7231 |
| S2 | 0.0164 | 0.0000 | 0.3115 | 0.3279 | 0.4754 |
| S3 | 0.0167 | 0.2333 | 0.3667 | 0.4667 | 0.5667 |
| S4 | 0.0182 | 0.3091 | 0.3818 | 0.3273 | 0.5091 |

### Hit@3

| tầng | dim-8 | hash1024 | bge-m3 | e5-large | gemini-001 |
|---|---:|---:|---:|---:|---:|
| S1 | 0.1231 | 0.7385 | 0.7846 | 0.8000 | 0.8000 |
| S2 | 0.0492 | 0.0492 | 0.5246 | 0.5246 | 0.6721 |
| S3 | 0.1333 | 0.4667 | 0.6000 | 0.6500 | 0.7333 |
| S4 | 0.0727 | 0.4000 | 0.5455 | 0.5818 | 0.6364 |

### Hit@5

| tầng | dim-8 | hash1024 | bge-m3 | e5-large | gemini-001 |
|---|---:|---:|---:|---:|---:|
| S1 | 0.1538 | 0.7692 | 0.8769 | 0.8923 | 0.8615 |
| S2 | 0.0656 | 0.0820 | 0.6230 | 0.6066 | 0.7541 |
| S3 | 0.1667 | 0.5000 | 0.6833 | 0.7167 | 0.7833 |
| S4 | 0.1091 | 0.4364 | 0.6182 | 0.6182 | 0.7091 |

### MRR@5

| tầng | dim-8 | hash1024 | bge-m3 | e5-large | gemini-001 |
|---|---:|---:|---:|---:|---:|
| S1 | 0.0736 | 0.6497 | 0.7344 | 0.7292 | 0.7718 |
| S2 | 0.0314 | 0.0292 | 0.4230 | 0.4317 | 0.5825 |
| S3 | 0.0686 | 0.3464 | 0.4858 | 0.5706 | 0.6478 |
| S4 | 0.0476 | 0.3558 | 0.4639 | 0.4445 | 0.5800 |

### Decoy Fall Rate (chỉ S3, S4 — càng THẤP càng tốt)

| tầng | dim-8 | hash1024 | bge-m3 | e5-large | gemini-001 |
|---|---:|---:|---:|---:|---:|
| S3 | 0.0667 | 0.2333 | 0.2333 | 0.1833 | 0.1167 |
| S4 | 0.0182 | 0.0545 | 0.0909 | 0.0727 | 0.0364 |

### Max Cosine Mean (S5: càng THẤP càng tốt · S1–S4: tham khảo)

| tầng | dim-8 | hash1024 | bge-m3 | e5-large | gemini-001 |
|---|---:|---:|---:|---:|---:|
| S1 | 0.9213 | 0.4219 | 0.7210 | 0.9038 | 0.8163 |
| S2 | 0.9218 | 0.2360 | 0.6002 | 0.8527 | 0.7383 |
| S3 | 0.9369 | 0.3428 | 0.6466 | 0.8715 | 0.7796 |
| S4 | 0.9494 | 0.3536 | 0.6436 | 0.8707 | 0.7659 |
| **S5** | **0.9333** | **0.3038** | **0.5848** | **0.8546** | **0.7199** |

### Macro trung bình S1–S4 (weighted theo `n` mỗi tầng)

| metric | dim-8 | hash1024 | bge-m3 | e5-large | gemini-001 |
|---|---:|---:|---:|---:|---:|
| Hit@1 | 0.0207 | 0.2822 | 0.4357 | 0.4440 | **0.5726** |
| Hit@3 | 0.0954 | 0.4191 | 0.6183 | 0.6432 | **0.7137** |
| Hit@5 | 0.1245 | 0.4523 | 0.7054 | 0.7137 | **0.7801** |
| MRR@5 | 0.0557 | 0.3501 | 0.5320 | 0.5494 | **0.6492** |
| Decoy Fall (S3+S4) | 0.0435 | 0.1478 | 0.1652 | 0.1304 | **0.0783** |

`gemini-embedding-001` thắng mọi metric chính, KỂ CẢ Decoy Fall Rate (thấp hơn cả `bge-m3` lẫn
`e5-large`, dù vẫn cao hơn `dim-8` vì lý do đã giải thích ở §Metric/§Kết luận).

## Gate (baseline dim-8 + margin theo `H.GATED_METRICS`/`record_baseline.py`)

**Hai chế độ gate** (`_harness.gate_verdict`):
- *Tương đối* so baseline dim-8 + margin — `hit1/hit3/hit5/mrr5` (S1 margin 0.02 · S2–S4 margin 0.10)
  và `max_cosine_mean` @S5 (margin 0.05, chiều thấp).
- *Tuyệt đối* — `decoy_fall` @S3/S4 phải `≤ 0.35`, KHÔNG so với dim-8. Xem §Vì sao `decoy_fall` phải
  gate tuyệt đối ngay dưới.

| tầng.metric | hash1024 | bge-m3 | e5-large | gemini-001 | gemini-2 | qwen3-8b |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| S1.hit1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S1.hit3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S1.hit5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S1.mrr5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S2.hit1 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S2.hit3 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S2.hit5 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S2.mrr5 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S3.hit1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S3.hit3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S3.hit5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S3.mrr5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S3.decoy_fall | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S4.hit1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S4.hit3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S4.hit5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S4.mrr5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S4.decoy_fall | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| S5.max_cosine_mean | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Tổng** | **15/19** | **19/19** | **19/19** | **19/19** | **19/19** | **19/19** |

Gate còn bắt đúng MỘT thứ, và đó là thứ đáng bắt: **`hash1024` trượt cả 4 ô S2 (paraphrase)** — nó
thuần lexical nên không hiểu diễn đạt lại; ở `hit3` thậm chí HOÀ đúng bằng dim-8 (0.0492 = 0.0492).
Năm provider ngữ nghĩa qua sạch 19/19.

### Vì sao `decoy_fall` phải gate TUYỆT ĐỐI — gate cũ BẤT KHẢ THI về mặt số học

Bản trước gate `decoy_fall` theo cùng cơ chế tương đối ("thấp hơn dim-8 − margin 0.10") và **cả 5
provider ngữ nghĩa đều trượt đúng 2 ô này**. Ban đầu tưởng là gate nghiêm; kiểm lại thì là **gate
hỏng**:

```
S3: cần decoy_fall ≤ 0.0667 − 0.10 = −0.033   ← NGƯỠNG ÂM
S4: cần decoy_fall ≤ 0.0182 − 0.10 = −0.082   ← NGƯỠNG ÂM
```

Không tỉ lệ nào âm được, nên **không provider nào từng có khả năng qua** — trượt vì số học, không vì
chất lượng.

Gốc rễ: **dim-8 thắng metric này một cách TẦM THƯỜNG.** Nó xếp hạng gần như ngẫu nhiên nên hạng #1
hiếm khi trúng đúng chunk decoy đã gán nhãn — thấp vì *không hiểu gì để bị bẫy*, không phải vì chống
bẫy giỏi. Đo cụ thể:

| | decoy_fall (macro S3+S4) | so với mức ngẫu nhiên thuần |
|---|---:|---:|
| xếp hạng ngẫu nhiên (1/\|scope\|) | 0.0076 | 1.0× |
| `dim-8` | 0.0435 | 5.7× |
| `gemini-001` / `gemini-2` | 0.078 | ~10× |
| `qwen3-8b` | 0.122 | 16× |
| `e5-large` | 0.130 | 17× |
| `hash1024` | 0.148 | 19× |
| `bge-m3` | 0.165 | 22× |

Model càng hiểu nghĩa càng dễ bị near-miss decoy kéo lên hạng #1 (decoy được DE dựng cố ý là "cùng
role, chủ đề kề"), nên metric này **không thể dùng để CHỌN model** — nó xếp một model ngẫu nhiên lên
đầu bảng. Nó chỉ dùng được như **thanh chắn an toàn một chiều**: bắt provider bị bẫy một cách bệnh
hoạn.

**Ngưỡng 0.35 lấy từ dữ liệu, không phải cảm tính**: giá trị cao nhất từng quan sát ở một provider
chạy được là **0.2333** (S3, `hash1024` và `bge-m3`); với n=60 ở S3 thì SE ≈ 0.055, nên
0.2333 + 2·SE ≈ 0.343. Chọn 0.35 để model tệ-ngang-`bge-m3` vẫn qua chắc chắn (gate không nhấp nháy
vì nhiễu lấy mẫu) nhưng vẫn bắt được thứ thật sự bệnh — ví dụ một nửa số truy vấn rơi vào bẫy.

Đã cài đặt: `_harness.ABSOLUTE_MAX` + `_harness.gate_verdict`, ngưỡng ghi vào `baseline-dim8.json`
(nằm trong git diff, đổi ngưỡng mà quên re-record thì CI đỏ). Margin `decoy_fall` đã bị **xoá khỏi**
`record_baseline._DEFAULT_MARGIN` để không còn cấu hình chết gây hiểu nhầm. Logic gate được chốt bằng
5 test tính tay ở `test_score_case.py` (nhánh 'ứng viên' vốn không bao giờ chạy ở CI thường vì CI chỉ
chấm chính dim-8 ở chế độ freshness), và đã gieo 3 mutation — đảo dấu ngưỡng, siết ngưỡng xuống dưới
mức đã quan sát, bỏ hẳn nhánh tuyệt đối — cả ba đều làm test đỏ.

## Provider BỔ SUNG — `gemini-embedding-2` và `qwen3-embedding-8b` (đo sau, qua OpenRouter)

Cùng harness · cùng 800 chunk · cùng 300 case · cùng `embedding_input` · cùng `dim=2048` như
`gemini-001`, nên so trực tiếp được với mọi bảng ở trên.

### Per-tầng

| metric | tầng | gemini-001 | gemini-2 | qwen3-8b |
|---|---|---:|---:|---:|
| Hit@1 | S1 | 0.7231 | 0.6769 | 0.6923 |
| Hit@1 | S2 | 0.4754 | **0.5246** | 0.4426 |
| Hit@1 | S3 | 0.5667 | 0.5333 | 0.4667 |
| Hit@1 | S4 | 0.5091 | 0.4364 | 0.4545 |
| Hit@3 | S1 | 0.8000 | **0.8462** | 0.8308 |
| Hit@3 | S2 | 0.6721 | 0.6721 | 0.6721 |
| Hit@3 | S3 | 0.7333 | 0.6667 | 0.6500 |
| Hit@3 | S4 | 0.6364 | 0.6000 | 0.6545 |
| Hit@5 | S1 | 0.8615 | 0.9077 | **0.9231** |
| Hit@5 | S2 | 0.7541 | **0.8033** | 0.7377 |
| Hit@5 | S3 | 0.7833 | 0.7500 | 0.7333 |
| Hit@5 | S4 | 0.7091 | 0.6727 | 0.6909 |
| MRR@5 | S1 | 0.7718 | 0.7659 | 0.7736 |
| MRR@5 | S2 | 0.5825 | **0.6131** | 0.5694 |
| MRR@5 | S3 | 0.6478 | 0.6092 | 0.5672 |
| MRR@5 | S4 | 0.5800 | 0.5273 | 0.5636 |
| Decoy Fall | S3 | 0.1167 | **0.1000** | 0.1500 |
| Decoy Fall | S4 | 0.0364 | 0.0545 | 0.0909 |
| Max Cosine | **S5** | 0.7199 | 0.6836 | **0.5592** |

### Macro S1–S4 + gate

| metric | gemini-001 | gemini-2 | qwen3-8b | chênh lệch lớn nhất |
|---|---:|---:|---:|---|
| Hit@1 | **0.5726** | 0.5477 | 0.5187 | 5.4đ (≈1.8 SE) |
| Hit@3 | **0.7137** | 0.7013 | 0.7054 | 1.2đ (**dưới nhiễu**) |
| Hit@5 | 0.7801 | **0.7884** | 0.7759 | 1.3đ (**dưới nhiễu**) |
| MRR@5 | **0.6492** | 0.6338 | 0.6226 | 2.7đ (**dưới nhiễu**) |
| Decoy Fall (S3+S4) | **0.0783** | 0.0782 | 0.1217 | 4.3đ |
| **Gate** | 17/19 | 17/19 | 17/19 | — (cả ba trượt đúng 2 ô `decoy_fall`) |

**Ba provider này THỐNG KÊ KHÔNG PHÂN BIỆT ĐƯỢC ở Hit@3/Hit@5/MRR@5** — chênh lệch 1.2–2.7 điểm, đều
dưới 1 SE. Hit@3 và Hit@5 chính là hai metric khớp production thật (`top_k=3`, fallback 5), nên **về
mặt sản phẩm, ba model này tương đương nhau**. Chỉ hai chỗ nhích ra ngoài nhiễu:

1. **Hit@1**: `gemini-001` (0.5726) hơn `qwen3-8b` (0.5187) 5.4đ ≈ 1.8 SE — nghiêng về gemini-001
   nhưng chưa đủ mạnh để khẳng định chắc.
2. **Decoy Fall Rate**: cả hai bản Gemini (0.078) tốt hơn rõ `qwen3-8b` (0.122) — dòng Gemini xử lý
   near-miss decoy tốt hơn nhất quán ở cả hai phiên bản.

### Vận hành — đây mới là chỗ khác biệt thật

| | gemini-001 (free-tier trực tiếp) | gemini-2 (OpenRouter) | qwen3-8b (OpenRouter) |
|---|---|---|---|
| Thời gian 1100 lượt | 209s (phần lớn là chờ quota) | **44.9s** | 91.1s |
| Sự cố | dính quota ngày, **phải đổi API key giữa chừng** | không | không |
| Giá | $0.15/M qua OpenRouter (free-tier trực tiếp: 1000 req/ngày) | $0.20/M token | **$0.01/M token** |
| Chi phí đợt đo này | $0 (free-tier, nhưng tốn 1 key dự phòng) | ~$0.014 | ~$0.0007 |

Khác biệt thật giữa ba model nằm ở **vận hành, không phải độ chính xác**: chất lượng tương đương (xem
bảng macro), còn giá chênh nhau tới 20 lần.

### Vì sao hai provider này DỪNG ở mức thử nghiệm, không thay `gemini-embedding-001`

Cả hai đều được thử vì một **giả thuyết cụ thể**, và cả hai giả thuyết đều bị chính dữ liệu bác bỏ.
Ghi lại đây để lần sau không ai thử lại cùng một hướng rồi ngạc nhiên như cũ.

**`qwen3-embedding-8b` — giả thuyết: "đứng đầu MTEB Multilingual thì phải mạnh trên tiếng Việt".**
Nó đang hạng 1 MTEB Multilingual (**70.58**), trên cả `gemini-embedding-exp` (68.37) và
`multilingual-e5-large` (63.22), nên kỳ vọng là nó sẽ dẫn đầu ở đây. **Thực tế ngược lại**: nó
KHÔNG vượt được `gemini-embedding-001` ở bất kỳ metric chính nào, và thua rõ nhất đúng ở hai chỗ khó
nhất của bài toán này:

| | qwen3-8b | gemini-001 | chênh |
|---|---:|---:|---:|
| Hit@1 (macro) | 0.5187 | 0.5726 | **−5.4đ** |
| Decoy Fall (S3+S4) | 0.1217 | 0.0783 | **+4.3đ (tệ hơn)** |

Nghĩa là nó vừa kém hơn ở "chọn đúng ngay hạng #1", vừa dễ bị near-miss decoy đánh lừa hơn — đúng
hai thứ mà corpus này cố tình dựng ra để thử. **Bài học: MTEB đo trung bình trên nhiều domain/ngôn
ngữ, không đo riêng tiếng Việt lĩnh vực chính sách nội bộ có bẫy near-miss cố ý.** Thứ hạng benchmark
công khai KHÔNG thay thế được đo trên dữ liệu thật của mình — đây chính là lý do tồn tại của harness
này, và lần này nó tự chứng minh giá trị bằng cách bác bỏ một model được kỳ vọng cao.

**`gemini-embedding-2` — giả thuyết: "context 8192 token (gấp 4 lần bản cũ) thì phải tốt hơn".**
(Lưu ý phân biệt: 8192 là **giới hạn context đầu vào**, không phải số chiều vector — cả hai bản đều
được đo ở CÙNG `dim=2048` để so công bằng.) **Thực tế: lợi thế đó hoàn toàn vô nghĩa với corpus này**
— đo trực tiếp độ dài chunk:

| | ký tự | ≈ token |
|---|---:|---:|
| chunk dài nhất | 566 | ~142 |
| phân vị 95 | 365 | ~91 |
| trung bình | 236 | ~59 |

**Chunk dài nhất chỉ dùng hết 6.9% giới hạn của bản CŨ (2048 token).** Nâng trần từ 2048 lên 8192 là
nới một ràng buộc chưa bao giờ bị chạm tới — không thể mang lại lợi ích nào. Và kết quả đúng như vậy:
`gemini-2` chỉ **ngang** `gemini-001` (chênh 1.2–2.7đ, đều dưới nhiễu), thậm chí **tệ hơn ở một số
tầng** — rõ nhất là S4.Hit@1 (0.4364 vs 0.5091, −7.3đ) và S3.Hit@3 (0.6667 vs 0.7333, −6.7đ), tức là
đúng hai tầng bẫy khó. Có xu hướng "tốt hơn ở S1/S2, kém hơn ở S3/S4" nhưng mọi chênh lệch per-tầng
đều dưới 2 SE nên **chưa đủ để khẳng định**; điều khẳng định được là **nó không tốt hơn**.

Cộng thêm chi phí: `gemini-2` giá **$0.20/M token**, đắt hơn `gemini-001` ($0.15/M) **33%**. Trả thêm
tiền cho một model không tốt hơn, để dùng một tính năng (context dài) mà corpus không cần → **không
có lý do nào để đổi**. Giữ `gemini-embedding-001`.

### Khi nào nên quay lại `qwen3-embedding-8b`: khi CHI PHÍ trở thành ràng buộc

Đây là lý do duy nhất đáng cân nhắc lại, và nó là lý do mạnh. Ở hai metric khớp production thật
(`top_k=3` và fallback 5), `qwen3-8b` **gần như không thua**:

| metric (macro) | qwen3-8b | gemini-001 | chênh |
|---|---:|---:|---:|
| **Hit@3** (= `top_k` production) | 0.7054 | 0.7137 | −0.8đ (**dưới nhiễu**) |
| **Hit@5** (= fallback) | 0.7759 | 0.7801 | −0.4đ (**dưới nhiễu**) |

Trong khi giá rẻ hơn **15 lần** ($0.01/M so với $0.15/M). Quy ra tiền ở quy mô thật:

| kịch bản | gemini-001 | gemini-2 | qwen3-8b |
|---|---:|---:|---:|
| Re-index corpus hiện tại (800 chunk, ~47K token) | $0.007 | $0.009 | **$0.0005** |
| Re-index corpus gấp 100 lần (~4.7M token) | $0.71 | $0.94 | **$0.047** |
| 1 triệu truy vấn/tháng (~14M token) | $2.10 | $2.80 | **$0.14** |

**Đánh đổi phải biết rõ trước khi đổi**: cái mất không nằm ở Hit@3/Hit@5 (gần như hoà) mà ở **Hit@1
(−5.4đ)** và **Decoy Fall (+4.3đ)**. Nên `qwen3-8b` phù hợp khi hệ thống đưa cả top-3/top-5 chunk cho
LLM tự chọn (lúc đó Hit@1 ít quan trọng); **không phù hợp** nếu sản phẩm hiển thị thẳng một kết quả
duy nhất cho người dùng, vì đó đúng là chỗ nó yếu nhất.

## Kết luận

**1. `gemini-embedding-001` thắng năm provider CHÍNH ở mọi metric (Hit@1/3/5, MRR@5), cách biệt rõ
nhất ở S2 (paraphrase, Hit@3 macro cao hơn `e5-large` +7 điểm) và S4 (cross-role, MRR@5 cao hơn
`bge-m3` +12 điểm).** Cả ba provider ngữ nghĩa đều vượt xa `dim-8`/`hash1024` (thuần lexical) — bằng
chứng lặp lại: "chuyển sang dense/ngữ nghĩa" quan trọng hơn "chọn dense model nào" (khoảng cách
dense↔lexical hàng chục điểm, khoảng cách nội bộ nhóm dense chỉ vài điểm). **Nhưng so với hai provider
BỔ SUNG thì lợi thế đó biến mất**: `gemini-2` và `qwen3-8b` ngang `gemini-001` ở Hit@3/Hit@5 (chênh
dưới nhiễu) — xem §Provider bổ sung.

**2. Phát hiện phản trực giác (lặp lại từ bản `hash-512`, nay có thêm `gemini-001`): CẢ BA provider
ngữ nghĩa đều có Decoy Fall Rate CAO HƠN `dim-8`** (macro 0.078–0.165 so với 0.044) — dù thắng áp đảo
ở mọi metric đúng-sai khác. Lý do: `dim-8` (8 chiều băm) gần như nhiễu ngẫu nhiên trên toàn corpus —
không đủ "hiểu" để bị cuốn theo cả đáp án ĐÚNG lẫn decoy near-miss, nên hạng #1 của nó gần như random
và hiếm khi trúng chính xác chunk decoy đã gán nhãn. Ba model ngữ nghĩa NGƯỢC LẠI: đủ hiểu để bị
near-miss decoy (cùng role, chủ đề kề, ví dụ chunk liền kề trong CÙNG tài liệu) kéo lên hạng #1 — ví
dụ cụ thể, `s3-ankor-hr-week1-tasks` ("tuần đầu vào công ty phải làm gì") có đáp án
`ankor-hr-onboarding#c3` nhưng `e5-large` trả hạng #1 là `ankor-hr-onboarding#c2` — chunk liền trước,
cùng mục onboarding. `gemini-001` có DFR thấp nhất trong ba (0.078) — model càng mạnh dường như càng
ít bị near-miss đánh lừa, nhưng vẫn cao hơn dim-8 vì lý do hình học trên, không phải vì dim-8 "chống
nhiễu tốt hơn". **Hệ quả đã được xử lý: gate `decoy_fall` chuyển từ so-tương-đối-với-dim-8 sang
NGƯỠNG TUYỆT ĐỐI `≤ 0.35`** — bản cũ cho ra ngưỡng âm nên bất khả thi với mọi provider; chi tiết +
cách chọn ngưỡng ở §Vì sao `decoy_fall` phải gate tuyệt đối. Vẫn giữ nguyên cảnh báo: **metric này
không dùng để CHỌN model được** (model càng ngẫu nhiên càng "thắng"), nó chỉ là thanh chắn một chiều.

**3. Chi phí vận hành: `bge-m3`/`e5-large` local (MPS), không phụ thuộc mạng/quota, tải model ~10–15s
một lần rồi tức thời; `gemini-embedding-001` phụ thuộc dịch vụ ngoài.** ~~ĐÃ dính quota thật khi chấm
đợt này~~ **— ĐÍNH CHÍNH (xem §Vận hành): quota đó là của đường gọi free-tier trực tiếp, KHÔNG phải
của model.** Gọi `google/gemini-embedding-001` qua OpenRouter ($0.15/M token, trả phí, không giới hạn
ngày) né hoàn toàn sự cố này — đã xác nhận đúng cách này chạy êm khi đo `gemini-embedding-2`/
`qwen3-embedding-8b` ở dưới. Nếu tiêu chí ưu tiên là "self-hosted, không dịch vụ ngoài" (đúng tinh
thần core hiện tại), `bge-m3`/`e5-large` vẫn phù hợp hơn (0 phụ thuộc mạng dù ở đường gọi nào) — nhưng
lý do KHÔNG còn là "gemini rủi ro quota", mà đơn thuần là chi phí/độ trễ mạng của một API call so với
chạy local. Nếu chấp nhận phụ thuộc dịch vụ ngoài (qua OpenRouter, trả phí, không quota), `gemini-001`
là lựa chọn mạnh nhất trong 5 provider chính đã đo (xem thêm `gemini-embedding-2`/`qwen3-embedding-8b`
— hai provider đo sau, thống kê không phân biệt được với `gemini-001`, đều gọi qua OpenRouter êm).

### Chốt lại — chọn gì, và KHÔNG chọn gì

| | chọn | vì sao |
|---|---|---|
| **Mặc định (API)** | `gemini-embedding-001` **qua OpenRouter**, KHÔNG rerank | mạnh nhất/đồng hạng nhất ở mọi metric; $0.15/M, không quota; rerank chỉ làm tệ đi (xem §rerank) |
| **Nếu bắt buộc self-hosted** | `bge-m3` hoặc `e5-large` **+ reranker** | 0 phụ thuộc mạng; rerank ở đây THẬT SỰ có lợi (+4–5đ Hit@1); hai reranker không phân biệt được nhau nên chọn `bge-reranker-v2-m3` vì miễn phí/local |
| **Nếu chi phí là ràng buộc** | `qwen3-embedding-8b` | rẻ hơn 15×, hoà ở Hit@3/Hit@5; chỉ chấp nhận được khi LLM đọc cả top-3/5 (xem đánh đổi ở §Khi nào quay lại qwen3) |
| **KHÔNG chọn** | `gemini-embedding-2` | không tốt hơn bản 001, đắt hơn 33%, lợi thế context 8192 vô nghĩa với chunk ~59 token |
| **KHÔNG chọn** | `dim-8`, `hash1024` | thuần lexical, sập hoàn toàn ở S2 (paraphrase); `dim-8` chỉ là fixture baseline, không phải ứng viên |

Và một điều quan trọng hơn mọi lựa chọn model ở trên: **khoảng cách giữa các model dense đã cạn**
(chênh dưới nhiễu), trong khi §Trần theo K cho thấy **đáp án đúng nằm trong top-50 ở 97.9% số case**
còn Hit@5 thực tế mới 78%. Dư địa 20 điểm đó nằm ở **tầng xếp hạng/lọc, không nằm ở model embedding**
— đổi model nữa sẽ không mua thêm được gì đáng kể.

## Thử nghiệm PHỤ — rerank bằng cross-encoder (`bge-reranker-v2-m3`)

**Không phải một trong 5 provider chính ở trên** — thử nghiệm ngoài luồng để trả lời "thêm rerank có
đáng không", đo trên harness thật (300 case, cùng corpus), KHÔNG đổi provider mặc định của harness.

**Cách đo**: retrieve top-**10** bằng bi-encoder (vòng 1) → cross-encoder chấm điểm lại CẢ 10 (vòng
2, đọc query+chunk CÙNG LÚC thay vì so hai vector rời) → sắp lại theo điểm mới, cắt còn top-**5** để
tính 6 metric — khớp `MAX_K` của harness nên so trực tiếp được với bảng ở trên.

### Bẫy đầu tiên: rerank trên `.text` (không tiêu đề) TỆ HƠN cả không rerank

Thử trên `e5-large`, so rerank khi cho cross-encoder đọc `.text` (bản KHÔNG có tiêu đề tài liệu) so
với `embedding_input` (CÓ tiêu đề — cùng chuỗi đã dùng để embed):

| metric (macro S1–S4) | trước rerank | sau rerank (`.text`) | sau rerank (`embedding_input`) |
|---|---:|---:|---:|
| Hit@1 | 0.4440 | 0.4105 | **0.4979** |
| Hit@3 | 0.6432 | 0.5989 | **0.6598** |
| MRR@5 | 0.5494 | 0.5019 | **0.5798** |

Rerank trên `.text` trần làm KẾT QUẢ TỆ HƠN không rerank — đúng bug tiêu đề tài liệu đã sửa ở
`doc_factory_v2` (xem đầu báo cáo) lặp lại một lần nữa, lần này ở tầng rerank: cross-encoder mất đúng
tín hiệu (tiêu đề) mà bi-encoder vòng 1 đang có, nên "ý kiến thứ hai" của nó kém thông tin hơn "ý kiến
thứ nhất". **Bài học: rerank PHẢI đọc CÙNG chuỗi đã dùng để embed, không phải `.text` hiển thị.** Toàn
bộ số dưới đây đều dùng `embedding_input` cho rerank.

### Rerank giúp `e5-large` (bi-encoder yếu hơn), nhưng HẠI `gemini-001` (bi-encoder mạnh hơn)

| metric (macro S1–S4) | e5-large trước | e5-large sau rerank | gemini-001 trước | gemini-001 sau rerank |
|---|---:|---:|---:|---:|
| Hit@1 | 0.4440 | **0.4979** (+5.4) | 0.5726 | 0.4979 (**−7.5**) |
| Hit@3 | 0.6432 | **0.6598** (+1.7) | 0.7137 | 0.6847 (**−2.9**) |
| Hit@5 | 0.7137 | **0.7261** (+1.2) | 0.7801 | 0.7635 (**−1.7**) |
| MRR@5 | 0.5494 | **0.5798** (+3.0) | 0.6492 | 0.5974 (**−5.2**) |
| Decoy Fall (S3+S4) | 0.1304 | **0.1217** (−0.9, tốt hơn) | 0.0783 | 0.1218 (**+4.4, tệ hơn**) |

Rerank cải thiện MỌI metric chính của `e5-large`, nhưng làm TỆ ĐI mọi metric chính của `gemini-001` —
kể cả sau khi đã sửa đúng bug tiêu đề ở trên. Diễn giải: giá trị của một reranker cố định
(`bge-reranker-v2-m3`, chất lượng cố định trên tiếng Việt) là **tương đối với bi-encoder nền**, không
phải cải thiện mặc định. Khi bi-encoder vòng 1 yếu hơn reranker (`e5-large`), "ý kiến thứ hai" nâng
chất lượng lên. Khi bi-encoder vòng 1 đã mạnh hơn reranker cho đúng bài toán này (`gemini-001` —
provider tốt nhất đo được ở trên), ghi đè bằng một ý kiến kém hơn làm loãng đi thứ hạng vốn đã tốt.

### Trần cứng của rerank — đáp án phải NẰM TRONG top-10 vòng 1 thì mới cứu được

| tầng | trần top-10 (`e5-large`) | trần top-10 (`gemini-001`) |
|---|---:|---:|
| S1 | 0.9385 | 0.9538 |
| S2 | 0.7377 | 0.8361 |
| S3 | 0.7833 | 0.8333 |
| S4 | 0.7455 | 0.7636 |

Rerank chỉ SẮP LẠI ứng viên đã lấy ở vòng 1, không tạo ứng viên mới — case có đáp án đúng nằm ngoài
top-10 thì rerank không cứu được bất kể reranker tốt đến đâu.

### Trần theo K — đo tới K=200 (`gemini-001`, đọc từ cache, 0 API call)

Đây là câu hỏi "đáp án đúng có NẰM TRONG pool không", tách hẳn khỏi "có xếp đúng thứ hạng không":

| K | S1 | S2 | S3 | S4 | **macro S1–S4** |
|---:|---:|---:|---:|---:|---:|
| 5 (= `MAX_K` hiện dùng) | 0.8615 | 0.7541 | 0.7833 | 0.7091 | **0.7801** |
| 10 | 0.9538 | 0.8361 | 0.8333 | 0.7636 | **0.8506** |
| 20 | 0.9692 | 0.9344 | 0.9333 | 0.8182 | **0.9170** |
| **50** | 1.0000 | 0.9836 | 0.9833 | 0.9455 | **0.9793** |
| 100 | 1.0000 | 1.0000 | 1.0000 | 0.9636 | **0.9917** |
| 200 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **1.0000** |

**Đây là con số quan trọng nhất trong cả báo cáo cho câu hỏi "làm sao đạt độ chính xác cao".** Đáp án
đúng nằm trong top-50 ở **97.9%** số case. Nghĩa là bài toán hiện tại **KHÔNG phải "không tìm được"**
(recall đã gần như đủ) mà là **"tìm được nhưng xếp sai thứ hạng"** — Hit@5 thực tế mới 0.78 trong khi
trần ở K=50 là 0.98. Khoảng cách 20 điểm đó là dư địa của tầng xếp hạng, không phải của model embedding.

Hệ quả cho thiết kế: mọi nỗ lực "đổi sang embedding tốt hơn" chỉ tranh chấp trong vài điểm phần trăm
(xem §Provider bổ sung — ba model mạnh nhất chênh nhau dưới nhiễu), trong khi **retrieve rộng hơn rồi
lọc lại** chạm được tới 98%. Và đây cũng là lý do rerank ở K=10 không giúp Gemini: ở K=10 bi-encoder
đã sắp gần tối ưu rồi, reranker chỉ tranh chấp lặt vặt. Bài toán reranker CHƯA từng được giao là
"lọc 50 ứng viên xuống 3" — chưa thử, và đó mới là chỗ nó có thể chứng minh giá trị thật.

**Kết luận thử nghiệm**: rerank KHÔNG phải cải thiện mặc định nên bật — phải đo trên đúng cặp
(bi-encoder nền, reranker, ngôn ngữ/domain) đang dùng thật, và phải rerank trên đúng chuỗi đã embed.

### So hai reranker khác nhau — `bge-reranker-v2-m3` (local) vs `cohere/rerank-v3.5` (API qua OpenRouter)

Cùng cách đo (top-10 → rerank → top-5, trên `embedding_input`), đổi reranker để xem kết luận "rerank
giúp/hại" có phụ thuộc vào RERANKER cụ thể hay không. `cohere/rerank-v3.5` gọi qua
`POST https://openrouter.ai/api/v1/rerank` (OpenRouter CÓ mục rerank riêng, ngoài danh mục
chat/completion — endpoint và model được xác nhận trực tiếp từ tài liệu OpenRouter, không suy đoán),
chi phí đo được **$0.001/lượt gọi** (300 case × 3 bi-encoder = 900 lượt, dưới $1 tổng). Ma trận 2
reranker × 3 bi-encoder đo ĐỦ 6/6 ô.

| bi-encoder | metric (macro S1–S4) | trước rerank | sau `bge-reranker-v2-m3` | sau `cohere/rerank-v3.5` |
|---|---|---:|---:|---:|
| `bge-m3` | Hit@1 | 0.4357 | **0.4772** | 0.4606 |
| `bge-m3` | Hit@3 | 0.6183 | **0.6556** | 0.6515 |
| `bge-m3` | Hit@5 | 0.7054 | 0.7137 | **0.7137** (hoà) |
| `bge-m3` | MRR@5 | 0.5320 | **0.5672** | 0.5613 |
| `bge-m3` | Decoy Fall (S3+S4) | 0.1652 | **0.1044** (tốt hơn) | 0.1479 (tốt hơn) |
| `e5-large` | Hit@1 | 0.4440 | **0.4979** | 0.4648 |
| `e5-large` | Hit@3 | 0.6432 | 0.6598 | **0.6846** |
| `e5-large` | Hit@5 | 0.7137 | 0.7261 | **0.7303** |
| `e5-large` | MRR@5 | 0.5494 | **0.5798** | 0.5705 |
| `e5-large` | Decoy Fall (S3+S4) | 0.1304 | **0.1217** (tốt hơn) | 0.1392 (tệ hơn) |
| `gemini-001` | Hit@1 | **0.5726** | 0.4979 (tệ hơn) | 0.4772 (tệ hơn) |
| `gemini-001` | Hit@3 | **0.7137** | 0.6847 (tệ hơn) | 0.6805 (tệ hơn) |
| `gemini-001` | Hit@5 | **0.7801** | 0.7635 (tệ hơn) | 0.7510 (tệ hơn) |
| `gemini-001` | MRR@5 | **0.6492** | 0.5974 (tệ hơn) | 0.5832 (tệ hơn) |
| `gemini-001` | Decoy Fall (S3+S4) | **0.0783** | 0.1218 (tệ hơn) | 0.1392 (tệ hơn) |

Bốn phát hiện:

1. **CẢ HAI reranker đều cải thiện CẢ HAI bi-encoder chưa mạnh nhất** (`bge-m3`, `e5-large`) ở mọi
   metric chính — nhất quán với kết luận "rerank có lợi khi bi-encoder nền chưa phải tốt nhất".
2. **CẢ HAI reranker đều làm TỆ ĐI `gemini-001` ở cả 5 metric MACRO** — khác hẳn hai bi-encoder kia
   (nơi ít nhất một reranker luôn có lợi). Ủng hộ giả thuyết "reranker cố định chỉ có lợi khi
   bi-encoder nền còn kém hơn nó": `gemini-001` là provider mạnh nhất trong 5 provider chính, và cả
   hai reranker (khác nhà, khác kiến trúc) đều không "giỏi" bằng để nâng nó lên.
   *(⚠️ Chỉ mức giảm ở **Hit@1** là ngoài nhiễu (−7.5đ ≈ 2.5 SE); Hit@3/Hit@5 giảm 1.7–2.9đ nằm trong
   nhiễu, và xét theo TỪNG TẦNG thì có tầng còn cải thiện — xem §VÌ SAO rerank hại model mạnh, nơi
   phát biểu này được đo lại và làm chính xác.)*
3. **Trên `bge-m3`, `bge-reranker-v2-m3` thắng CẢ 5 metric** so với `cohere/rerank-v3.5` (dù sát nút ở
   Hit@5/Decoy Fall) — khác với `e5-large`, nơi hai reranker thắng-thua đan xen. Có thể vì
   `bge-reranker-v2-m3` cùng họ BGE với `bge-m3` (cùng nơi huấn luyện/dữ liệu), lợi thế "cùng nhà"
   không chắc còn giữ khi đổi bi-encoder nền.
4. **Trên `e5-large`, hai reranker THẮNG-THUA khác nhau ở từng metric, không có reranker nào thắng
   tuyệt đối**: `bge-reranker-v2-m3` thắng Hit@1/MRR@5 VÀ Decoy Fall Rate; `cohere/rerank-v3.5` thắng
   Hit@3/Hit@5 nhưng làm Decoy Fall Rate TỆ ĐI (0.130→0.139, ngược chiều với `bge-reranker-v2-m3`).

Củng cố kết luận chính: **"rerank có lợi" phải đo cho từng cặp (bi-encoder, reranker) cụ thể — không
suy diễn từ một cặp sang cặp khác, kể cả cùng bi-encoder nền hay cùng reranker.**

> ⚠️ **Cảnh báo nhiễu cho phát hiện 3 và 4**: mọi so sánh reranker-vs-reranker trên CÙNG bi-encoder ở
> bảng trên chênh nhau 0.4–3.3 điểm — **đều dưới 1 SE (0.030)**. Ở cỡ mẫu này **hai reranker KHÔNG phân
> biệt được**. Câu "bge-reranker thắng cả 5 metric trên bge-m3" đúng về con số nhưng **không phải bằng
> chứng** (Hit@5 còn hoà tuyệt đối 0.7137=0.7137); giả thuyết "lợi thế cùng họ BGE" chỉ là suy đoán
> trên một cú hoà thống kê, đừng dùng nó để chọn reranker. Thứ THẬT SỰ ngoài nhiễu chỉ có hai điều:
> (a) rerank giúp `bge-m3`/`e5-large` ở Hit@1 (+4.2 đến +5.4đ), (b) rerank hại `gemini-001` ở Hit@1
> (−7.5đ ≈ 2.5 SE).

### VÌ SAO rerank hại model mạnh — cơ chế đo được, không phải suy đoán

Chạy thêm `gemini-embedding-2` qua cùng reranker để kiểm chứng một dự đoán: nếu giả thuyết "reranker
áp trần riêng của nó" đúng, thì `gemini-2` (Hit@1 trước rerank = 0.5477, TRÊN trần) cũng phải bị hại,
và phải rơi về **cùng một mức** với các bi-encoder khác. Kết quả:

| bi-encoder | Hit@1 TRƯỚC rerank | Hit@1 SAU `bge-reranker-v2-m3` | thay đổi |
|---|---:|---:|---:|
| `bge-m3` | 0.4357 | 0.4772 | **+4.2đ** |
| `e5-large` | 0.4440 | 0.4979 | **+5.4đ** |
| `gemini-2` | 0.5477 | 0.4979 | **−5.0đ** |
| `gemini-001` | 0.5726 | 0.4979 | **−7.5đ** |
| **Độ TRẢI giữa các bi-encoder** | **0.1369** | **0.0207** | — |

Dự đoán đúng: `gemini-2` bị hại y hệt, và **ba bi-encoder khác nhau (xuất phát 0.444→0.573) đều rơi
đúng về 120/241 case = 0.4979**. Độ trải giữa các bi-encoder sụp từ 0.137 xuống 0.021 (dưới 1 SE).

**Cơ chế**: cross-encoder KHÔNG tinh chỉnh thứ tự cũ — nó chấm điểm lại từ đầu cả 10 ứng viên rồi sắp
theo điểm của RIÊNG NÓ. Điểm cosine của bi-encoder bị **vứt bỏ 100%**. Nên bi-encoder chỉ còn giữ một
vai trò duy nhất: quyết định *chunk nào lọt vào pool 10* (recall). Còn *chunk nào đứng #1* thì hoàn
toàn do reranker quyết → **độ chính xác sau rerank ≈ năng lực tự thân của reranker, gần như độc lập
với bi-encoder nào tạo pool.**

Đếm SỬA vs PHÁ ở rank-1 làm cơ chế này thành con số cụ thể:

| bi-encoder | SỬA (sai→đúng) | PHÁ (đúng→sai) | ròng |
|---|---:|---:|---:|
| `gemini-001` | 12 | 30 | **−18 case** |
| `gemini-2` | 14 | 26 | **−12 case** |

Số case reranker SỬA được gần như cố định (12–14) vì nó phản ánh năng lực của chính reranker. Nhưng
số case bị PHÁ tỉ lệ với việc bi-encoder vốn đã đúng bao nhiêu — **bi-encoder càng giỏi càng có nhiều
thứ để mất, trong khi số sửa được không tăng theo → càng giỏi càng lỗ.**

Trần ~0.50 của `bge-reranker-v2-m3` không phải lỗi cấu hình: nó là cross-encoder đa ngôn ngữ dùng
chung, không huấn luyện riêng cho tiếng Việt lĩnh vực chính sách nội bộ có decoy near-miss cố ý.

**Sắc thái quan trọng — thiệt hại tập trung ở rank-1, không trải đều:** với `gemini-2`, Hit@3 chỉ giảm
0.4đ (0.7012→0.6971) và Hit@5 giảm 0.4đ (0.7884→0.7842) — **cả hai đều trong nhiễu, coi như không
đổi**. Và ở tầng S1, rerank thực ra LÀM TỐT HƠN cho `gemini-001` (Hit@3 0.80→0.86, Hit@5 0.86→0.89).
Nên phát biểu "rerank hại gemini ở MỌI metric, không ngoại lệ" ở phát hiện 2 phía trên là **quá mạnh**
— chính xác hơn: *rerank hại rõ và chắc chắn ở rank-1; ở Hit@3/Hit@5 thì trộn lẫn theo tầng và phần
lớn nằm trong nhiễu.* Với production dùng `top_k=3`, rerank trên Gemini gần như **vô hại nhưng cũng
vô ích** — chỉ tốn thêm một tầng tính toán.

Đây là thử nghiệm ngoài luồng (không nằm trong `_harness.py`/CI), không phải khuyến nghị production.

## Còn để mở

0. **Ngưỡng `decoy_fall` 0.35 chưa được chọn lại trên validation set.** Nó vẫn là con số quét trên
   chính 300 case dùng để báo cáo (§Gate) — đúng sai sót phương pháp #2 của `kb#38`. Split đã có
   (`validation-split.json`, 98 case), việc còn lại là chọn lại ngưỡng CHỈ trên tập đó rồi báo cáo
   trên `test`. Ưu tiên cao nhất trong danh sách này vì nó là gạch DoD đang mở.

Xếp theo đòn bẩy — việc đầu tiên là thứ dữ liệu ở §Trần theo K chỉ thẳng vào.

1. **Rerank/lọc ở K=50 thay vì K=10** — trần recall ở K=50 là 97.9% còn Hit@5 thực tế mới 78.0%; đây
   là dư địa lớn nhất còn lại và chưa ai chạm vào. Cũng là phép thử công bằng duy nhất cho reranker
   trên Gemini (ở K=10 nó chỉ tranh chấp thứ hạng bi-encoder đã sắp gần tối ưu).
2. **Chưa thử bỏ prefix/`task_type`** của `e5-large`/`gemini`/`qwen3` để đo chênh lệch thực tế mà quy
   ước bất đối xứng mang lại trên bộ case này (treo từ bản báo cáo trước).
3. **Chưa đo reranker thứ ba** `qwen/qwen3-reranker-8b` (thấy trên OpenRouter khi tra
   `cohere/rerank-v3.5`). Ưu tiên thấp: cơ chế "reranker áp trần riêng" dự đoán nó cũng sẽ kéo mọi
   bi-encoder về trần của chính nó — đáng đo chỉ khi trần đó cao hơn ~0.57 của Gemini.
4. **`decoy_fall` có phiên bản tốt hơn chưa wire**: DFR *có điều kiện* — `P(hạng #1 = decoy | hạng #1
   SAI)` — tách được "bị bẫy" khỏi "sai nói chung" (DFR thô bị nhiễu bởi độ chính xác: model càng
   đúng nhiều càng ít cơ hội rơi bẫy). Đã tính thử: dim-8 0.044 · gemini-001 0.170 · e5-large 0.217 ·
   hash1024 0.202 · bge-m3 0.264. Vẫn KHÔNG sửa được vấn đề gốc (dim-8 vẫn "thắng"), nên chưa đưa vào
   harness — ghi lại để không phải tính lại.
5. **S5 (59 case, ~20% bộ case) không nằm trong bất kỳ con số Hit@k nào** ở báo cáo này. Mọi phát biểu
   dạng "đạt X% độ chính xác" ở đây đều chỉ tính trên 241 case S1–S4. Độ chính xác end-to-end tính cả
   khả năng TỪ CHỐI đúng ở S5 là câu hỏi khác, phụ thuộc tầng sinh câu trả lời, không chỉ retrieval.
