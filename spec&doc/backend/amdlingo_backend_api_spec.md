# AMDlingo — Backend API Specification v1.1

> **更新內容（v1.1）：加入「聊天紀錄同步機制（Session History Sync）」完整後端設計，包括：**
>
> - `/session/history` API（Web ↔ VSCode 同步）
> - `/session/append` API（Worker 結果寫入）
> - Session Store 資料模型
> - Request/Response schema
> - Request lifecycle 流程更新

以下為已整合更新後的完整 Backend API Spec。

Backend API 是整個 AMDlingo 系統的「對外介面」，負責：

- 接收前端（Web Plugin / VSCode Plugin）輸入
- 呼叫 Master Agent（Routing + Preprocessing）
- 指派正確的 Worker Agent
- 回傳結構化 JSON 結果

本規格定義：

- API 架構
- Route 設計
- Request/Response schema
- 錯誤處理
- Session / 對話管理

Backend 不做推理，也不做 parsing。它的任務是協調與調度。

---

# 1. Backend 整體架構

```
Frontend (Web / VSCode)
      ↓ REST API
Backend API Layer
      ↓ calls
Master Agent
      ↓ dispatch
Worker Agents
      ↓ return JSON
Backend API returns to frontend
```

Backend 層必須保持 Stateless（用 session\_id 控制上下文）。

---

# 2. API Route 列表

AMDlingo 核心共五條分析型 API（對應 5 個 Worker Agents）：

| Route               | Method | Description                    |
| ------------------- | ------ | ------------------------------ |
| `/analyze/document` | POST   | 技術文件解析（Document Worker）        |
| `/analyze/code`     | POST   | 程式碼分析（Code Worker）             |
| `/analyze/error`    | POST   | Runtime error 分析（Error Worker） |
| `/convert/hipify`   | POST   | CUDA → HIP 移植（HIPify Worker）   |
| `/lookup/api`       | POST   | API 查詢（API Worker）             |

此外還需：

| Route              | Method | Description         |
| ------------------ | ------ | ------------------- |
| `/session/create`  | POST   | 建立新 session         |
| `/session/history` | GET    | 取得 session 對話歷史（可選） |

---

# 3. 共通 Request Schema（五大分析 API 通用）

所有 `/analyze/*` routes 共用基本 schema：

```json
{
  "text": "使用者輸入 (文件、程式碼、錯誤、API query)",
  "explicit_mode": "document | code | error | hipify | api | null",
  "parallel_modes": ["document", "code", "error", "hipify", "api"],
  "session_id": "abcd-1234",
  "url": "(若是 document 模式)"
}
```

Backend → Master Agent：

- 不改動文字
- 不拆字串
- 不處理文件

---

# 4. 通用 Response Schema

Backend 必須回傳 Worker Agent 的結果：

```json
{
  "mode": "code",
  "result": { ... Worker Agent JSON ... },
  "session_id": "abcd-1234",
  "usage": {
     "tokens_input": 1234,
     "tokens_output": 645
  }
}
```

Backend 不改動 Worker Agent 的結果。

---

# 5. Route 細部規格

---

## 5.1 `/analyze/document` — Document Worker

**用途：** 技術文件導讀與摘要。

### Request

```json
{
  "text": "...文件或網址...",
  "url": "https://rocm.docs.amd.com/...",
  "session_id": "sess-01"
}
```

### Response（範例）

```json
{
  "mode": "document",
  "result": {
     "summary": "...",
     "api_explanations": [...],
     "example_code": "..."
  },
  "session_id": "sess-01"
}
```

---

## 5.2 `/analyze/code` — Code Worker

### Request

```json
{
  "text": "__global__ void add(...) {...}",
  "session_id": "sess-02"
}
```

### Response

```json
{
 "mode": "code",
 "result": {
    "summary": "...code intention...",
    "issues": [...],
    "fixed_code": "..."
 }
}
```

---

## 5.3 `/analyze/error` — Error Worker

### Request

```json
{
  "text": "hipErrorIllegalAddress: illegal memory access",
  "session_id": "sess-03"
}
```

### Response

```json
{
  "mode": "error",
  "result": {
    "error_summary": "...",
    "root_cause": "...",
    "fix_steps": [...]
  }
}
```

---

## 5.4 `/convert/hipify` — HIPify Worker

### Request

```json
{
 "text": "cudaMemcpy(A,B,N,cudaMemcpyHostToDevice);",
 "session_id": "sess-04"
}
```

### Response

```json
{
 "mode": "hipify",
 "result": {
    "hip_code_final": "...",
    "diff_summary": [...],
    "unconverted_notes": [...]
 }
}
```

---

## 5.5 `/lookup/api` — API Worker

### Request

```json
{
 "text": "hipMalloc",
 "session_id": "sess-05"
}
```

### Response

```json
{
 "mode": "api",
 "result": {
    "api_name": "hipMalloc",
    "description": "...",
    "example_code": "..."
 }
}
```

---

# 6. Session 管理（更新：加入聊天同步機制）

Backend API 需支援 session，以同步：

- Web Plugin
- VSCode Plugin

Session 僅保存 Worker 的結果，不保存模型完整對話。

## ✔ 6.1 `/session/create` — 建立 session

```json
{
  "session_id": "sess-1234"
}
```

---

## ✔ 6.2 `/session/append` — 將此次對話加入歷史（後端自動呼叫）

每次 Worker Agent 返回結果後，Backend 會呼叫此 API 將內容寫入 Session Store。

### Request

```json
{
  "session_id": "sess-1234",
  "entry": {
    "role": "assistant",
    "mode": "code",
    "result": { /* Worker JSON */ }
  }
}
```

### Entry 結構

```json
{
  "role": "user" | "assistant",
  "text": "原始使用者輸入（若為 user）",
  "mode": "code | document | error | hipify | api",
  "result": { /* worker output JSON */ }
}
```

---

## ✔ 6.3 `/session/history` — 前端同步（Web ↔ VSCode）

使用 `session_id` 抓取全部聊天歷史。

### GET Response

```json
{
  "session_id": "sess-1234",
  "history": [
    {
      "role": "user",
      "text": "請解釋 hipMemcpy",
      "mode": "api"
    },
    {
      "role": "assistant",
      "mode": "api",
      "result": {
         "api_name": "hipMemcpy",
         "description": "..."
      }
    }
  ]
}
```

---

## ✔ Session Store 資料結構

可使用 SQLite / Redis / Postgres。

資料模型：

```
session_id: string
history: [ {role, text, mode, result} ]
```

---

# 7. 錯誤處理（Backend-level）

錯誤處理（Backend-level） Backend 不解析 GPU 錯誤，但需處理 HTTP 層錯誤：

### HTTP 400 - Bad Request

- 缺 text
- session\_id 格式錯誤

### HTTP 500 - Internal

- Master Agent crash
- Worker Agent crash

### HTTP 422 - Unprocessable

- 模型無法解析 payload

---

# 8. Backend → Master Agent 呼叫規範

Backend 必須傳入：

```json
{
 "text": "...",
 "explicit_mode": null,
 "parallel_modes": ["document","code","error","hipify","api"],
 "url": null,
 "session_id": "..."
}
```

Master Agent 回應：

```json
{
 "mode": "code",
 "preprocessed": { ... },
 "session_id": "..."
}
```

Backend 再將此 payload 傳給 Worker Agent。

---

# 9. Backend 生命週期（Request → Response）

```
Frontend Request
     ↓
Backend API
     ↓
Master Agent (routing + preprocessing)
     ↓
Worker Agent
     ↓
Backend assembles final JSON
     ↓
Return to Frontend
```

Backend 本身完全 stateless。

---

# 10. Summary（給簡報用）

Backend API 是整個 AMDlingo 的「資料中樞」，負責：

- 将使用者輸入接入 Multi-Agent 系統
- 將非 AI routing 與 preprocessing 委派給 Master Agent
- 將 reasoning 委派給 Worker Agents
- 回傳可視化、結構化的 JSON 給前端

它不做 AI 推理，是架構中最穩定也最關鍵的調度層。

---

此 Backend API Spec v1.0 可用於：

- 後端工程實作
- 多代理協作流程設計
- Hackathon 技術簡報

