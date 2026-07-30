# Plan D9 (DE) — Harden: test negative phải cắn thật + chuẩn bị evidence-pack

> **Ngày:** 2026-07-30 (D9, G2) · **Bút:** DE (Nguyễn Đông Anh) · **Repo WRITE:** kb · **READ:** kit
>
> Issue: `docs/requirements/week-1/days/day-09.md`. Việc DE (`:36`): *"Test **trace ordering (0-gap) +
> rebuild-read** + `kb.search` **tenant-mismatch trả rỗng**; golden 5 case ổn định"*. DoD chung `:52-56`.
> Ràng buộc `:45`: *"Test negative phải bắt lỗi thật. Không thêm feature mới — chỉ harden."*
>
> **Gate 31/07** — evidence-pack nộp **trước 24h**, tức trong ngày D9.

---

## 0. Đánh giá khối lượng — ba việc chữ trong `:36` gần như đã có, việc thật nằm ở `:52`

Nói thẳng để không thổi phồng. Ba deliverable ghi trong `:36` đều đã tồn tại từ D5–D8:

| `:36` đòi | Đã có ở đâu | Trạng thái |
|---|---|---|
| Test trace **ordering** | `test_trace_reader.py` — `test_xao_tron_thu_tu_van_doc_ra_dung_thu_tu_ts`, `test_ts_trung_nhau_giu_nguyen_thu_tu`, `test_ts_sai_dinh_dang_thi_raise` | ✅ D5 |
| Test **0-gap** | `test_du_4_node_thi_0_gap`, `test_bo_1_node_thi_reader_bao_thieu`, `test_mot_node_emit_hai_lan_cung_bi_bao` | ✅ D5–D6 |
| Test **rebuild-read** (đọc lại từ DB) | `test_db_doc_lai_dung_thu_tu_va_bao_0_gap`, `test_db_hai_run_xen_ke_khong_lan_nhau`, `test_db_khong_doc_cheo_tenant` + 3 test DB khác | ✅ D5–D6 (16 test trace tổng) |
| `kb.search` **tenant-mismatch trả rỗng** | `test_tenant_wall.py::test_tenant_la_tra_rong_fail_closed` (W3) | ✅ **D8, hôm qua** |
| Golden 5 case | `golden/smoke-5.yaml` (5 case) + `smoke-10.yaml` (10 case) | ✅ D4/D6 |

→ Nếu chỉ đọc `:36` thì D9 của DE gần như **xong sẵn**. Đó chính là cái bẫy của hôm nay.

**Việc thật nằm ở DoD `:52`: *"Test negative bắt lỗi thật (không phải test giả)."*** Và DE có **bằng
chứng cứng trong tay** rằng test của mình có thể là test giả — hôm qua SWE review kb#4 bắt được
`test_tenant_wall.py` chiều B→A thiếu `assert res_rev`, nên tập rỗng làm hai assert dưới pass rỗng
nghĩa. Đã vá (`77dd9e4`). Nhưng một chỗ lộ ra thì phải hỏi: **còn chỗ nào nữa?**

D9 với DE = **audit chính test của mình bằng đúng phép soi đã bắt được lỗi hôm qua**, không phải viết
test mới cho những thứ đã test rồi.

---

## 1. Hai điều chốt trước để plan không trôi

**① "Test giả" ở đây có nghĩa hẹp và kiểm được, không phải lời hô.** Khuôn lỗi cụ thể:

```python
res = await kb.search(...)              # nếu res == []
assert all(x == MONG_DOI for x in res)  # → True  (all của rỗng)
assert not any(x == CAM for x in res)   # → True  (any của rỗng là False)
```

Test xanh mà không kiểm gì. Thuốc là **một dòng cầu chì** `assert res, "..."` — nó không giữ test xanh,
nó làm test **đỏ to** khi truy xuất chết, thay vì im lặng báo đạt. Mentor đã vấp đúng chỗ này và ghi
lại trong `test_leak.py:46-50` (*"a lazy/broken impl that returns an empty list would false-pass the
exclusion assertion below (∅ trivially excludes everything)"* — dual-review catch gemini F4). Đây là
tiền lệ của chính repo, không phải ý riêng.

**② Không thêm feature (`:45`).** Mọi thứ dưới đây là test + tài liệu. Không đụng `src/studio_kb/`
trừ khi audit lộ ra bug thật ở code nguồn — mà nếu lộ thì sửa code, **không nới test cho khớp**.

---

## 2. Việc DE thật sự còn — 6 mục

### D9-1 · Audit vacuous-pass toàn bộ test kb ⭐ (mục lõi, phục vụ DoD `:52`)

Đã quét trước một lượt (29/07). Kết quả — **3 chỗ hở, 4 chỗ đã an toàn**:

| Chỗ | Assert | Có cầu chì? |
|---|---|---|
| `test_static_search.py:104` | `assert all(h.tenant_id == ANKOR_ID for h in hits)` | ❌ **hở** — cùng khuôn hệt lỗi SWE bắt (ankor hỏi về Borea) |
| `test_pg_kb.py:167` | `assert all(h.chunk_id != "ankor-salary-001#c1" for h in sai_vai)` | ❌ **hở** — loại trừ theo vai, rỗng thì pass |
| `test_static_search.py:40` | `assert all(h.chunk_id and h.text and ... for h in hits)` | ❌ hở, nhưng **QUYẾT ĐỊNH: vẫn thêm cầu chì**. Răng thật của test là chữ ký 4-kwarg không raise `TypeError`, nên assert này chỉ là trang trí — chính vì thế mà nó nguy hiểm: người đọc tưởng có kiểm nội dung. Một dòng, làm cho xong |
| `test_spine_live.py:173` | `assert all(e.inputs_hash for e in events)` | ⚠️ rỗng thì `len(set())==len([])` cũng True → hở về lý thuyết; fixture `spine` che. Thêm cầu chì cho rẻ |
| `test_pg_kb.py:207` | `assert sc01, "truy xuất phải trả về thật thì phép loại trừ mới có nghĩa"` | ✅ **DE đã tự dùng đúng khuôn này rồi** |
| `test_pg_kb.py:148` | có `assert "ankor-leave-001#c1" in ids` phía trên | ✅ chặn bằng inclusion |
| `test_spine_live.py:189` | có `assert chunks, "..."` | ✅ |
| `test_static_search.py:93`, `test_doc_factory.py:46` | `hits[0]` / `roles[...]` → `IndexError`/`KeyError` nếu rỗng | ✅ chặn bằng cấu trúc (đỏ to) |

**Việc:** thêm cầu chì cho 3–4 chỗ hở, mỗi chỗ kèm một dòng comment nói **vì sao** nó tồn tại (để người
sau không xoá vì tưởng thừa — đúng cách đã làm ở `77dd9e4`).

**Nghiệm thu không được tự khai.** Với mỗi cầu chì thêm vào, chứng minh nó **có tác dụng**: tạm ép
truy xuất trả rỗng (đổi tenant thành `uuid4()`, hoặc query rác) → test phải **đỏ**; bỏ cầu chì ra →
test **xanh** trên cùng dữ liệu rỗng đó. Chênh lệch đỏ/xanh chính là bằng chứng "negative cắn thật"
mà `:52` đòi. Ghi cặp số này vào daily-note.

### D9-2 · Golden set "ổn định" — định nghĩa cho được rồi mới đo

`:36` đòi *"golden 5 case ổn định"*, `:54` đòi *"bảng điểm chạy lại ra **cùng** số"*. Hai câu này về
**determinism**, và phần DE sở hữu là **nguồn dữ liệu** (`smoke-5.yaml`, `smoke-10.yaml`,
`load_callisto()`), không phải bộ chấm (AIE-2, đã có `test_determinism.py`).

**Đã kiểm trước (29/07) — ổn định sẵn, nên đây là việc RẺ.** Chạy `StaticKbSearch.search` ở 3 tiến
trình với `PYTHONHASHSEED` khác nhau (1/7/42), kết quả **giống hệt từng chunk_id và score**:

```
seed=1  [('ankor-leave-001#c1',1.0), ('ankor-leave-001#c2',0.5), ('ankor-leave-001#c3',0.5), ('ankor-leave-001#c5',0.5), ('ankor-expense-001#c1',0.25)]
seed=7  ... giống hệt
seed=42 ... giống hệt
```

Chỗ đáng lo nhất đã tự loại: **ba chunk đồng điểm 0.5** mà thứ tự vẫn cố định qua mọi seed — nếu có
`set()`/`dict` lọt vào đường sắp xếp thì đúng chỗ hoà điểm này sẽ trôi. Không trôi.

→ Việc còn lại chỉ là **khoá tính chất đã đúng thành test** (~15 phút), không phải đi tìm bug. Nếu
sau này ai đổi thuật toán xếp hạng (S2 vector) thì test này là cái báo.

### D9-3 · Sửa `test_spine_live.py` cho chạy lại được (chặn D9-1 và evidence-pack)

`engine@main` giờ đòi `session_context` bắt buộc (`a6967a2`, PR #12 merged 29/07).
`test_spine_live.py:86` gọi `run()` không truyền → `TypeError`. Hiện **đang SKIP** vì thiếu Postgres nên
chưa ai thấy đỏ, nhưng D9 đòi **rebuild-read** — mà rebuild-read chính là 4 test DB trong file này.
Không sửa thì không có bằng chứng chạy thật để nộp.

Sửa: file đã import `studio_workbench` (dòng 40) và `.importlinter` chỉ soi `src`, không soi test — nên
dùng thẳng `resolve_session()` của SWE:

```python
result = await run(
    recipe,
    session_context=resolve_session({"tenant_id": tenant_id, "user": "spine-test"}),
    ...
)
```

**Đây không chỉ là vá chữ ký.** Làm vậy thì spine test thành **chỗ duy nhất trong cả kit chạy trọn
chuỗi thật**: resolver SWE → interpreter AIE-1 → fence DE → Postgres → đọc lại. Gần nhất với chứng minh
DoD `:52` của D8 mà đến giờ chưa ai trong nhóm có. Xem `docs/inv1_tenant_wall.md` §5.1.

**⚠️ RỦI RO HẠ TẦNG — làm ĐẦU TIÊN trong ngày, trước cả D9-1.** Kiểm 29/07: `docker-compose.test.yml`
có, nhưng **Docker daemon không chạy trên máy này**. 31 test kb đang skip suốt vì thế.

Ba thứ cùng phụ thuộc vào việc Postgres lên được: (a) bằng chứng rebuild-read của `:36`, (b) con số
suite thật trong evidence-pack `:55`, (c) chính D9-3 này. Nếu để chiều mới phát hiện không lên được thì
**ba mảng sập cùng lúc vào đúng hôm trước gate**. Vì vậy: `docker compose -f docker-compose.test.yml up -d`
là việc **09:00**, không phải việc lúc cần tới.

**Phương án lùi nếu Postgres không lên được:** nộp kết quả tầng tĩnh (`StaticKbSearch`, `check_walk`
thuần — vốn không cần DB) **kèm câu nói rõ ràng cái gì chưa chứng minh được và vì sao**, thay vì im
lặng để mentor tự đoán 31 skip nghĩa là gì. Trung thực về khoảng trống tốt hơn một bảng số trông đầy đủ.

### D9-4 · Báo mentor: `test_t6_label_spoof` thiếu răng — BÁO, KHÔNG SỬA

Phát hiện 29/07 khi soát theo `:52`. `test_leak.py::test_t1_idor` có positive-inclusion guard
(`assert "chunk-a-1" in result_chunk_ids`, dòng 50) đúng như comment dual-review dặn. Nhưng
`test_t6_label_spoof` ngay dưới (dòng 55-69) seed **hai** chunk mà chỉ assert chunk mật **không** có mặt
— **không** đòi `chunk-public` phải có mặt. Impl trả `[]` sẽ pass. Và `test_leak_meta.py:25` (anti-tamper)
cũng chỉ khoá đúng một assert đó, tức mã hoá luôn sự bất đối xứng.

Chưa cắn hôm nay (`xfail` + `KbSearchService` còn là spec stub), nhưng **cắn đúng lúc un-ratchet** — tức
đúng lúc nó thành hard gate.

**Ranh giới:** `test_leak.py`/`test_leak_meta.py` do skeleton mentor mang vào, và `test_leak_meta.py`
tồn tại chính để phát hiện người ngoài chỉnh `test_leak.py`. **Tuyệt đối không sửa.** Việc DE là viết
một đoạn báo, dựa trên chính comment "gemini F4" của mentor làm tiền lệ.

### D9-5 · Phần DE trong evidence-pack (`:55`)

`:55` đòi *"đủ để mentor chấm không cần hỏi"*. Phần DE gom:

- Output `pytest packages/kb` **có Postgres bật** (số passed thật, không phải 31 skip) — *phụ thuộc D9-3, xem rủi ro hạ tầng*.
- Cặp số đỏ/xanh của D9-1 chứng minh negative cắn thật.
- Link PR: kb#4 (day8/tenant-wall) + PR D9.
- `docs/inv1_tenant_wall.md` — sơ đồ ba mảnh INV-1 ráp vào nhau (viết D8). **Cần refresh số dòng:** §5.1
  và §2 trích `interpreter.py:219`/`:271` từ nhánh trước merge; sau `a6967a2` chúng là **`:241`/`:293`**.
  Doc có ghi "đọc lại nếu đã merge" nhưng đã nộp làm bằng chứng thì sửa cho đúng, 1 phút.
- Bảng điểm `scripts/smoke_eval_d6.py` **6/10** — **chỉ có được sau khi Q-A chốt**; thiếu một dòng
  `session_context` thì script không chạy, và đây là con số trung tâm của pack.

### D9-6 · Daily-note D9 + rà D1–D9 liền mạch (`:22`, `:56`)

`:22` đòi *"rà daily-notes D1–D9 liền mạch"*. **Đã rà 29/07 — có lỗ hổng thật:** ba note của DE
(`2026-07-23` D4, `2026-07-24` D5, `2026-07-27` D6 — 273/71/219 dòng, hoàn chỉnh) nằm trên nhánh
`origin/daily-note/d6-DongAnh2704` **chưa từng được mở PR**. Merge sạch, không conflict.

**Việc D9-6a: mở PR cho nhánh đó** — nếu không, hồ sơ DE trước gate thiếu D4/D5/D6, mà note D6 chính là
chỗ ghi *"AIE-2 nghỉ, tôi nhận làm thay smoke-eval"*. Thiếu nó thì đóng góp bị đọc lệch.

Cũng đang kẹt (không phải việc DE, báo giúp): `2026-07-27-Dozyboy.md`, `2026-07-29-TranBaDat2607.md`.

---

## 3. Phụ thuộc & câu hỏi chặn (gửi đầu giờ)

| # | Cho ai | Câu hỏi | Vì sao chặn |
|---|---|---|---|
| **Q-A** | **AIE-2 / cả nhóm** | `scripts/smoke_eval_d6.py:173` gọi `run()` không có `session_context` → vỡ với `engine@main`. **Bản vá đã biết và đã kiểm chạy được**: thêm `session_context=resolve_session({"tenant_id": tenant_id, "user": "smoke-eval"})` trong `run_case` (script đã import `studio_workbench` sẵn) → chạy ra **6/10 PASS**, `lint-imports` KEPT. Ngày 29/07 đã dựng rồi **revert** vì có thông tin AIE-2 đã làm — nhưng `origin/main` repo cha không có commit nào chạm file này (gần nhất vẫn là `556607c` của DE), và PR #65 mở từ 28/07 chỉ sửa 1 dòng import. **Câu hỏi: AIE-2 đã vá ở đâu, hay để DE đặt lại một dòng đó?** | Đây **không phải bài toán chưa giải — là quyết định chưa chốt**. Bảng điểm 6/10 là con số trung tâm của evidence-pack `:55`, và `:53` đòi smoke-eval đọc citation từ trace. Một dòng chặn cả hai |
| **Q-B** | **AIE-2** | `:53` *"smoke-eval lấy citation từ trace (một nguồn số)"* — `citations_from_trace` đọc `TraceEvent.citations` do interpreter điền. DE cần confirm định dạng đang khớp, hay AIE-2 vẫn tính rời ở đâu đó? | `:53` là DoD chung; nếu hai bên tính hai kiểu thì "một nguồn số" hỏng, mà nguồn là trace của DE |
| **Q-C** | **mentor / chủ evidence-pack** | Evidence-pack là **một** tài liệu chung (`:42`) — nằm ở repo nào, ai gom, format gì? | `:55` nộp trước 24h; không biết chỗ nộp thì phần DE gom xong vẫn không vào được pack |
| **Q-D** | **mentor** | `test_t6_label_spoof` thiếu positive-inclusion mà `test_t1_idor` có (D9-4) — có phải chủ đích không? | Nếu cố ý thì DE ghi là nợ đã biết; nếu sót thì cần chủ file sửa trước un-ratchet |

---

## 4. Lịch

| Mốc | Việc | ⬜ |
|---|---|---|
| **09:00 — trước hết** | **Bật Docker + `docker compose -f docker-compose.test.yml up -d`.** Daemon đang không chạy (kiểm 29/07). Lên được hay không quyết định D9-3 + D9-5 + bằng chứng `:36` — phải biết lúc 09:00, không phải 17:00 | ⬜ |
| Đầu giờ | Gửi **Q-A** (chặn evidence-pack) + **Q-C** (chỗ nộp) · mở PR nhánh `daily-note/d6-DongAnh2704` (**D9-6a**) | ⬜ |
| Sáng | **D9-3** sửa `test_spine_live` → chạy full kb có DB, ghi lại số | ⬜ |
| Sáng | **D9-1** audit vacuous-pass: vá 3–4 chỗ + chứng minh đỏ/xanh từng cái ← **mục lõi, chạy được kể cả khi Postgres hỏng** | ⬜ |
| Chiều | **D9-2** khoá test ổn định (đã verify sẵn — việc rẻ, ~15 phút) | ⬜ |
| Chiều | **D9-4** soạn đoạn báo mentor về `test_t6` · **D9-5** gom phần DE của evidence-pack | ⬜ |
| Cuối ngày | **D9-6** daily-note D9 · mở PR kb nhánh `day9/...` | ⬜ |

---

## 5. DoD D9 — phần DE

- [ ] `:52` **Test negative bắt lỗi thật.** 3–4 cầu chì thêm vào, mỗi cái kèm cặp số đỏ/xanh chứng minh
      nó cắn (D9-1). Đây là mục **có trọng lượng nhất** của DE hôm nay.
- [ ] `:53` smoke-eval lấy citation từ trace — **chủ yếu AIE-2**; DE cấp nguồn trace + confirm định dạng (Q-B).
- [ ] `:54` bảng điểm chạy lại ra cùng số — DE khoá tầng dữ liệu (D9-2); bộ chấm là AIE-2.
- [ ] `:55` evidence-pack — phần DE gom xong (D9-5), chờ Q-C biết chỗ nộp.
- [ ] `:56` daily-note D9 (D9-6) + **3 note D4/D5/D6 được merge** (D9-6a).
- [ ] `:36` trace ordering / 0-gap / rebuild-read / tenant-mismatch — **đã có từ D5–D8**; D9 chỉ chạy
      thật có DB để lấy bằng chứng, không viết mới.

**Tóm tắt khối lượng:** ~một ngày, nhưng phân bố lệch. Ba deliverable chữ trong `:36` gần như xong sẵn;
công thật đổ vào **audit test giả** (D9-1), **bật Postgres chạy thật** (D9-3), và **gom bằng chứng
trước gate** (D9-5). Rủi ro lớn nhất không phải code — là Q-A: nếu `smoke_eval_d6.py` không ai vá thì
evidence-pack thiếu con số trung tâm.
