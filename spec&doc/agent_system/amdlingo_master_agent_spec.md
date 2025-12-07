# AMDlingo — Master Agent Specification v1.0

Master Agent 是 AMDlingo 的核心協調者（Coordinator），負責 **路由判斷、非 AI 前處理、payload 構建**，並保證所有任務在進入 Worker Agent（LLM）前是乾淨、有結構、可預測的。

Master Agent 不進行 reasoning，不生成內容，而是整個多代理系統的「流量控制器」。

---

# 1. Master Agent 角色定位（Role Definition）

Master Agent 三大任務：

## **1) Routing（模式判斷）**
決定使用者輸入屬於五大處理模式中的哪一個：
- `document` — 技術文件導讀
- `code` — 程式碼分析
- `error` — 錯誤 Debug
- `hipify` — CUDA → HIP 移植
- `api` — API 查詢

Routing 必須：
- 高正確率
- 不依賴 LLM
- 可 Debug
- 可向使用者覆蓋（override）

## **2) Non-AI Preprocessing（前處理）**
Master Agent 需完成 Worker Agent 無法高效執行的 deterministic 工作：

- 程式碼 normalize / language detect
- API name extract
- error log rule-based detection
- static HIPify（mapping）
- kernel pattern 檢查（boundary / indexing）
- 文件 metadata 提取（URL, H1/H2/H3）

## **3) Payload Construction（構建 Worker Agent 輸入）**
完成以下內容：
- 選定模式（最終路由）
- 完整整理後的 preprocessed payload
- 原始輸入（raw input）
- session_id（同步上下文）

並交給 Worker Agent 進行 AI reasoning。

---

# 2. Routing 設計（Route Classification Architecture）

Routing 分為四個階段：

```
前端模式（最高優先）
   ↓
Rule-based Routing（快速且準確）
   ↓
Parallel Routing Scoring（多路並行）
   ↓
Worker Agent Double-check（最後保護）
```

---

# 2.1 前端模式（Frontend Explicit Mode）

若使用者透過按鈕選擇模式（例如按 HIPify）：

```json
{
  "explicit_mode": "hipify"
}
```

則 Master Agent **直接採用，不再推翻**。

---

# 2.2 Rule-based Routing（基礎判斷）

使用 deterministic 規則分類輸入內容。

### Document Mode
- 有 URL
- 出現在 Web Plugin
- 有技術段落（API, header）

### Code Mode
- 包含 `__global__`、`hipLaunchKernelGGL`
- 包含 `{}`, `;` 且呈現 code structure

### Error Mode
- 包含 `hipError`、`illegal memory access`
- 有 stack trace patterns

### HIPify Mode
- 出現 `cudaMalloc`、`cudaMemcpy`
- 沒有 hip 相關 API

### API Mode
- 單一詞且符合 HIP API DB key
- 文本短於 30 字元

---

# 2.3 Parallel Routing Scoring（多路並行比對）

前端會送出：
```json
{
  "parallel_modes": ["document", "code", "error", "hipify", "api"]
}
```

Master Agent 會對每個候選模式跑「輕量 scoring function」。

## Scoring 範例：

### document scoring
- URL 存在：+20
- H1/H2 結構：+15
- 出現 HIP API：+10

### code scoring
- 有 `{}`, `;`：+15
- 有 kernel pattern：+20
- code line > 3：+10

### error scoring
- 有 `error`, `illegal`：+40
- 有 stack trace：+20

### hipify scoring
- 出現 cuda API：+50

### api scoring
- 單字 + 在 API DB：+40

最終：
```
best_mode = argmax(score)
```

---

# 2.4 Worker Agent Double-check（LLM 驗證）

Worker Agent 在正式執行任務前，需要確認：

```
assigned_mode 是否合理？
```

## Worker Agent prompt snippet：

```
Before solving the task, verify if the assigned mode is correct.
Respond only in JSON:
{
  "mode_ok": true | false,
  "suggest_mode": "document | code | error | hipify | api"
}
```

若 `mode_ok=false` → Master Agent 自動 reroute。

---

# 3. Non-AI Preprocessing（依 route 分類）

Master Agent 會根據最終模式執行不同 preprocessing。

---

# Document Mode Preprocessing
- URL metadata extract
- H1/H2/H3 structure parsing
- extract API names
- classify document category (runtime / library / MI300X)
- clean irrelevant elements（footer, ads, boilerplate）

---

# Code Mode Preprocessing
- language detection（CUDA/HIP/C++/Python）
- static API misuse detection（如 memcpy 方向錯誤）
- indexing pattern detection
- boundary check detection
- code normalization（format）

---

# Error Mode Preprocessing
- rule-based error classifier（hipErrorInvalidValue...）
- extract stack trace
- extract related API
- map error type → known cause DB

---

# HIPify Mode Preprocessing
- run static mapping-based HIPify
- detect unmapped CUDA features
- detect kernel launch syntax
- build diff blocks

---

# API Mode Preprocessing
- lookup API metadata DB
- fetch signature / category / examples

---

# 4. Payload Construction（Master → Worker Agent）

Master Agent 回傳統一格式：

```json
{
  "mode": "code",
  "preprocessed": {
     "language": "hip",
     "api_list": ["hipMemcpy", "hipMalloc"],
     "issues_found": ["hipMemcpy direction mismatch"],
     "normalized_code": "..."
  },
  "raw_input": "...",
  "session_id": "abc123"
}
```

這是 Worker Agent 能穩定推理的最小上下文。

---

# 5. Master Agent Pseudo-code（可交給後端）

```python
def master_agent(request):

    text = request.text

    # 1. 前端明確模式 override
    if request.explicit_mode:
        mode = request.explicit_mode
    else:
        mode = rule_based_detect(text)

    # 2. Parallel Scoring
    scores = {}
    for candidate in request.parallel_modes:
        scores[candidate] = compute_score(candidate, text)

    best_candidate = max(scores, key=scores.get)
    mode = best_candidate

    # 3. Non-AI Preprocessing
    preprocessed = preprocess(mode, text, request)

    # 4. 組 payload（交給 Worker Agent）
    return {
        "mode": mode,
        "preprocessed": preprocessed,
        "raw_input": text,
        "session_id": request.session_id
    }
```

---

# 6. Master Agent Summary（重點）

- **不進行 reasoning**
- **不與 Worker Agent 重複工作**
- **確保 routing 100% 正確**
- **確保 LLM 負擔最小化（非 AI 工具先處理）**
- 讓 Worker Agent 接收到的是「乾淨、有意圖、有結構」的上下文

> Master Agent = Router × Validator × Preprocessor × Context Builder

---

此 Spec v1.0 已可直接用於：
- ADK graph 設計
- 後端實作
- 工程任務拆解
- Hackathon Pitch / 簡報架構圖用途

