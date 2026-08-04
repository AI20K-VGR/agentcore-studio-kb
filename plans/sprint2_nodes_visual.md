# 6 node hoạt động thế nào — minh hoạ bằng hình

> Đọc kèm `sprint2_overview.md`. Sơ đồ dưới viết bằng **Mermaid** → GitHub tự vẽ ra hình.
> Ví dụ xuyên suốt: nhân viên **Ankor** hỏi *"Mức chi tối đa?"* (Ankor = 20 triệu · Borea = 77 triệu).
> Nguồn: `studio_contracts/nodes.py`, `recipe.py`, `studio_engine/interpreter.py`, `studio_kb/trace_reader.py`.

---

## 1. Ai làm gì với node? (SWE định nghĩa → AIE-1 chạy → DE nuôi & ghi)

```mermaid
flowchart LR
    subgraph SWE["🎨 SWE — ĐỊNH NGHĨA"]
      P["Palette 6 node<br/>nối edges → DAG<br/>graph-lint kiểm"]
    end
    subgraph AIE1["⚙️ AIE-1 — CHẠY"]
      E["6 executor<br/>lái tàu qua từng node"]
    end
    subgraph DE["📚 DE — NUÔI & GHI"]
      K["kb.search<br/>nuôi node kb-retrieve"]
      T["trace + cost<br/>ghi lại mọi node"]
    end
    P -->|"recipe (công thức)"| E
    E -->|"tới kb-retrieve thì gọi"| K
    E -->|"emit 1 dòng / node"| T
```

**Ví như bản đồ tàu điện:** SWE **vẽ bản đồ** (ga nào, ray nối ra sao). AIE-1 **lái tàu**. DE **bán vé cho ga kb-retrieve** và **ghi hành trình** (camera).

---

## 2. Sáu loại node — 4 cái đã bật, 2 cái chưa

```mermaid
flowchart TD
    subgraph ON["✅ ĐÃ CHẠY (Sprint 2 dùng được)"]
      direction LR
      A["kb-retrieve<br/>📚 tra kho KB"]
      B["llm-step<br/>🤖 AI viết trả lời"]
      C["tool-call<br/>🧰 gọi công cụ (whitelist)"]
      D["end<br/>🏁 kết thúc"]
    end
    subgraph OFF["⛔ CHƯA BẬT (stub — gặp là raise)"]
      direction LR
      E["condition<br/>🔀 rẽ nhánh theo when"]
      F["hitl-pause<br/>✋ dừng chờ người duyệt"]
    end
```

> `condition` và `hitl-pause` còn là **stub** — động cơ gặp là **dừng, ném lỗi**. AIE-1 bật đủ 6 vào D14 (#96).

---

## 3. Một luồng chạy thật (walk) — recipe của trợ lý Ankor

```mermaid
flowchart LR
    START(("bắt đầu")) --> n1
    n1["n1 · kb-retrieve"] --> n2["n2 · llm-step"]
    n2 --> n3["n3 · tool-call"]
    n3 --> n4["n4 · end 🏁"]
    n1 -. "cấp đoạn: 20 triệu<br/>trích ankor-expense-001 c2" .-> n2
```

Động cơ đi theo **mũi tên** từ node-bắt-đầu (không mũi tên trỏ vào) tới `end`: **n1 → n2 → n3 → n4**.
**Mỗi node chạy = 1 dòng trace** (camera DE ghi).

---

## 4. Một câu hỏi đi qua 4 vai

```mermaid
sequenceDiagram
    autonumber
    participant U as 👤 NV Ankor
    participant SWE as 🎨 Playground (SWE)
    participant ENG as ⚙️ Động cơ (AIE-1)
    participant KB as 📚 Kho+Fence (DE)
    participant TR as 🎥 Trace+Cost (DE)
    participant EV as 🧑‍⚖️ Giám khảo (AIE-2)
    U->>SWE: "Mức chi tối đa?"
    SWE->>ENG: chạy recipe (tenant = Ankor)
    ENG->>KB: kb.search("mức chi", Ankor)
    Note over KB: chỉ lục ngăn Ankor<br/>KHÔNG đụng Borea (fence)
    KB-->>ENG: "20 triệu" + trích nguồn
    ENG->>TR: emit trace từng node + token
    ENG-->>SWE: câu trả lời có dẫn chứng
    SWE->>TR: đọc timeline + cost (1 số)
    EV->>TR: đọc kết quả để chấm
    EV-->>U: ✅ ĐẠT / ❌ RỚT
```

**DE xuất hiện 2 lần (KB, Trace) + cấp bộ đề cho AIE-2 chấm.**

---

## 5. Thiếu node thì gãy ở đâu? (3 kiểu)

### a) Thiếu `kb-retrieve` → AI trả lời chay, mất trích dẫn
```mermaid
flowchart LR
    n2["llm-step"] --> n4["end"]
    X["❌ không có kb-retrieve"] -. "chunks = []" .-> n2
    n2 --> R["🤖 trả lời chay<br/>KHÔNG trích nguồn"]
    R --> V["🧑‍⚖️ AIE-2: RỚT citation"]
```

### b) Nối edges sai / thiếu `end` → động cơ NÉM LỖI, không chạy
```mermaid
flowchart LR
    a["a"] --> b["b"]
    b --> a
    L["💥 ValueError<br/>0 node bắt đầu<br/>(cả đồ thị là vòng lặp)"]
```
> Các lỗi tương tự: **>1 node bắt đầu** (không biết bắt đầu đâu) · **thòng lọng a→b→b** (thăm lại node cũ) · edge trỏ tới node không tồn tại. → recipe **không được interpret**.

### c) Dùng node CHƯA bật (`condition`/`hitl-pause`)
```mermaid
flowchart LR
    n1["kb-retrieve"] --> c["condition 🔀"]
    c --> STOP["💥 raise — dừng luôn<br/>(executor còn là stub)"]
```

### d) (Của DE) Node chạy nhưng trace bị SÓT
```mermaid
flowchart LR
    subgraph THUC["thực tế chạy 4 node"]
      k1["kb-retrieve"] --> l1["llm-step"] --> t1["tool-call"] --> e1["end"]
    end
    subgraph GHI["camera ghi được 3 (sót llm-step)"]
      k2["kb-retrieve"] --> t2["tool-call"] --> e2["end"]
    end
    THUC -. "so bằng walk_from_dag()" .-> ALARM["🚨 DE reader báo:<br/>THIẾU NODE (0-gap fail)"]
```
> Nguy hiểm vì timeline **trông** liền mạch — mất bằng chứng mà không ai biết. DE suy chuỗi kỳ vọng **từ chính recipe.dag** rồi đối chiếu.

---

## 6. Ba "sợi dây" node của SWE tác động DE & AIE-1

```mermaid
flowchart TD
    SWE["🎨 SWE — recipe"]
    SWE -->|"① node_type<br/>phải TRÙNG enum<br/>studio_contracts.nodes"| DET["📚 DE — trace"]
    SWE -->|"② edges = đường walk<br/>động cơ phải đi"| ENG["⚙️ AIE-1 — động cơ"]
    SWE -->|"③ kb_binding.scope<br/>= tra NGĂN nào"| DEK["📚 DE — kb.search"]

    ENG -->|"phát tokens"| DEC["📚 DE — cost"]
    DEK -->|"đoạn + citations"| ENG
```

| Dây | SWE đặt gì | Ảnh hưởng | Nếu sai |
|---|---|---|---|
| **①** | tên `node_type` | DE ghi trace theo enum này | SWE `kb_retrieve` ≠ DE `kb-retrieve` → camera lệch, báo sai |
| **②** | edges (nối node) | AIE-1 đi theo đúng đường | vòng lặp/hở đích → động cơ ném lỗi |
| **③** | `kb_binding.scope` | DE lục ngăn tương ứng | ghi nhầm `borea` → DE trả 77 triệu cho NV Ankor = **rò!** |

---

## 7. Vì sao fence của DE KHÔNG tin `scope` mù quáng

```mermaid
flowchart LR
    Q["👤 NV Ankor hỏi<br/>(phiên: tenant=Ankor)"] --> F{"🚧 Fence DE<br/>kẹp tenant THẬT<br/>của phiên"}
    F -->|"ngăn Ankor ✅"| G["📗 20 triệu"]
    F -. "ngăn Borea 🔒" .-> H["📕 77 triệu"]
    G --> OK["trả lời đúng"]
    H -. "CHẶN — kể cả recipe<br/>ghi scope=borea" .-> OK
```

> **Bài học:** dù SWE lỡ cấu hình `scope` sai, hay client tự khai gian nhãn (T6), fence của DE vẫn kẹp theo **tenant thật của phiên do server quyết** → fail-closed, không rò. Đó là lý do D17 (#110) là ngày DE "áp mandatory filter tại retrieval".

---

## Tóm một hình
**SWE vẽ bản đồ (node + edges) → AIE-1 lái tàu qua từng node → DE bán vé cho ga `kb-retrieve` và quay camera mọi ga.** Thiếu ga hoặc vẽ sai ray: hoặc tàu không chạy (ValueError), hoặc chạy mà mất dẫn chứng / rò dữ liệu — và bảng điểm AIE-2 lãnh đủ.
