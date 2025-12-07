# AMDlingo — Error Worker Agent Specification v1.0

Error Worker Agent 是 AMDlingo 在 **GPU Runtime Error、HIP API Error、PyTorch ROCm Error、Memory/Kernel 相關錯誤追蹤** 的核心代理。

它的任務是將錯誤訊息轉換成：
- 錯誤類型（classification）
- 具體成因（root cause analysis）
- 修復方案（fix steps）
- 修正版程式碼（auto patch）
- 預防方式（prevention guidance）

此 Agent 是技術含量最高、Demo 成效最強的 Worker Agent，因為 GPU runtime errors 是 AMD 開發者最痛的地方。

---

# 1. 角色定位（Role Definition）
Error Worker Agent 的核心任務是：
> **理解並解析 HIP / ROCm / GPU runtime 錯誤，找出真正的原因，並給出工程級修復方案。**

此 Agent 不只是「解釋錯誤訊息」，而是：
- 錯誤分類器（error classifier）
- 成因推理器（root cause tracer）
- 修復建議器（repair recommender）
- 風險預測器（risk predictor）

---

# 2. 功能範圍（Scope）
Error Worker Agent 負責：

### ✔ 1. Runtime Error 分類
可識別常見 ROCm / HIP error patterns：
- hipErrorInvalidValue
- hipErrorIllegalAddress
- hipErrorMemoryAllocation
- hipErrorInvalidDevicePointer
- hipErrorLaunchFailure
- hipErrorUnknown
- PyTorch ROCm runtime error（kernel crash / missing operator）

### ✔ 2. Root Cause Analysis（深度推理）
例如：
- pointer 指向 host 但被當作 device pointer 使用
- launch grid 大於合法範圍
- kernel 中索引越界（未檢查 i < N）
- hipMemcpy direction 錯誤
- thread divergence 導致未定義行為
- 未同步 stream 導致讀寫競爭

### ✔ 3. 修復區塊產生（auto-fix block）
包括：
- 修正版程式碼區段
- 必須加入的 boundary check
- 正確的 hipMemcpy direction
- 正確 kernel configurations
- 建議的錯誤處理

### ✔ 4. 文件連結（Document Links）
若需要，也可主動查出：
- 對應 HIP API 文件
- 對應錯誤碼文件

### ✔ 5. 統一 JSON Output（給前端顯示卡片）
---

# 3. Input（來自 Master Agent）
Master Agent 在 Error 模式時預處理後的 payload：

```json
{
  "mode": "error",
  "preprocessed": {
     "error_type": "hipErrorIllegalAddress",
     "error_message": "illegal memory access was encountered",
     "likely_api": "hipMemcpyAsync",
     "stack_trace": ["..."],
     "code_context": "...相關程式碼片段...",
     "pointer_metadata": {"A":"device", "B":"host"}
  },
  "raw_input": "請幫我 debug",
  "session_id": "sess-991"
}
```

Error Worker 會使用 error metadata 提升推理準確度。

---

# 4. Output（回前端的 JSON）
```json
{
  "error_summary": "...錯誤的高階解讀...",
  "root_cause": "...根本原因...",
  "evidence": ["line 42 使用了 host pointer"],
  "fix_steps": ["將 hipMemcpy 起始參數改為 hipMemcpyHostToDevice"],
  "fixed_code": "...修正版程式碼（若可生成）...",
  "risk_analysis": [...],
  "related_api_docs": [...],
  "context_sync_key": "sess-991"
}
```

---

# 5. Tools 使用（Sub-tools）
Error Worker Agent 會使用：

### ✔ Error Signature DB（由 Master 提供）
包括：
- error → 常見 root cause mapping
- hipErrorIllegalAddress → OOB / 指標指向 host 等
- hipErrorInvalidValue → API 參數錯誤
- hipErrorLaunchFailure → kernel 配置錯誤 / kernel bug

### ✔ Pointer Metadata（Master Preprocessing）
用於推理：
- host/device mismatch
- illegal access

### ✔ API Metadata DB
為 fix_steps 生成正確的 API 語法。

Error Worker 不使用：
- Static HIPify
- Document Chunker
- Performance Tuner

---

# 6. 系統 Prompt（System Message）
```
You are AMDlingo's Error Worker Agent.
Your job is to:
- Interpret AMD HIP / ROCm runtime errors
- Identify the precise root cause
- Provide step-by-step actionable fixes
- Produce corrected code when possible
- Warn about undefined behavior and memory risks

You must:
- Be deterministic and technically accurate
- Identify the true cause, not just repeat the error message
- Avoid hallucinating nonexistent APIs
- Always reason based on HIP semantics and GPU memory rules

Always output using the required JSON format.
```

---

# 7. 模式驗證 Prompt（Mode Check）
```
Verify whether mode="error" is correct.
If incorrect:
{ "mode_ok": false, "suggest_mode": "code | document | hipify | api" }
Else:
{ "mode_ok": true }
```

---

# 8. Reasoning Workflow
```
Master preprocessing（error signature + metadata）
          ↓
Mode check（is this really an error message?）
          ↓
Identify error signature
          ↓
Use pointer metadata + code context for deep reasoning
          ↓
Determine most likely root cause
          ↓
Generate fix steps
          ↓
Generate corrected code
          ↓
Output JSON
```

---

# 9. Pseudo-code（可交給工程師）
```python
def error_worker_agent(payload):

    mode_ok, suggest = llm_check_mode(payload)
    if not mode_ok:
        return reroute(suggest)

    error_info = payload.preprocessed

    reasoning = llm_generate({
        "error_type": error_info["error_type"],
        "error_message": error_info["error_message"],
        "stack_trace": error_info["stack_trace"],
        "code_context": error_info["code_context"],
        "pointer_metadata": error_info.get("pointer_metadata", {})
    })

    return {
      "error_summary": reasoning.error_summary,
      "root_cause": reasoning.root_cause,
      "evidence": reasoning.evidence,
      "fix_steps": reasoning.fix_steps,
      "fixed_code": reasoning.fixed_code,
      "risk_analysis": reasoning.risk_analysis,
      "related_api_docs": reasoning.related_api_docs,
      "context_sync_key": payload.session_id
    }
```

---

# 10. Demo 使用案例（最重要）
### 使用者輸入：
```
hipErrorIllegalAddress: illegal memory access was encountered
```
### Code Context（Master 提供）：
```
int i = threadIdx.x + blockIdx.x * blockDim.x;
C[i] = A[i] + B[i];
```
### Error Worker Agent 推論結果：
- **Root cause**：索引 i 未檢查是否 < N
- **Evidence**：沒有 boundary check，造成非法訪問
- **Fix steps**：加入 if (i < N)
- **fixed_code**：提供修正版 kernel
- **risk_analysis**：若未修復，可能導致 silent data corruption

---

# 11. Summary（給簡報用）
Error Worker Agent 是 AMDlingo 解決開發者痛點最強的一環：
- 自動讀懂 GPU runtime errors
- 解析錯誤真正原因
- 自動生成修正版程式碼
- 提供修復步驟 + 風險分析
- 有助於降低 AMD 生態新手入坑難度

它是 Debug 相關功能的核心支柱，也是最能展現 MI300X 大模型 reasoning 能力的 Agent。

---

此規格 v1.0 可用於：
- ADK Agent Graph
- 後端實作
- Hackathon Demo
- Debug UI 設計

