# OCR 非同步化與並發控制 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 將 OCR LLM 呼叫從同步阻塞改為非同步非阻塞，加上並發控制（Semaphore），讓多人同時使用時後台不會卡住或崩潰。

**Architecture:** 把 `LLMApi.ocr_generate()` 改為 async，使用 `httpx.AsyncClient` 取代同步 `OpenAI` client。在 `OCRService` 層加 `asyncio.Semaphore` 限制同時 LLM 請求數為 2。移除每次請求都呼叫 `models.list()` 的邏輯，啟動時讀一次快取 model name。

**Tech Stack:** Python asyncio, httpx, FastAPI (already async)

---

### Task 1: 將 LLMApi 改為 AsyncLLMApi（非同步 + 快取 model name）

**Files:**
- Modify: `backend/services/ocr_service.py` — `LLMApi` class (lines 826-894)

**Step 1: 改寫 LLMApi 為 async**

將 `LLMApi` class 改為使用 `httpx.AsyncClient`，移除同步 `OpenAI` client。啟動時快取 model name，不再每次請求都呼叫 `models.list()`。

把以下舊的 `LLMApi` class（L826-894）替換為：

```python
class LLMApi:
    def __init__(self, model_path="/data1/models/OpenGVLab/InternVL3-8B"):
        self.model_path = model_path
        self.base_url = os.getenv("OCR_API_URL", "http://0.0.0.0:23333/v1")
        self.api_key = os.getenv("OCR_API_KEY", "YOUR_API_KEY")
        self.timeout = 45.0
        self._model_name = None  # cached model name
        # Keep sync client for backward compatibility (batch_ocr_image, parse_ocr_to_fields fallback)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=60.0,
            max_retries=1
        )

    async def _get_model_name(self) -> str:
        """Get and cache model name - only calls API once"""
        if self._model_name:
            return self._model_name
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/models")
            resp.raise_for_status()
            data = resp.json()
            if data.get("data"):
                self._model_name = data["data"][0]["id"]
                return self._model_name
        raise Exception("No models available from LLM server")

    async def async_ocr_generate(self, image_path, prompt="Only return the OCR result and don't provide any other explanations.", max_retries=2):
        """Async version of ocr_generate - non-blocking"""
        import httpx

        for attempt in range(max_retries):
            try:
                if image_path and not os.path.exists(image_path):
                    print(f"[OCR ERROR] Image path does not exist: {image_path}")
                    return "OCR錯誤: 圖片路徑不存在或無效"

                model_name = await self._get_model_name()
                print(f"[OCR DEBUG] Async processing (attempt {attempt + 1}/{max_retries}), model: {model_name}")

                # Build message content
                content = [{'type': 'text', 'text': prompt}]
                if image_path:
                    image_url = os.path.abspath(image_path)
                    content.append({'type': 'image_url', 'image_url': {'url': image_url}})

                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": content}],
                    "temperature": 0
                }

                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    )
                    resp.raise_for_status()
                    data = resp.json()

                result = data["choices"][0]["message"]["content"]
                if result and len(result.strip()) > 0:
                    print(f"[OCR SUCCESS] Async OCR result length: {len(result)}")
                    if len(result) > 100:
                        print(f"[OCR PREVIEW] {result[:100]}...")
                    return result.strip()
                else:
                    print(f"[OCR WARNING] Empty result on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        continue
                    return "OCR錯誤: 識別結果為空"

            except Exception as e:
                print(f"[OCR ERROR] Async API call failed on attempt {attempt + 1}: {e}")
                print(f"[OCR ERROR] Exception type: {type(e).__name__}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                return f"OCR識別失敗: {str(e)}"

        return "OCR錯誤: 所有重試均失敗"

    def ocr_generate(self, image_path, prompt="Only return the OCR result and don't provide any other explanations.", max_retries=3):
        """Sync version - kept for batch processing and parse_ocr_to_fields fallback"""
        for attempt in range(max_retries):
            try:
                if image_path and not os.path.exists(image_path):
                    print(f"[OCR ERROR] Image path does not exist: {image_path}")
                    return "OCR錯誤: 圖片路徑不存在或無效"

                image_url = f"{os.path.abspath(image_path)}" if image_path else ""
                print(f"[OCR DEBUG] Processing image (attempt {attempt + 1}/{max_retries}): {image_url}")

                # Use cached model name if available, otherwise fetch
                if not self._model_name:
                    try:
                        models = self.client.models.list()
                        if models.data:
                            self._model_name = models.data[0].id
                    except Exception as e:
                        print(f"[OCR ERROR] Failed to get models: {e}")
                        if attempt < max_retries - 1:
                            continue
                        return f"OCR錯誤: 無法獲取模型列表 - {str(e)}"

                model_name = self._model_name
                print(f"[OCR DEBUG] Using model: {model_name}")

                content = [{'type': 'text', 'text': prompt}]
                if image_path:
                    content.append({'type': 'image_url', 'image_url': {'url': image_url}})

                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[{'role': 'user', 'content': content}],
                    temperature=0,
                    timeout=45.0
                )

                result = response.choices[0].message.content
                if result and len(result.strip()) > 0:
                    print(f"[OCR SUCCESS] OCR result length: {len(result)}")
                    if len(result) > 100:
                        print(f"[OCR PREVIEW] {result[:100]}...")
                    return result.strip()
                else:
                    print(f"[OCR WARNING] Empty result on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        continue
                    return "OCR錯誤: 識別結果為空"

            except Exception as e:
                print(f"[OCR ERROR] API call failed on attempt {attempt + 1}: {e}")
                print(f"[OCR ERROR] Exception type: {type(e).__name__}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2)
                    continue
                return f"OCR識別失敗: {str(e)}"

        return "OCR錯誤: 所有重試均失敗"
```

**Key changes:**
- Added `async_ocr_generate()` using `httpx.AsyncClient` — non-blocking
- `_get_model_name()` caches model name, only calls API once
- Kept sync `ocr_generate()` for backward compat (batch processing)
- Reduced `max_retries` from 3 to 2 in async version, and `client max_retries` from 2 to 1
- `await asyncio.sleep(1)` instead of `time.sleep(2)` in async version

**Step 2: Verify no import issues**

Run: `cd /data1/165/ocr_v2/manage_card && python -c "from backend.services.ocr_service import LLMApi; print('OK')"`
Expected: `OK`

---

### Task 2: 在 OCRService 加入 Semaphore 並改用 async LLM 呼叫

**Files:**
- Modify: `backend/services/ocr_service.py` — `OCRService` class (lines 27-158)

**Step 1: 在 OCRService.__init__ 加入 semaphore**

在 `__init__` 方法（L30-48）中加入：

```python
def __init__(self):
    self.llm_api = LLMApi()
    self.card_enhancer = CardEnhancementService()
    # Limit concurrent LLM requests to prevent GPU overload
    self._llm_semaphore = asyncio.Semaphore(2)
    # ... rest unchanged
```

**Step 2: 改寫 ocr_image() 使用 async LLM 呼叫 + semaphore**

將 `ocr_image()` 方法（L50-158）中的 `self.llm_api.ocr_generate(...)` 呼叫改為：

```python
async with self._llm_semaphore:
    result = await self.llm_api.async_ocr_generate(temp_path, structured_prompt)
```

和重試部分同樣改為：

```python
async with self._llm_semaphore:
    result = await self.llm_api.async_ocr_generate(enhanced_path, structured_prompt)
```

**Step 3: 改寫 parse_ocr_to_fields() 為 async + semaphore**

`parse_ocr_to_fields()` 的 LLM fallback 呼叫（L252）也需要改為 async：

1. 方法簽名改為 `async def parse_ocr_to_fields(self, ocr_text: str, side: str) -> Dict[str, str]:`
2. LLM 呼叫改為：
```python
async with self._llm_semaphore:
    result = await self.llm_api.async_ocr_generate("", prompt)
```

**Step 4: Verify syntax**

Run: `cd /data1/165/ocr_v2/manage_card && python -c "from backend.services.ocr_service import OCRService; print('OK')"`

---

### Task 3: 更新 API endpoint 配合 async 變更

**Files:**
- Modify: `backend/api/v1/ocr.py` — `parse_ocr_fields` endpoint (line 23-35)

**Step 1: 更新 parse_ocr_fields endpoint**

`parse_ocr_to_fields` 現在是 async，所以需要加 `await`：

```python
@router.post("/parse-fields")
async def parse_ocr_fields(request: OCRParseRequest):
    try:
        parsed_fields = await ocr_service.parse_ocr_to_fields(request.ocr_text, request.side)
        return {
            "success": True,
            "parsed_fields": parsed_fields,
            "side": request.side
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR解析失敗: {str(e)}")
```

Note: `ocr_image` endpoint（line 14）已經在用 `await`，不需要改。

---

### Task 4: 驗證整體功能

**Step 1: 重啟後台**

```bash
# Find and kill current process
kill $(pgrep -f "python main.py" | head -1)
sleep 2
cd /data1/165/ocr_v2/manage_card && nohup python main.py > backend/nohup_backend.log 2>&1 &
sleep 3
```

**Step 2: 驗證 health check 正常**

```bash
curl -s --max-time 5 http://localhost:8006/health
```
Expected: `{"status": "healthy", ...}`

**Step 3: 驗證 OCR endpoint 可用**

用瀏覽器或 curl 測試一張名片圖片的 OCR。

**Step 4: 驗證並發不阻塞**

在 OCR 處理中，同時訪問其他 API（如 `/api/v1/cards/`），確認不會被卡住。

---

## Summary of Changes

| 改動 | 效果 |
|------|------|
| `async_ocr_generate()` 用 httpx | LLM 呼叫不阻塞 event loop，其他請求正常回應 |
| `asyncio.Semaphore(2)` | 最多 2 個 LLM 請求同時跑，防止 GPU 雪崩 |
| 快取 model name | 減少不必要的 API 呼叫 |
| 降低重試次數 | 失敗時更快回報，不長時間佔用資源 |
| 保留同步 `ocr_generate()` | batch processing 等現有功能不受影響 |
