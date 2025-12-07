# AMDlingo — API Worker Agent Specification v1.0

API Worker Agent 是 AMDlingo 中負責 **HIP / ROCm / MI300X 相關 API 查詢、語意補全、使用示例生成、常見錯誤解釋** 的專職代理。

它不像 Document Worker 需要解析整份文件，也不像 Code Worker 要理解整段程式碼，而是：

> **將單一 API 名稱 → 轉換為完整的語意說明、使用方式、限制、範例與常見錯誤。**

此 Agent 的目標：
- 取代開發者搜尋文件、比對多頁內容的痛點
- 以工程師能立即使用的方式回覆 API 資訊
- 避免 hallucination（必須依據 Metadata DB）

---

# 1. 角色定位（Role Definition）

API Worker Agent 是 AMDlingo 的「技術 API 解答器」。
其任務為：
- 查詢單一 API 的定義、參數、語義（以 Metadata DB 為基礎）
- 補充工程語意（為何使用？何時使用？）
- 產生正確且可執行的使用示例
- 指出該 API 常見誤用（pitfalls）
- 與相關 API 互相比較（hipMalloc vs hipHostMalloc）

它類似於：
- CUDA / HIP API Copilot
- LLM 版本的 man page + engineering insights

---

# 2. 功能範圍（Scope）
API Worker Agent 必須完成：

### ✔ 1. API Metadata 查詢（deterministic）
從 DB 擷取：
- API 功能描述
- 參數列表
- 回傳值
- 錯誤碼

### ✔ 2. 語意補全（semantic completion）
將 DB 的機械式資料轉換成：
- 如何正確使用
- 此 API 適用於哪種 GPU 記憶體模型
- 和其他 API 的差異

### ✔ 3. 自動產生 code 示例
Worker Agent 必須能：
- 正確產生 HIP 程式碼示例
- 若為 memory API → 加入 pointer 分配
- 若為 stream API → 加入同步示例

### ✔ 4. 常見錯誤提示（Pitfalls）
例如：
- hipMemcpy：direction mismatch
- hipMalloc：未檢查 hipSuccess
- hipEventRecord：未同步造成 race condition

### ✔ 5. API 家族關聯圖（可選）
例如：
hipMemcpyAsync → 與 hipMemcpy 的差異
hipEventSynchronize → 與 hipDeviceSynchronize 的差異

### ✔ 6. 統一 JSON schema
供 Web Plugin 與 VSCode 插件顯示。

---

# 3. Input（來自 Master Agent）
API Worker Agent 僅處理單一 API 名稱或短查詢。
Master Agent 先確認：輸入真的像 API query（短、結構單一）。

格式如下：
```json
{
  "mode": "api",
  "preprocessed": {
    "api_name": "hipMemcpy",
    "metadata": {
       "description": "Copies data between host and device.",
       "parameters": [...],
       "return": "hipError_t",
       "category": "HIP Runtime API"
    }
  },
  "raw_input": "hipMemcpy 是什麼",
  "session_id": "api-447"
}
```

---

# 4. Output（JSON schema）

```json
{
  "api_name": "hipMemcpy",
  "description": "...工程語意描述...",
  "parameters": [...],
  "return": "hipError_t",
  "usage": "...如何正確使用此 API...",
  "example_code": "...HIP 程式碼示例...",
  "pitfalls": ["指標方向錯誤", "未同步 stream 導致資料競爭"],
  "related_apis": ["hipMemcpyAsync", "hipMemset"],
  "notes": "...補充...",
  "context_sync_key": "api-447"
}
```

---

# 5. Tools 使用（Sub-tools）
API Worker Agent 使用：

### ✔ API Metadata DB（最重要）
這是此 Agent 的唯一 deterministic 資料來源。
它包含：
- API 名稱
- 功能描述（非 AI）
- 參數
- 回傳值
- 所屬類別（Memory / Stream / Event / Device / Math）
- 錯誤碼

### ✔ LLM Semantic Enricher
用於：
- 將 metadata 轉換成可理解的描述
- 產生使用示例
- 產生工程向提示與警告

API Worker Agent 不能：
- 發明不存在的 API
- 推斷 ROCm 未支援的功能

---

# 6. 系統 Prompt（System Message）
```
You are AMDlingo's API Worker Agent.
Your job is to:
- Retrieve API metadata (from the provided DB),
- Explain the API clearly and accurately,
- Provide usage guidance and examples,
- Highlight common mistakes and constraints,
- Connect this API with related APIs.

Rules:
- Never invent APIs that do not exist.
- Always rely on the given metadata for deterministic details.
- Examples must compile logically.
- Provide HIP-specific engineering insights.

Always output in the required JSON format.
```

---

# 7. 模式驗證 Prompt（Mode Check）
```
Verify whether mode="api" is correct.
If incorrect:
{ "mode_ok": false, "suggest_mode": "code | error | hipify | document" }
Else:
{ "mode_ok": true }
```

Master Agent 會在必要時 reroute。

---

# 8. Reasoning Workflow

```
Master API-name preprocessing
        ↓
Mode check
        ↓
Load metadata from API DB
        ↓
Semantic explanation of API purpose
        ↓
Generate usage examples
        ↓
Identify common mistakes
        ↓
Suggest related APIs
        ↓
Output JSON
```

---

# 9. Pseudo-code（可直接交給後端）

```python
def api_worker_agent(payload):

    mode_ok, suggest = llm_check_mode(payload)
    if not mode_ok:
        return reroute(suggest)

    metadata = payload.preprocessed["metadata"]
    api_name = payload.preprocessed["api_name"]

    reasoning = llm_generate({
        "api_name": api_name,
        "metadata": metadata
    })

    return {
      "api_name": api_name,
      "description": reasoning.description,
      "parameters": metadata.get("parameters", []),
      "return": metadata.get("return", ""),
      "usage": reasoning.usage,
      "example_code": reasoning.example_code,
      "pitfalls": reasoning.pitfalls,
      "related_apis": reasoning.related_apis,
      "notes": reasoning.notes,
      "context_sync_key": payload.session_id
    }
```

---

# 10. 相關技術文件下載來源
API Worker Agent 必須基於 metadata，因此資料來源至關重要。

## ✔ HIP API 官方文件
https://rocm.docs.amd.com/projects/HIP/en/latest/api/index.html

核心 API：
- 記憶體操作（hipMalloc / hipMemcpy / hipFree）
- kernel launch（hipLaunchKernelGGL）
- stream / event APIs
- device APIs

## ✔ ROCm Library APIs
- rocBLAS： https://rocm.docs.amd.com/projects/rocBLAS/en/latest/
- rocFFT： https://rocm.docs.amd.com/projects/rocFFT/en/latest/
- MIOpen： https://rocm.docs.amd.com/projects/MIOpen/en/latest/
- rocPRIM： https://rocm.docs.amd.com/projects/rocPRIM/en/latest/

## ✔ CUDA API（僅用於比較，不直接參照）
https://docs.nvidia.com/cuda/cuda-runtime-api

---

# 11. Summary（給簡報用）
API Worker Agent 是 AMDlingo 的「快速 API 咨詢助手」，具備：
- 即時 API 查詢能力
- 以 metadata 為基礎的 deterministic 回答
- 自動生成 HIP 程式碼示例
- 工程級的使用解說 + 常見錯誤提示
- 能協助開發者快速理解並運用 AMD API

它讓整個 AMDlingo 系統完整覆蓋了：
文件導讀 → 程式碼分析 → Debug → 移植 HIPify → **API 即時查詢**（最後一塊拼圖）

---

此 Spec v1.0 可用於：
- 多代理架構建置
- API DB schema 設計
- Hackathon Demo：快速查詢 hipMemcpy / hipMalloc 等 API
- VSCode 插件 hover / 搜尋整合

