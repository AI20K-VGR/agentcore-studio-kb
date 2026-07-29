# INV-1 Tenant-Wall — ai giữ mảnh nào, khớp ở đâu, hở ở đâu

> Giải thích dễ hiểu nhất về **INV-1**: danh tính tenant phải do **server quyết từ session**, không
> phải do client khai. Ba bút làm ba mảnh rời nhau trong ba repo, và câu hỏi thật là: **ba mảnh đó có
> ráp được vào nhau không?**
>
> Nguồn code (đọc thẳng, không bịa): `studio_workbench/tenant_wall.py` (SWE, `workbench@afa805d`) ·
> `studio_engine/session.py` + `interpreter.py` + `executors.py` (AIE-1, nhánh
> `engine@day8/session-context-tenant-wall`) · `studio_kb/schema.py` + `static_search.py` +
> `postgres.py` + `trace_reader.py` (DE) · `studio_app/middleware.py` (composition root).
>
> Ngày viết: 2026-07-29 (D8). Trạng thái nhánh ghi ở §6 — đọc lại nếu đã merge.

---

## 1. Ba mảnh, ba bút

INV-1 không phải một hàm. Nó là **một chuỗi**: có nơi *sinh ra* danh tính, có nơi *chuyền* nó đi, có
nơi *chặn bằng* nó. Thiếu một mắt là chuỗi đứt.

```
  ┌─ SINH ────────────┐   ┌─ CHUYỀN ──────────┐   ┌─ CHẶN ─────────────┐
  │  session → UUID   │──▶│  UUID đi qua DAG  │──▶│  lọc / RLS         │
  │                   │   │                   │   │                    │
  │  bút: SWE         │   │  bút: AIE-1       │   │  bút: DE           │
  │  workbench        │   │  engine           │   │  kb                │
  │  tenant_wall.py   │   │  session.py       │   │  schema.py         │
  │                   │   │  interpreter.py   │   │  static_search.py  │
  │                   │   │  executors.py     │   │  postgres.py       │
  └───────────────────┘   └───────────────────┘   └────────────────────┘
       resolve_session()      session_context           WHERE tenant_id
       → ResolvedContext      → node.params             + RLS FORCE
                              → TraceEvent
```

**Mảnh của DE (CHẶN) đã xong từ D4–D5**, D8 chỉ verify:

| Mảnh | Ở đâu |
|---|---|
| `kb.chunks.tenant_id UUID NOT NULL` | `schema.py:40` |
| RLS fail-closed (`ENABLE`+`FORCE`+policy `app.tenant_id`) | `schema.py:52-58` |
| `StaticKbSearch` lọc tenant (so `==` UUID resolved) | `static_search.py:63,92` |
| `PgKbSearch` `WHERE tenant_id` + `_bind_tenant` (`set_config`) | `postgres.py:68-70,88-101` |
| Trace reader lọc tenant | `trace_reader.py:67-70` |

---

## 2. Luồng thật hôm nay — `run()` một recipe

Đây là đường dữ liệu **thật sự chạy** (smoke-eval, spine test). Chú ý: nó **không đi qua workbench**.

```
   ┌────────────────────────────────────────────────────────────┐
   │  RECIPE  (client soạn — recipe.tenant_id là CLIENT KHAI)   │
   └────────────────────────────┬───────────────────────────────┘
                                │
        SESSION (server resolve)│
        ┌───────────────────────┴────────────┐
        │  session_context.tenant_id : UUID  │  ◀── bắt buộc, keyword-only,
        └───────────────────────┬────────────┘      KHÔNG default
                                │                   (interpreter.py:113)
                                ▼
   ① engine — interpreter.run()                          [AIE-1]
   ┌────────────────────────────────────────────────────────────┐
   │  node.params = {**node.params, "tenant_id": session_ctx}   │ :241
   │            ▲ đặt SAU spread → client khai bị GHI ĐÈ        │
   │                                                            │
   │  TraceEvent(tenant_id = session_ctx.tenant_id)             │ :293
   │            ▲ trace và search cùng một nguồn                │
   │                                                            │
   │  recipe.tenant_id  ─────▶  KHÔNG ĐỌC Ở ĐÂU                 │
   └────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
   ② engine — KbRetrieveExecutor                          [AIE-1]
   ┌────────────────────────────────────────────────────────────┐
   │  if not isinstance(raw_tenant_id, UUID):                   │
   │      raise PermissionError(...)                            │ :145
   │      ▲ defense-in-depth: ai gọi executor thẳng, bỏ qua     │
   │        fence session, thì NỔ — không trả 0 dòng lặng lẽ    │
   └────────────────────────────┬───────────────────────────────┘
                                │  search(query, tenant_id: UUID, ...)
                                ▼
   ③ kb — StaticKbSearch / PgKbSearch                        [DE]
   ┌────────────────────────────────────────────────────────────┐
   │  chunk.tenant_id != tenant_id  → loại       static:92      │
   │  WHERE tenant_id = %s  +  RLS FORCE         postgres/schema│
   │      ▲ hai lớp: mệnh đề WHERE và policy DB                 │
   └────────────────────────────────────────────────────────────┘
```

**Vì sao AIE-1 bỏ nil-UUID sentinel.** Bản cũ: thiếu `tenant_id` → fallback `UUID(int=0)` → truy vấn
trả 0 dòng. Nghe thì fail-closed, nhưng nó **fail-closed do may**, không do hợp đồng: một bug wiring
phía trên đọc **y hệt** "tenant này không có chunk nào". Bản D8 raise thay vì đoán — sai wiring thì
biết ngay.

---

## 3. Seam của SWE nằm ở đâu — và vì sao nó KHÔNG ở trên hình trên

Đây là chỗ dễ đọc lệch nhất. `tenant_wall.py` là seam ở **workbench API boundary**, còn hình §2 là
đường **engine → kb**. Hai seam khác nhau, docstring `tenant_wall.py` tự phân biệt.

```
        client
          │
          ├──────────────▶ workbench API      ──▶  tenant_wall.resolve_session()   [SWE]
          │                (dựng/publish recipe)    → ResolvedContext
          │
          └──────────────▶ studio app /run    ──▶  interpreter.run(session_context) [AIE-1]
                           (chạy agent)             → kb.search                      [DE]
```

Nên câu hỏi cũ *"middleware của SWE bơm UUID xuống `kb.search` qua đường nào?"* là **hỏi sai seam** —
nó không bơm xuống đường đó. Đường đó là `session_context` của AIE-1.

---

## 4. Chỗ đã khớp — có kiểm, không tin lời

AIE-1 **cố ý không import** `ResolvedContext` của SWE: `.importlinter` cấm `studio_engine` import
`studio_workbench` (hai quadrant anh em). Thay vào đó khai một `typing.Protocol` riêng
(`session.py:49`), và dựa vào **structural typing** để hai bên ráp mà không chạm nhau.

```
   studio_workbench                       studio_engine
   ┌──────────────────────┐               ┌──────────────────────┐
   │ ResolvedContext      │               │ SessionContext       │
   │ @dataclass           │               │ (Protocol)           │
   │   frozen=True        │  ── thoả ──▶  │   tenant_id : UUID   │
   │   slots=True         │   structural  │   user      : str    │
   │                      │    typing     │   roles     : list   │
   │  tenant_id : UUID    │               │  (read-only props)   │
   │  user      : str     │               └──────────────────────┘
   │  roles     : list    │                          ▲
   └──────────────────────┘                          │
              │                                      │
              └──────── apps/studio ─────────────────┘
                    (lớp DUY NHẤT được import cả hai)
```

Kiểm thật, không suy luận:

```
runtime  isinstance(resolve_session({...}), SessionContext)  →  True
static   mypy --strict                                       →  Success: no issues found
```

Ba điểm khớp:

1. **Type.** `resolve_tenant() -> UUID` ↔ `SessionContext.tenant_id: UUID` ↔ `search(..., tenant_id:
   UUID, ...)` / `read_run(run_id, tenant_id: UUID)`. Cùng `UUID` suốt chuỗi (D-13 / DEC-B).
2. **Hình dạng.** `ResolvedContext` thoả `SessionContext` **không cần adapter**. Không bên nào phải sửa.
3. **Triết lý fail-closed.** Cả hai raise `PermissionError` — cùng loại exception, thiếu là nổ, không
   có giá trị mặc định nào. DE thì fail-closed ở tầng DB (`tenant_id = NULL` không bao giờ true).

---

## 5. Chỗ chưa khớp

### 5.1 Khoảng trống thật: composition root chưa nối

Grep toàn kit: **không call site nào** gọi `resolve_session()` rồi truyền vào `run()`. SWE cấp đầu
sinh, AIE-1 cấp đầu nhận, **giữa hai đầu chưa có dây**.

```
   resolve_session()  ●- - - - - - - -?- - - - - - - -●  run(session_context=...)
        [SWE ✅]           chưa ai viết                    [AIE-1 ✅]
                       (lane: apps/studio)
```

Dây này phải nằm ở `apps/studio` — lớp duy nhất được import cả hai quadrant. **Chưa giao trong
`day-08.md`**, và `:45` chốt *"hôm nay chỉ cần đúng pattern"*, nên đây là **nợ có chủ, không phải lỗi
D8**.

Hình dạng của dây đó thì đã thấy trước được: `engine/__main__.py` (CLI demo) dựng
`_DemoSessionContext` — một `@dataclass(frozen=True, slots=True)` mang `tenant_id/user/roles` — rồi
truyền thẳng làm kwarg. Composition root thật chỉ khác ở chỗ **nguồn**: thay vì hằng số demo thì gọi
`tenant_wall.resolve_session(session)` của SWE. Docstring của AIE-1 nói rõ vì sao dựng tại chỗ chứ
không đọc từ recipe: *"session identity must never come from the recipe"*.

### 5.2 `apps/studio` đang có một resolver thứ hai, contract lệch

| | `middleware.py::_resolve_tenant_id` | `tenant_wall.py::resolve_tenant` |
|---|---|---|
| input | `(request, conn)` — header `x-tenant-id` | `Mapping` session |
| output | `str \| None` | `UUID` |
| fail-closed kiểu | trả `None` → *không* set `app.tenant_id` | `raise PermissionError` |
| slug→UUID | có (query `core.tenants`) | **không** |

Chưa va nhau vì chưa nối. Nhưng ai làm dây ở §5.1 phải chốt một trong hai, không để song song.

### 5.3 Slug→UUID: không bên nào trong chuỗi làm

SWE raise nếu session mang slug; AIE-1 raise nếu params không phải `UUID`; DE chỉ nhận `UUID`. Chuỗi
đúng và chặt, nhưng **ai đó ở trên phải resolve slug→UUID trước** — hiện chỉ
`middleware._resolve_tenant_id` biết làm, mà nó không nối vào đâu. Đây là **Q-G từ D5 quay lại**, chưa
có lời giải.

### 5.4 Call site cũ vỡ vì `run()` đổi chữ ký

`session_context` bắt buộc, không default (cố ý — *"no call site can silently skip the fence"*).

```
6 failed  ── workbench: test_builder, test_wiring_d3/d4/d6×2/d7      [lane SWE]
TypeError: run() missing 1 required keyword-only argument: 'session_context'

2 chưa nổ nhưng sẽ nổ:
  kb/tests/test_spine_live.py:86   ── đang SKIP vì thiếu Postgres    [lane DE]
  scripts/smoke_eval_d6.py:173     ── script smoke-eval ở kit
```

---

## 6. Có cần sửa không — phân tầng

| Việc | Lane | Cần? |
|---|---|---|
| `tenant_wall.py` (SWE), `session.py` (AIE-1) | SWE / AIE-1 | ❌ **không đụng gì** — đã khớp, kiểm rồi (§4) |
| 6 test wiring workbench: thêm `session_context=` | SWE | ✅ **có, CI đang đỏ** |
| `builder.py:165` nhét `tenant_id` vào `node.params` | SWE | ❌ không bắt buộc — giờ bị `:241` ghi đè, tức đã bị vô hiệu **đúng cách**. Bỏ hay giữ đều được; giữ thì nên comment là "không còn là nguồn tenant" |
| `kb/tests/test_spine_live.py:86` | DE | ⏳ trước khi bật Postgres |
| `scripts/smoke_eval_d6.py:173` | kit | ⏳ trước smoke-eval D8 (DoD `:39` của AIE-2) |
| Dây composition root ở `apps/studio` | apps/studio | ⏳ **không phải việc D8** — `:45` chỉ đòi đúng pattern |
| Hợp nhất 2 resolver (§5.2), slug→UUID (§5.3) | apps/studio | ⏳ nợ có chủ, ghi để không quên |

**Một câu:** ba mảnh **ráp đúng về kiểu và triết lý, chưa ráp về đường dây**. Cái phải sửa hôm nay chỉ
là mấy call site vỡ do đổi chữ ký — không mảnh nào phải thiết kế lại.

---

## 7. Gợi ý cho SWE (nếu hỏi tới) — hai cách, cách 2 đáng hơn

AIE-1 đã lập sẵn pattern trong lane của họ: một helper chung `default_session_context()`
(`tests/test_session_context_tenant_wall.py:56`) trả `_FrozenSessionContext`, được 7 file test engine
import lại *"so `run()`'s new mandatory `session_context` doesn't get 7 copy-pasted definitions"*.

**Cách 1 — bắt chước engine:** khai một frozen dataclass double trong `conftest`/helper của workbench.
Ít ma sát nhất, giống hệt lane engine.

**Cách 2 — dùng chính `resolve_session()` của mình:**

```python
result = await run(
    recipe,
    session_context=resolve_session({"tenant_id": ANKOR_ID, "user": "..."}),
    kb_search=EmptyKbSearch(),
    ...
)
```

Engine **phải** dùng double vì `.importlinter` cấm nó import workbench. **SWE thì không bị cấm gì** —
`resolve_session()` nằm ngay trong package của họ. Nên cách 2 vừa không tốn thêm code, vừa biến 6 test
wiring **thành bằng chứng seam thật**: SWE cấp `ResolvedContext` → engine nhận qua `SessionContext` →
không bên nào import bên nào. Đúng `day-08.md:42` (*"SWE giữ bút middleware; cả team consume"*), và nó
kiểm đúng thứ mà double không kiểm được — rằng `ResolvedContext` **thật** ráp vừa.
