# AMDlingo — Document Worker Agent Specification v1.0

Document Worker Agent 是 AMDlingo 中負責「技術文件理解、知識重構、範例生成、API 解釋」的核心 AI Agent。
其任務是將 ROCm / HIP / MI300X 的技術文件轉換成 **可讀、可用、可執行的工程知識**。

---

# 1. 角色定位（Role Definition）
Document Worker Agent 的使命：
> **讀懂 AMD 技術文件 → 提取工程重點 → 自動補充背景知識 → 生成程式碼實例 → 協助開發者理解文件。**

它不是搜尋器，而是：
- 技術文件翻譯員
- API 說明生成器
- 實作範例補完器
- 工程觀念連結者（cross-section mapper）

---

# 2. 功能範圍（Scope）
Document Worker Agent 需要完成：

### ✔ 1. 文件重點摘要（工程向，而非泛用摘要）
- 背景意義
- 適用情境
- 限制條件
- 注意事項

### ✔ 2. API 自動解析 + 說明生成
從 Master Agent preprocessing 得到 API list 之後：
- 描述 API 功能
- 提取與補充參數意義
- 回傳值解釋
- 常見誤用（pitfalls）
- 正確使用方式

### ✔ 3. 自動產生可執行範例（example synthesis）
文件有範例 → 提升可讀性
文件沒範例 → Worker 必須生成：
- 正確示例
- 反例（錯誤示例）
- HIP 架構最佳實務版本

### ✔ 4. 跨文件概念連結（Cross-Section Linking）
例如文件沒提 memory model，但 API 與 memory 有關，Worker 需自動補上：

> 「此 API 與 Memory Model 有緊密關聯，請注意 Host/Device 指標差異。」

### ✔ 5. 輸出固定 JSON Schema（供前端使用）
回傳結構化內容，用於 Web Plugin 與 VSCode 插件呈現。

---

# 3. Input（由 Master Agent 傳入）
Document Worker Agent 僅接收 Master 處理後、乾淨的 payload：

```json
{
  "mode": "document",
  "preprocessed": {
    "url": "https://rocm.docs.amd.com/projects/HIP/en/latest/api/hipMemcpy.html",
    "title": "hipMemcpy",
    "api_list": ["hipMemcpy", "hipMemcpyAsync"],
    "section_headers": ["Description", "Parameters", "Return Value"],
    "raw_text": "...AMD 官方文件內容...",
    "document_category": "HIP Runtime API"
  },
  "raw_input": "幫我看懂這段文件",
  "session_id": "abc123"
}
```

Document Worker 不負責抽字串，只負責推理。所有 parsing 都已由 Master 完成。

---

# 4. Output（回前端的 JSON 格式）

```json
{
  "summary": "...工程向文件摘要...",
  "api_explanations": [
    {
      "name": "hipMemcpy",
      "description": "...功能描述...",
      "parameters": "...參數解釋...",
      "return": "...回傳值...",
      "common_pitfalls": ["錯誤 direction", "未同步 stream"],
      "example_code": "...HIP 範例..."
    }
  ],
  "key_points": [...],
  "pitfalls": [...],
  "concept_links": [...],
  "example_code": "...綜合示例...",
  "notes": "...補充說明...",
  "context_sync_key": "abc123"
}
```

此 JSON 是前端渲染卡片 UI 的資料來源。

---

# 5. Tools 使用（Sub-tools）
Document Worker Agent 會使用：

- **API Metadata DB** → 提供 deterministic API description
- **Code Generator（LLM 推理）**
- **Concept Linker（LLM 推理）**

它不會使用：
- Error Parser
- HIPify Static Converter
- Kernel Tuner

---

# 6. 核心 Prompt（System Message）

```
You are AMDlingo's Documentation Worker Agent.
Your job is to read AMD technical documentation (ROCm, HIP, PyTorch ROCm, MI300X) and
convert it into developer-friendly knowledge.

You must:
- Summarize the document with engineering clarity.
- Explain all APIs mentioned.
- Provide correct code examples even if the documentation has none.
- Highlight common pitfalls and constraints.
- Link concepts across the documentation (memory model, synchronization).
- Focus on HIP/ROCm correctness.
- Avoid hallucinating nonexistent APIs.

Always output using the required JSON format.
```

---

# 7. Worker Agent 驗證 Prompt（mode check）

```
Check whether the assigned mode="document" is correct.
If incorrect, respond:
{ "mode_ok": false, "suggest_mode": "code | error | hipify | api" }
Else:
{ "mode_ok": true }
```

Master Agent 若收到 mode_ok=false，會 reroute。

---

# 8. Reasoning 流程（Workflow）

1. Mode 檢查
2. 對文件內容做語意理解
3. 從 DB 取出 API metadata
4. 組合文件內容 + metadata
5. 生出解釋、範例、pitfalls
6. 輸出結構化 JSON

---

# 9. Pseudo-code（可直接交給工程師）

```python
def document_worker_agent(payload):

    # 1. LLM 檢查模式
    mode_ok, suggest = llm_check_mode(payload)
    if not mode_ok:
        return reroute(suggest)

    # 2. 提取 API metadata
    api_infos = []
    for api in payload.preprocessed.api_list:
        api_infos.append(load_api_metadata(api))

    # 3. 主推理：結合文件 + metadata
    reasoning = llm_generate({
        "document_text": payload.preprocessed.raw_text,
        "api_metadata": api_infos,
        "title": payload.preprocessed.title
    })

    # 4. 組合輸出
    return {
       "summary": reasoning.summary,
       "api_explanations": reasoning.api_blocks,
       "key_points": reasoning.key_points,
       "pitfalls": reasoning.pitfalls,
       "example_code": reasoning.code_example,
       "notes": reasoning.notes,
       "context_sync_key": payload.session_id
    }
```

---

# 10. 下載 AMD 技術文件（官方來源）
Document Worker Agent 主要面向以下資料來源：

## ✔ ROCm 官方文件
https://rocm.docs.amd.com/

### 常用區：
- HIP API Reference: https://rocm.docs.amd.com/projects/HIP/en/latest/api/index.html
- ROCm Libraries (rocBLAS / rocFFT / MIOpen): https://rocm.docs.amd.com/projects/
- Runtime / Compiler / Tools: https://rocm.docs.amd.com/en/latest/deploy/

---

## ✔ HIP 官方 GitHub
https://github.com/ROCm/HIP

用途：
- 範例程式碼
- API mapping（CUDA ↔ HIP）

---

## ✔ ROCm GitHub（編譯器 / 工具鏈 / ISA）
https://github.com/ROCm

用途：
- 檢視 kernel 實作
- MLIR / LLVM 後端
- rocprof / rocgdb 文件

---

## ✔ MI300X / CDNA3 架構公開資料
https://www.amd.com/en/products/accelerators/instinct/mi300-series

用途：
- Matrix Core 行為
- HBM3 規格
- Infinity Fabric

---

## ✔ PyTorch on ROCm 官方指南
https://pytorch.org/get-started/locally/#rocm

用途：
- framework 安裝
- 相容性
- 常見 runtime error

---

# 11. Summary（給簡報用）
Document Worker Agent 能將繁雜的 AMD 技術文件轉換成：
- 結構化資訊
- 即用工程知識
- 自動 API 解說
- 自動程式碼生成
- 常見錯誤與限制提示

它是 AMDlingo 中負責「技術理解」的最重要 agent。

---

此規格可直接用於：
- ADK Agent Graph
- 後端實作
- Hackathon Pitch 文件
- 前端 UI 設計

