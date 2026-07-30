# Bằng chứng D9 — phần DE (kb)

> **Mục đích:** phần của DE trong evidence-pack chung (`day-09.md:31`, DoD `:55`). Viết theo chuẩn
> *"đủ để chấm **không cần hỏi**"* — nghĩa là mọi con số dưới đây phải **tái lập được** bằng lệnh
> trong §1, không phải tin lời khai.
>
> Người gom pack: lấy §1 (lệnh), §2 (số), §3 (link PR), §4 (lỗ đã biết). §5 là phần cần chuyển tới
> chủ `test_leak.py`.

---

## 1. Chạy lại — khối lệnh dán-là-chạy

Từ **thư mục gốc của kit** (`agentcore-studio-kit/`):

```bash
docker compose -f docker-compose.test.yml up -d --wait

export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5433/studio_test
export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test

uv run pytest packages/kb -q                          # 68 passed, 2 xfailed, 0 skipped
uv run python packages/kb/scripts/mutation_check.py   # 8/8 mutant bắt đúng bài đã khai
uv run python packages/kb/scripts/mutation_sweep.py   # 93 mutant, 9 sống sót (~60s)
```

Đã kiểm bằng cách `docker compose ... down -v` xoá sạch container + volume rồi chạy lại từ đầu — khối
trên dựng lại được toàn bộ, không cần bước tay nào khác.

### ⚠️ Hai dòng `export` là bắt buộc, và đây là chỗ dễ mất điểm oan

`make test-int` **không** export DSN — nó chỉ `docker compose up` rồi `uv run pytest`. Chạy theo
`make test-int` thì kết quả là:

```
36 passed, 34 skipped        ← KHÔNG phải 68 passed
```

34 test tầng DB bị skip **lặng lẽ**, và người đọc sẽ kết luận con số 68 trong tài liệu này là khai
láo. Đây không phải lỗi của người chấm — `01-FOUNDATION.md` §2 của bộ test-design cũng ghi nhận đúng
điểm này về `make test-int`.

`mutation_check.py` **từ chối chạy** khi thiếu DSN (thoát mã 1) thay vì chạy rồi cho số sai. Lý do:
trước khi vá, thiếu DSN vẫn có 36 test chạy nên cảnh báo "0 test" không bắt được, và script báo
`M4 không cắn` trong khi thực tế nó cắn — một công cụ đo tự tin trong khi đo nhầm thứ, đúng họ lỗi
cả bộ này sinh ra để chống.

### Cảnh báo an toàn dữ liệu

Guard trong `conftest.py:67` là `if not (port_ok or dbname_ok)` — **`or`, không phải `and`**, và
**không kiểm host**. Fixture `TRUNCATE` 5 schema không hỏi lại. Chỉ export DSN thoả **cả ba**:
`localhost` + cổng `5433` + db `studio_test`. Một DSN trỏ máy khác mà trùng cổng 5433 sẽ lọt guard.

---

## 2. Số đo

### 2.1 Suite

| | |
|---|---|
| trước khi bật Postgres | `35 passed, 31 skipped` |
| **sau (số nộp)** | **`68 passed, 2 xfailed, 0 skipped`** |
| `uv run ruff check packages/kb` | sạch |
| chống flaky | chạy sạch **30 lần liên tiếp, 68 passed cả 30** |

`2 xfailed` là hai case `test_leak.py` — xem §5, đó là ratchet có chủ đích, không phải test hỏng.

### 2.2 Mutation — bộ tuyển chọn (`mutation_check.py`)

8 mutant, mỗi mutant **khai trước tên bài phải đỏ** rồi so với thực tế. Nhờ vế khai-trước này mà
script là một bài test của chính bộ test, không phải bảng số in ra.

| mutant | đổi gì | bắt |
|---|---|---|
| M1 | `StaticKbSearch.search` trả `[]` | 13 |
| M2 | `PgTraceReader.read_run` trả `[]` | 13 |
| M3 | reader đánh rơi `citations` | 3 |
| M5 | reader trả `tokens` 0/0 | 1 |
| M6 | reader trả `cost=0.0` | 1 |
| M7 | interpreter tiêm `recipe.tenant_id` vào kb-retrieve | 1 |
| M8 | `TraceEvent` mang `recipe.tenant_id` | 1 |
| M4 | `citations_from_trace` siết theo `node_type` (evalhub) | 1 |

**Kết: 8/8 bắt đúng bài đã khai.**

M7/M8 đánh vào INV-1 và M4 nằm ngoài kb (evalhub) — cả ba **trước D9 cho 0 test đỏ**, tức bất biến
trung tâm của D8 và hợp đồng "một nguồn số" của `:53` chưa được bài nào khoá.

### 2.3 Mutation — quét mù toàn `src` (`mutation_sweep.py`)

93 mutant AST, ~60 giây, 4 loại toán tử (so sánh · `and`/`or` · `not` · hằng bool/int).

**9 sống sót**, đọc từng cái: **7 tương đương** (phân loại ghi trong docstring script), **2 lỗ thật**
đã vá trong chính PR này:

- `postgres.py` biên `top_k=1` — bài có sẵn kiểm 0 và 2, bỏ đúng số 1 ở giữa. Bản `StaticKbSearch`
  đã khoá biên này từ D4; bản Postgres thì chưa, mà hai bản phải thay được cho nhau.
- `embeddings.py` nhánh vector-0 — docstring `derive_vector` chốt hành vi và nói rõ lý do (pgvector
  tính cosine với vector 0 ra `NaN` → thứ hạng vô nghĩa **mà không lỗi nào nổi lên**) nhưng không bài
  nào kiểm.

Hai mutant sống sót đáng ghi ngược lại — chúng cho thấy code **phòng thủ nhiều lớp**, không phải hở:
`if top_k <= 0 or not section_roles` đổi thành `and` vẫn an toàn vì SQL cũng fail-closed;
`zip(..., strict=True)` đổi thành `False` vẫn an toàn vì dòng trên đã `raise` khi lệch độ dài.

**Giới hạn phải biết:** 4 loại toán tử nói trên KHÔNG phủ xoá câu lệnh, đổi giá trị trả về, hằng
chuỗi, biên lát cắt, nhánh bắt ngoại lệ. `static_search.py` 0 sống sót nghĩa là sạch **theo bốn loại
này**, không phải sạch tuyệt đối.

### 2.4 Hai bug trong chính công cụ đo — ghi lại vì bài học đáng hơn cái bug

**① Regex trượt vì mã màu ANSI.** pytest phun `\x1b[31m` trước `FAILED` kể cả khi stdout là pipe, nên
regex neo đầu dòng không khớp: script báo *"không cắn"* cho **mọi** mutant trong khi **số đếm vẫn
đúng**. Chỉ so số đếm thì không ai phát hiện; chính cơ chế khai-trước-tên-bài-phải-đỏ bắt được.

**② Bytecode cũ làm mutant không có hiệu lực.** Sweep chạy ba lần ra 8, 7, 8 sống sót — danh sách
khác nhau. Python quyết định `.pyc` còn dùng được bằng **(mtime giây, kích thước file)**; mutant đổi
một ký tự (`1`→`2`, `0`→`1`) giữ **nguyên kích thước** và sweep ghi file trong cùng một giây, nên
Python nạp lại bytecode **cũ**. Vá bằng xoá `__pycache__` + cờ `-B`. Sau khi vá: **9 sống sót, ổn
định qua nhiều lần chạy** — và con số 8 ban đầu là **đếm thiếu**.

Đã loại trừ khả năng suite tự flaky (30 lần chạy sạch, 68 passed cả 30).

---

## 3. Link PR

| repo | PR | nội dung |
|---|---|---|
| `agentcore-studio-kb` | [#5](https://github.com/AI20K-VGR/agentcore-studio-kb/pull/5) | spine truyền `session_context` — **merged** |
| `agentcore-studio-kb` | [#6](https://github.com/AI20K-VGR/agentcore-studio-kb/pull/6) | harden: cầu chì, payload rebuild-read, INV-1, 2 script mutation |
| `agentcore-report` | [#24](https://github.com/AI20K-VGR/agentcore-report/pull/24) | daily-note D9 — **merged** |
| `agentcore-report` | [#25](https://github.com/AI20K-VGR/agentcore-report/pull/25) | daily-note D1 (backfill, bù chuỗi D1–D9) |

**PR kb#6 sẽ đỏ CI, và không phải lỗi test.** Kit `main` ghim `packages/engine` ở `a65c9d6`
(merge PR #11, **Day 7**), cách engine `main` (`a6967a2`, PR #12 Day 8) **4 commit**. Bản đó có **0**
lần `session_context`. CI dựng workspace từ con trỏ kit rồi mới overlay code PR, nên
`from studio_workbench.tenant_wall import resolve_session` là `ModuleNotFoundError` ngay lúc collect.
Workbench và evalhub đã bump đủ, riêng engine dừng ở D7.

Bump con trỏ **hiện chưa an toàn**: chạy toàn workspace với con trỏ mới cho `6 failed, 265 passed`,
cả 6 ở `packages/workbench` cùng dòng `TypeError: run() missing 1 required keyword-only argument:
'session_context'`. Chuỗi thật: **SWE cập nhật workbench (#43) → kit bump con trỏ → CI kb xanh.**

---

## 4. Lỗ đã biết trong phần DE — khai ra, không giấu

- **`test_leak.py` 2 case `xfail(strict=False)`**, job `leak-test` là `continue-on-error`. Đây là
  ratchet có chủ đích (un-ratchet là việc riêng, xem `postgres.py:9-13`), nhưng hệ quả phải nói rõ:
  **job tên `leak-test` đang xanh mà không đánh giá assertion nào.**
- **Vế `roles` của INV-1 chưa ai hiện thực.** `KbRetrieveExecutor` docstring (`executors.py:90-95`)
  chốt `section_roles` phải server-resolve, nhưng `:138` đọc thẳng `node.params` — tức từ recipe, tức
  client khai. `session_context.roles` không được đọc ở đâu trong engine. INV-1 hiện chỉ chặn trục
  `tenant`. Việc AIE-1/SWE.
- **Hợp đồng `ts` chưa chốt.** `test_trace_reader.py::test_ts_trung_nhau_giu_nguyen_thu_tu` ghi
  *"`ts` trùng là bình thường"*; `engine/tests/test_interpreter_determinism.py` (PR #13 đang mở)
  `assert len(set(timestamps)) == 4`. Hai giả định ngược nhau. Đo được: khoảng cách nhỏ nhất giữa hai
  node là **5 µs** (300 lần chạy, 0 lần trùng) — cả hai cùng xanh, nhưng chỉ do may.
- **`sorted()` trong `load_callisto` không load-bearing.** Docstring nói nó tồn tại *"để `chunk_id` ổn
  định giữa các lần chạy"*; mutant bỏ `sorted()` không làm test nào đỏ, vì `chunk_id` sinh từ tên file
  và mọi consumer đều sắp lại. Vô hại, nhưng lý do ghi trong docstring sai.

---

## 5. Chuyển tới chủ `test_leak.py` — `test_t6_label_spoof` thiếu răng

**Không sửa, chỉ báo.** `test_leak_meta.py` tồn tại chính để phát hiện người ngoài chỉnh
`test_leak.py`; đụng vào là phá đúng cơ chế đang bảo vệ file đó.

**Sự bất đối xứng.** `test_leak.py::test_t1_idor` có positive-inclusion guard:

```python
assert "chunk-a-1" in result_chunk_ids   # dòng ~50
```

đúng như comment dual-review ngay trên nó dặn (*"a lazy/broken impl that returns an empty list would
false-pass the exclusion assertion below — ∅ trivially excludes everything"*, catch gemini F4).

`test_t6_label_spoof` ngay dưới (`:55-69`) seed **hai** chunk nhưng **chỉ** assert chunk mật không có
mặt — **không** đòi `chunk-public` phải có mặt. Một impl trả `[]` sẽ pass.

**Và `test_leak_meta.py:25` mã hoá luôn sự bất đối xứng đó** — nó khoá đúng một assert, nên bản vá
đúng cũng không thể thêm vào mà không chạm anti-tamper.

**Vì sao báo bây giờ dù chưa cắn.** Hôm nay chưa cắn vì `xfail` + `KbSearchService` còn là spec stub.
Nó cắn **đúng lúc un-ratchet** — tức đúng lúc nó trở thành hard gate, và lúc đó không ai còn nhớ chỗ
này. Đây cũng là tiền lệ của chính repo, không phải ý riêng: mentor đã vấp đúng khuôn lỗi này và ghi
lại ở `test_leak.py:46-50`.

**Đề xuất (một dòng, chủ file quyết định):**

```python
assert "chunk-public" in result_chunk_ids, "truy xuất phải trả về thật thì phép loại trừ mới có nghĩa"
```

kèm cập nhật `test_leak_meta.py` **trong cùng commit** để anti-tamper khoá cả hai assert thay vì một.

**Bối cảnh liên quan, nếu hữu ích:** cùng khuôn lỗi này đã được đo trong `packages/kb` hôm nay — ba
chỗ có assert loại trừ mà vẫn XANH khi cho `StaticKbSearch.search` trả `[]`; sau khi thêm cầu chì thì
cả ba đỏ. Xem §2.2 M1.

**Và một liên hệ đáng chú ý với §4.** Docstring của chính `test_t6_label_spoof` viết: *"the request
itself declares `section_roles=["confidential"]` — **the server must resolve authorized roles itself
(never trust the client-declared list)**"*. Tức T6 là bài kiểm **vế `roles` của INV-1** — đúng cái vế
mà §4 ghi là chưa ai hiện thực (`executors.py:138` vẫn đọc `section_roles` thẳng từ `node.params`).

Nên hai việc này là một: bài test canh vế `roles` đang thiếu răng, **và** thứ nó canh cũng chưa được
dựng. Vá răng cho test mà không dựng hàng rào thì test sẽ đỏ và đỏ đúng — nên thứ tự hợp lý là chốt
câu hỏi *"ai resolve `section_roles`"* trước (đang nằm trong danh sách câu hỏi mở của bộ test-design),
rồi vá test theo câu trả lời.
