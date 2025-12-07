# AMDlingo — HIPify Worker Agent Specification v1.0

HIPify Worker Agent 是 AMDlingo 中專責處理 **CUDA → HIP 移植輔助** 的推理代理。

它與 static HIPify 工具（非 AI）形成互補：
- Static HIPify：負責**機械式 API / 語法替換**（mapping-based）
- HIPify Worker Agent：負責**語意層解釋、補強轉換、處理無法自動轉換的部分**

換句話說，HIPify Worker Agent 是：
> **從工程師角度解釋「為什麼這樣轉」、補完「工具轉不了的部分」、產出可執行 HIP 程式碼的最後一關。**

---

# 1. 角色定位（Role Definition）

HIPify Worker Agent 的核心任務：
- 將 static HIPify 產生的結果進行 **語意檢查與補強**
- 解釋 CUDA → HIP 差異
- 重新組織程式碼使之在 AMD ROCm 上能安全運作
- 提供明確的「前後差異說明」與「轉換理由」

它不是單純的一鍵轉換，而是：
- 移植顧問（Porting Consultant）
- 差異解說員（Diff Explainer）
- 風險警告器（Risk Highlighter）

---

# 2. 功能範圍（Scope）

HIPify Worker Agent 需要完成：

### ✔ 1. 檢查 static HIPify 結果
Master Agent / Static Tool 已先做：
- CUDA API → HIP API mapping
- cudaMalloc → hipMalloc
- cudaMemcpy → hipMemcpy

Worker Agent 需：
- 確認 mapping 是否合理
- 找出仍殘留的 CUDA 特有語法

### ✔ 2. 處理無法自動轉換的語法 / 特性
例如：
- `<<< >>>` kernel launch 語法
- `dim3 grid, block;` 配置
- CUDA stream / event 特有用法
- CUDA 特有 library（如 Thrust）

Worker Agent 必須：
- 指出這些地方需要人工處理
- 儘可能提供 HIP 等效寫法

### ✔ 3. 解釋 CUDA ↔ HIP 差異
包括：
- API 命名／語義差異
- kernel launch 方式差異
- 記憶體 API 差異
- 錯誤處理方式差異

### ✔ 4. 產生最終 HIP 程式碼
輸出：
- 可編譯之 HIP code（儘可能完整）
- 針對無法自動轉換的部分給註解 TODO

### ✔ 5. 建立差異報告（Diff Report）
包含：
- 轉換前後主要變化列表
- 每個變化對應的技術理由

### ✔ 6. JSON Output
供前端產生「移植報告」與「code diff 檢視」。

---

# 3. Input（來自 Master Agent）

Master Agent 在 HIPify 模式下，會先用 **static HIPify tool** 做第一次轉換，並將結果與原始程式碼打包給 HIPify Worker Agent：

```json
{
  "mode": "hipify",
  "preprocessed": {
    "original_code": "...CUDA 原始程式碼...",
    "hipified_code_static": "...static HIPify 產生的程式碼...",
    "mapping_report": [
       {"from": "cudaMalloc", "to": "hipMalloc"},
       {"from": "cudaMemcpy", "to": "hipMemcpy"}
    ],
    "unconverted_segments": [
       "<<<grid, block>>>",
       "thrust::sort(...)"
    ]
  },
  "raw_input": "幫我把這段 code 轉成 HIP 並解釋差異",
  "session_id": "hipify-001"
}
```

---

# 4. Output（回給前端的 JSON）

```json
{
  "hip_code_final": "...經過 Worker 修正與補強後的 HIP 程式碼...",
  "hip_code_static": "...static HIPify 原始輸出（可選擇一起回傳）...",
  "diff_summary": [
     {"type": "api_mapping", "from": "cudaMalloc", "to": "hipMalloc", "reason": "HIP runtime 替代"},
     {"type": "kernel_launch", "from": "<<<grid, block>>>", "to": "hipLaunchKernelGGL(...)"}
  ],
  "unconverted_notes": [
     {
       "segment": "thrust::sort(...)",
       "status": "manual_port_required",
       "suggestion": "改用 rocPRIM 或 host-side sort，再 memcpy 至 device"
     }
  ],
  "porting_risks": [
     "請確認原本使用的 CUDA library 是否有 ROCm 對應版本",
     "請驗證 kernel launch 參數是否符合目標 GPU 架構"
  ],
  "explanation": "...以工程師角度解釋整體移植策略...",
  "context_sync_key": "hipify-001"
}
```

---

# 5. Tools 使用（Sub-tools）

HIPify Worker Agent 會使用：

### ✔ Static HIPify Report（由 Master 提供）
- API mapping 列表
- 未轉換區段列表

### ✔ API Metadata DB
- hipMalloc / hipMemcpy / hipLaunchKernelGGL 語意

### ✔ Optional: Pattern Helper
- 協助將 `<<< >>>` 轉成 hipLaunchKernelGGL 語法

它不會：
- 重新發明 mapping 邏輯（由 DB / static tool 提供）
- 處理 runtime error（交給 Error Worker）

---

# 6. 系統 Prompt（System Message）

```
You are AMDlingo's HIPify Worker Agent.
Your job is to:
- Review CUDA → HIP static conversion results,
- Fix or complete any missing or incorrect mappings,
- Explain the key differences between CUDA and HIP usage,
- Produce a final HIP code that is as correct and compilable as possible,
- Highlight segments that still require manual porting.

You must:
- Respect existing static mappings when they are correct,
- Avoid inventing nonexistent HIP APIs,
- Clearly distinguish between automatically ported code and TODO/manual parts,
- Provide short but precise engineering explanations.

Always output using the required JSON format.
```

---

# 7. 模式驗證 Prompt（Mode Check）

```
Verify whether mode="hipify" is correct.
If incorrect:
{ "mode_ok": false, "suggest_mode": "code | error | document | api" }
Else:
{ "mode_ok": true }
```

---

# 8. Reasoning Workflow

```
Master static HIPify preprocessing
           ↓
Mode check
           ↓
Compare original CUDA code vs static HIPify result
           ↓
Identify remaining CUDA-specific constructs
           ↓
Fix mappings where needed
           ↓
Generate final HIP code with comments
           ↓
Produce diff summary & risk notes
           ↓
Output JSON
```

---

# 9. Pseudo-code（可交給工程師）

```python
def hipify_worker_agent(payload):

    mode_ok, suggest = llm_check_mode(payload)
    if not mode_ok:
        return reroute(suggest)

    p = payload.preprocessed

    reasoning = llm_generate({
        "original_code": p["original_code"],
        "hipified_code_static": p["hipified_code_static"],
        "mapping_report": p["mapping_report"],
        "unconverted_segments": p["unconverted_segments"]
    })

    return {
      "hip_code_final": reasoning.hip_code_final,
      "hip_code_static": p["hipified_code_static"],
      "diff_summary": reasoning.diff_summary,
      "unconverted_notes": reasoning.unconverted_notes,
      "porting_risks": reasoning.porting_risks,
      "explanation": reasoning.explanation,
      "context_sync_key": payload.session_id
    }
```

---

# 10. 相關技術文件下載來源

HIPify Worker Agent 涉及 CUDA → HIP 移植，需要參考：

## ✔ HIP 官方文件（ROCｍ Docs）
- HIP API Reference：  
  https://rocm.docs.amd.com/projects/HIP/en/latest/api/index.html
- HIP Programming Guide：  
  https://rocm.docs.amd.com/projects/HIP/en/latest/

## ✔ HIPify 工具來源（GitHub）
- HIPify-clang / hipify-perl：  
  https://github.com/ROCm-Developer-Tools/HIPIFY

用途：
- 了解現有 mapping 規則
- 確認哪些語法目前不支援自動轉換

## ✔ CUDA 官方文件（作為對照）
- CUDA C++ Programming Guide：  
  https://docs.nvidia.com/cuda/cuda-c-programming-guide/
- CUDA Runtime API：  
  https://docs.nvidia.com/cuda/cuda-runtime-api

用途：
- 比對 CUDA API 語意
- 理解原始程式碼設計意圖

---

# 11. Summary（給簡報用）

HIPify Worker Agent 負責：
- 接手 static HIPify 的初步轉換結果
- 深度理解程式語意
- 補強 mapping、處理轉換 dead zones
- 解釋 CUDA/HIP 差異
- 產出接近可直接 compiler 通過的 HIP code

它讓「CUDA → AMD ROCm」的遷移路徑不再只是機械式搜尋替換，而是有**語意理解、差異說明與風險提示**的工程級工具。

---

此規格 v1.0 可用於：
- Multi-agent Graph（HIPify branch）
- 實作 backend HIPify pipeline
- Hackathon Demo（CUDA 專案一鍵遷移到 AMD）
- 技術簡報中說明移植價值

