# Plan D10 (DE) — GATE-1: demo walking-skeleton chạy thật + teach-back

> **Ngày:** 2026-07-31 (D10, **GATE-1 cứng**) · **Bút:** DE (Nguyễn Đông Anh)
> **Anchor:** issue kit **#46** (con của #50). **Repo WRITE: `agentcore-studio-kb`** · kit READ.
>
> Việc DE (#46): *"Demo **KB stub 5 doc + `kb.search` cited chunks** + **trace Postgres
> (`obs.trace_events`) timeline đọc lại khớp** + golden 5 case."* DoD #46 (6 ô) ở §5. Đề chi tiết
> `day-10.md`; ràng buộc `:47`: *"ngày gate — không build **mới**"*, `:48`: *"chỉ ra điểm skeleton sẽ
> gãy khi lên S2 **trước khi mentor hỏi**"*. Format mỗi vai (`:45`): **5' chạy thật · 5' quyết định
> khó · 5' Q&A**; demo là **một luồng chung** (`:44`) — mảnh DE là §3 của `kit:docs/demo-script-d10.md`.

---

## 0. "Không build mới" ≠ "không đụng src" — DE có WRITE kb hôm nay

Đọc `:47` cho đúng: cấm thêm **feature mới**, **không** cấm code. Ngược lại, câu trung tâm của gate
(`:28`) là *"1 luồng đi hết form→interpreter→KB→trace→smoke-eval — bằng **chạy thật**, không slide"* —
mà "chạy thật a→z" chính là thứ **có thể còn thiếu code để đạt**. Nên hôm nay DE **được và nên** sửa
`kb/src` khi: (a) làm luồng thật chạy trọn qua Postgres, (b) vá chỗ gãy lộ ra lúc chạy thử, (c) siết
một chỗ hở đã biết mà không phải feature mới. Issue #46 cấp **WRITE kb** đúng để làm việc đó.

Lằn ranh giữ nguyên (đúng thói quen): **không sửa test để pass**; nếu chạy thử lộ bug thì **sửa src,
không nới test**; **không đụng quadrant khác** (`apps/studio`, engine, workbench) — chỉ báo hoặc
coordinate.

---

## 1. Trạng thái chốt trước (trưa 31/07)

| Mục | Trạng thái |
|---|---|
| `gate-1/de-DongAnh2704.md` (evidence-pack DE) | ✅ trên report main (PR#34, `79ccef8`) |
| kb#8 (PR trùng) | ✅ đã đóng |
| `68 passed, 2 xfailed, 0 skipped` | ✅ tái lập tươi phiên này (Docker bật lại, Postgres healthy) |
| Con trỏ `docs/reports` ở kit (`kit#73`) | ⏳ leader bump chiều nay → cần `79ccef8` |
| Daily-note D10 | ⬜ chưa viết |
| `swe-Dozyboy.md` | ⬜ thiếu — pack chung 3/4 |

---

## 2. Việc DE thật sự còn — code trước, trình bày sau

### D10-1 · CODE ⭐ — làm luồng thật chạy **qua Postgres trong một lệnh** (DoD `:55` "không slide")
Đây là chỗ skeleton còn **hụt đúng nghĩa "1 luồng chạy thật"**, và là code task nặng nhất hôm nay.
Hiện `demo-script-d10.md` chạy **2 lệnh**: §1 thân luồng dùng `_NoopTraceWriter` (RAM, **không** chạm
Postgres), §3 mới là leg Postgres riêng. Tức trace-Postgres **không nằm trong** luồng chính — đúng cái
mentor sẽ chỉ ra là "slide trá hình".

**Phần DE làm được ngay (kb WRITE):** `PgTraceWriter` đã có trong kb. Bảo đảm nó là **drop-in thay
`_NoopTraceWriter`** — cùng interface `write(TraceEvent)`, chọn theo DSN có/không. Viết một entrypoint
kb (`scripts/spine_live_demo.py` hoặc mở rộng cái có sẵn) chạy **một lệnh** trọn chuỗi
resolver→interpreter→**fence**→**PgTraceWriter**→`read_run` đọc lại — không Noop. `test_spine_live.py`
đã chứng minh chuỗi này chạy được; việc hôm nay là **gói nó thành một lệnh demo**, không phải viết mới.

**Ranh giới:** phần composition ở `apps/studio/scripts/e2e_smoke_eval.py` (repo khác, DE không WRITE)
— nếu muốn hợp nhất tại đó thì **coordinate/PR**, không tự sửa. Tối thiểu: cấp sẵn đường-một-lệnh phía
kb + demo bằng nó.

**Nghiệm thu:** một lệnh, exit 0, in ra timeline 4 event đọc-lại-từ-Postgres đúng thứ tự `ts`, 0-gap.
Nếu không kịp hợp nhất: demo 2 lệnh (§1→§3) **và nói thẳng** đây là điểm S2 (đừng để mentor bắt).

### D10-2 · CODE reactive — vá chỗ gãy lộ ra khi chạy thử
Chạy thử toàn luồng trước gate; bất cứ chỗ nào trong `kb/src` gãy/hở → sửa src (không nới test). Ứng
viên đã biết còn trong tầm kb, cân nhắc siết nếu chạm phải (không bắt buộc, không phải feature):
- **#7** `StaticKbSearch` không ngưỡng → `[]` thực tế không xảy ra (hoãn có chủ đích D9; chỉ đụng nếu
  demo cần một ca trả rỗng thật).
- Không đụng #10 (contract carrier) — phải PR sang `packages/contracts`, để agenda freeze D11.

### D10-3 · Giữ hạ tầng sống cho leg trace (DoD `:57`)
Leg Postgres cần Docker + 2 dòng `export` DSN. **Đây đúng cái đã mất O3.2** — đừng để 09:00 gate mới
biết daemon tắt.
```bash
docker compose -f docker-compose.test.yml up -d --wait
export STUDIO_DATABASE_URL_ADMIN=postgresql://studio_owner:changeme@localhost:5433/studio_test
export STUDIO_DATABASE_URL=postgresql://studio_app:changeme@localhost:5433/studio_test
uv run pytest packages/kb -q      # phải 68 passed, 0 skipped — KHÔNG dùng make test-int (ra 36/34)
```

### D10-4 · Demo mảnh DE trong luồng chung + teach-back (`:45`, `:58`)
5' chạy thật mảnh DE (§3: fence 5 doc→25 chunk lọc **trước** ranking · trace Postgres đọc lại đúng
thứ tự · INV-1 tenant lệch → rỗng fail-closed), **trong** luồng chung không tách rời. Teach-back **bằng
lời mình**, trọng tâm **vì sao**:
- **Fence-tại-retrieval là LUẬT** vì "đừng tiết lộ" chỉ là chỉ dẫn mềm — dữ liệu sai tenant/vai đã vào
  context thì rò qua suy luận/citation/tool output, prompt injection thì bỏ qua chỉ dẫn. Loại **trước**
  khi đưa cho agent, fail-closed → vì thế lọc **trước** ranking, không lọc sau.
- **Eval-gate là LUẬT** — `FAIL` chặn Publish, có rollback về bản `PASS`; scorecard là **bằng chứng để
  hệ thống quyết định**, đọc từ **trace** (mặt quan sát thật) không tin agent tự khai.

Thủ sẵn câu chắc bị hỏi: *"case đỏ vì ai?"* → đọc cột quy-trách-nhiệm, không suy diễn.

### D10-5 · Điểm skeleton gãy S2 — nêu TRƯỚC khi mentor hỏi (`:48`, `:59`)
Theo **ledger chung** `#1`–`#14` (`daily-notes/2026-07-27-DongAnh2704.md`) — DE cầm **#7** (không
ngưỡng), **#10** (carrier `citations`); cái mới chưa số → ghi *"đề nghị bổ sung D11"*: **fence chỉ ở
tầng retrieval của KB stub** (S2 thêm đường lấy dữ liệu, mỗi đường một chỗ fence phải lặp) · **INV-1
mới chặn `tenant`, chưa chặn `roles`** (🟠, `session_context.roles` chưa đọc ở đâu — việc AIE-1/SWE) ·
**`ts` strictly-monotonic chưa chốt hợp đồng** (hai test đang giả định ngược nhau, cùng xanh do may,
min-gap 5µs). Nếu D10-1 không hợp nhất kịp: **§1 không qua Postgres** cũng là một điểm gãy phải tự nêu.

### D10-6 · Daily-note D10 — viết TRONG ngày, không backfill (DoD `:60`)
Mạch như note D9: bối cảnh gate → việc code hôm nay (D10-1/D10-2) đối chiếu PR/số thật → teach-back →
điểm gãy → DoD. Ghi **hôm nay** để 10/10 liền mạch — đúng kỷ luật ngược với 3 note backfill đã bị trừ.

### D10-7 · Chốt handoff `kit#73` với leader (không phải code, nhưng của DE)
DE không WRITE kit → nhắn leader bump `docs/reports` lên **`79ccef8`** (kéo section DE #34 + AIE-1 #32
+ sprint-report #33 một lượt). Sai SHA thì evidence-pack DE vô hình với mentor.

---

## 3. Phụ thuộc & câu hỏi chặn (đầu giờ)

| # | Cho ai | Câu hỏi | Vì sao chặn |
|---|---|---|---|
| **Q-A** | **cả nhóm / chủ `apps/studio`** | Hợp nhất §1+§3 thành một lệnh chạy qua Postgres (D10-1) — DE cấp đường kb, ai ráp ở composition? | `:55` "không slide"; trace-Postgres ngoài luồng chính là chỗ mentor sẽ bắt |
| **Q-B** | **leader** | Bump `docs/reports` ở kit = `79ccef8`? | Sai SHA → evidence-pack DE ẩn (O3.3) |
| **Q-C** | **SWE** | `swe-Dozyboy.md` kịp trước gate? pack chung mới 3/4 | `:31` "đủ để chấm không cần hỏi" |

---

## 4. Lịch

| Mốc | Việc | ⬜ |
|---|---|---|
| **09:00 — trước hết** | **D10-3** bật Docker + `pytest packages/kb` = 68 passed; giữ daemon sống tới gate | ⬜ |
| Đầu giờ | gửi Q-A/Q-B/Q-C · nhắn leader SHA `79ccef8` (D10-7) | ⬜ |
| Sáng | **D10-1 CODE** — gói luồng thật qua Postgres thành một lệnh (drop-in `PgTraceWriter`) | ⬜ |
| Sáng | **D10-2** chạy thử toàn luồng, vá chỗ gãy trong `kb/src` (không nới test) | ⬜ |
| Trưa | **D10-4** duyệt mảnh DE + soạn teach-back · **D10-5** rà điểm gãy S2 theo số | ⬜ |
| Gate | demo 5' mảnh DE trong luồng chung · teach-back · Q&A | ⬜ |
| Sau gate | xác nhận leader bump `kit#73`=`79ccef8` · **D10-6** daily-note D10 | ⬜ |

---

## 5. DoD #46 — phần DE

- [ ] **1 luồng chạy thật 4 quadrant (không slide)** — **D10-1 code**: luồng thật qua Postgres một
      lệnh; fallback 2 lệnh + tự khai là điểm S2.
- [ ] **INV-1 client-khai-tenant bị ignore** — `test_tenant_wall::..._tra_rong_fail_closed` + tách
      borea/ankor (M7/M8 0→1 đỏ). ✅ có, demo lại.
- [ ] **Trace timeline đọc lại đúng thứ tự** — `PgTraceReader.read_run` + 0-gap + payload lock. ✅ D9.
- [ ] **Teach-back fence & eval-gate là LUẬT** — D10-4, bằng lời mình.
- [ ] **Chỉ ra điểm skeleton gãy S2** — D10-5, theo ledger chung, trước khi bị hỏi.
- [ ] **Daily-notes 10/10** — D10-6, viết trong ngày.
- [x] Evidence-pack phần DE — `de-DongAnh2704.md` trên report main; chờ bump con trỏ (D10-7).

**Khối lượng:** code thật vẫn có (D10-1 gói luồng-thật-qua-Postgres + D10-2 reactive) — "không build
mới" không có nghĩa nhàn. Rủi ro lớn nhất: (1) daemon tắt lúc gate (đúng cái mất O3.2); (2) luồng
chính không qua Postgres → mentor gọi là slide; (3) leader bump nhầm SHA (O3.3 không đóng).
