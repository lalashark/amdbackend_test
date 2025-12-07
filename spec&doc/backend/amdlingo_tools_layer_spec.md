# AMDlingo — Tools Layer Specification v1.0

Tools Layer 是 AMDlingo 系統中 **所有非 AI、deterministic、可重複、可預測的工程工具集合**。

它負責：
- **降低 LLM 推理成本**（避免每次都丟給模型）
- **提高準確度**（避免模型幻覺）
- **提供 Worker Agents 必要的 metadata**（API/錯誤碼/程式結構）
- **形成 Multi-Agent 架構的基礎能力層**

Tools Layer = 「模型之前的所有能力」。

本文件定義 Tools 的：
- 功能設計
- Input/Output
- 實作方式
- 與 Master/Worker 的關係

---

# 🔧 Tools Layer 架構圖
```
User Input
   ↓
Master Agent ----→ Tools Layer → Preprocessed Payload → Worker Agents
```

Tools 不直接與使用者互動，只做純工程處理。

---
# 1. Tool #1 — Static HIPify Converter
**用途：** CUDA → HIP 的機械式字串與 AST mapping。

### 功能：
- 以 hipify-clang / hipify-perl 為基礎
- 將 CUDA API 替換成 HIP API
- 產生 mapping report（每一個 from → to）
- 偵測未轉換語法（dead zones）

### Input：
```json
{
  "code": "...CUDA code..."
}
```

### Output：
```json
{
  "hipified_code": "...HIP code...",
  "mapping_report": [...],
  "unconverted_segments": [...]
}
```

---
# 2. Tool #2 — Error Signature DB
**用途：** 對常見 GPU / HIP runtime error 進行 deterministic 匹配。

### 內容：
- hipErrorIllegalAddress → 常見原因列表
- hipErrorInvalidValue → 參數錯誤
- hipErrorLaunchFailure → kernel crash
- PyTorch ROCm error signatures

### Output：
```json
{
  "error_type": "hipErrorIllegalAddress",
  "typical_causes": ["pointer mismatch", "OOB access"]
}
```

Worker Agent 再基於 context 進行推理。

---
# 3. Tool #3 — API Metadata DB
**用途：** 給 API Worker / Code Worker 提供 deterministic 資料。

每一個 API 包含：
- name
- description（官方文件摘錄）
- parameters
- return type
- category（Memory / Stream / Device）
- common pitfalls（非 AI，可人工整理）

### Output：
```json
{
  "hipMemcpy": {
     "description": "Copies memory between host and device.",
     "parameters": [...],
     "return": "hipError_t",
     "category": "Memory API"
  }
}
```

---
# 4. Tool #4 — Code Pattern Extractor
**用途：** 解析 GPU 程式碼中的結構（在 Worker 前完成）。

### 能做：
- 偵測 kernel 宣告（__global__）
- 抽出 indexing expression（i = threadIdx.x + ...）
- 抽出 pointer metadata（A 是 device pointer？）
- 抽出 launch config

### Output：
```json
{
  "kernel_blocks": [...],
  "pointer_metadata": { "A": "device", "B": "host" },
  "index_patterns": ["i = ..."],
  "launch_config": {"grid":..., "block":...}
}
```

---
# 5. Tool #5 — Pointer Analyzer
**用途：** 確定指標屬性（host/device/shared/global）。

使用規則：
- 若從 hipMalloc → device pointer
- 若從 malloc/new → host pointer

### Output：
```json
{
  "A": "device",
  "B": "host"
}
```

---
# 6. Tool #6 — Kernel Launch Inspector
**用途：** 檢查 kernel 參數與 launch 設定是否合理。

### 檢查：
- grid/block size 是否與 N compatible
- 是否缺 boundary check
- 是否有 thread divergence risk

### Output：
```json
{
  "issues": ["missing boundary check", "block too large for GPU"]
}
```

---
# 7. Tool #7 — Document Structure Extractor
**用途：** 將 AMD 官方文件解析成：
- 標題（H1/H2/H3）
- API 名稱
- 參數段落
- 表格
- 注意事項

### Output：
```json
{
  "title": "hipMemcpy",
  "headers": [...],
  "api_list": [...],
  "raw_text": "...cleaned document..."
}
```

---
# 8. Tools Layer → Master Agent 整合流程
```
Raw input
   ↓
Master Agent
   ↓ (calls)
Tools Layer
   ↓
Preprocessed structured payload
   ↓
Worker Agents (Document/Code/Error/HIPify/API)
```

Tools Layer 只能做 deterministic 工作，不包含推理。

---
# 9. Summary（給簡報用）
Tools Layer 讓 AMDlingo：
- **降低 LLM 成本**（前處理交給工具）
- **提升準確度**（使用 DB / deterministic 程式）
- **性能更高**（避免 LLM 做 parsing 工作）
- **讓 Worker Agents 專注推理，不做清理工作**

這是多代理架構中最關鍵的「啟動層」。

