# Hướng dẫn Cài đặt và Chạy Backend Mới

## Tóm tắt

Backend đã được refactor để implement flow:
```
User Query → LLM Refine → Retrieval → Top 5 → LLM Verify 
  → Match: Generate với full context
  → No match: Multi-option cho user
```

Sử dụng **Langchain** cho memory management và query refinement.

---

## Bước 1: Cài đặt Dependencies

```bash
cd POC
pip install -r requirements.txt
```

Dependencies mới:
- `langchain>=0.1.0`
- `langchain-openai>=0.0.5`
- `langchain-core>=0.1.0`

---

## Bước 2: Kiểm tra Config

Mở file `backend/config.py` và kiểm tra:

```python
LLM_BASE_URL = "https://your-llm-endpoint.com/v1"  # ← Đảm bảo đúng URL
LLM_API_KEY = "your-api-key"                        # ← Đảm bảo đúng API key
LLM_MODEL = "glm-4.7-flash"                         # ← Model name
```

**Lưu ý:** Hiện tại đang dùng Ngrok URL, có thể thay đổi sau mỗi lần restart.

---

## Bước 3: Kiểm tra Index Files

Đảm bảo các file sau tồn tại trong `POC/index/`:
- `faiss.index`
- `bm25.pkl`
- `chunks.json`

Nếu chưa có, chạy:
```bash
cd POC
python script/chunking_script.py
python script/embedding_indexing_script.py
```

---

## Bước 4: Khởi động Server

```bash
cd POC
python backend/main.py
```

Hoặc với uvicorn:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 7860 --reload
```

Server sẽ chạy tại: **http://localhost:7860**

---

## Bước 5: Test Backend

### Option 1: Sử dụng Test Script
```bash
cd POC
python test_backend_flow.py
```

Script sẽ test 3 scenarios:
1. Query về môn cụ thể
2. Query mơ hồ → Clarification
3. Follow-up questions với memory

### Option 2: Sử dụng curl/Postman

**Test health:**
```bash
curl http://localhost:7860/health
```

**Test ask endpoint:**
```bash
curl -X POST http://localhost:7860/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Giảng viên môn Giải tích 2A là ai?",
    "session_id": "test123",
    "use_advanced": true
  }'
```

**Expected response:**
```json
{
  "answer": "Giảng viên môn Giải tích 2A là...",
  "sources": [...],
  "refined_query": "Giảng viên môn Giải tích 2A là ai?",
  "search_method": "SPECIFIC_COURSE",
  "timing_ms": 1250.5
}
```

**Test clarify endpoint (khi có multi-option):**
```bash
curl -X POST http://localhost:7860/clarify \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test123",
    "selected_code": "MTH00012",
    "original_question": "Cách tính điểm?"
  }'
```

---

## Bước 6: Integration với Frontend

Frontend không cần thay đổi gì, chỉ cần:

1. **Xử lý field mới trong response:**
   - `refined_query` (optional) - Query đã được refine
   - `selected_subject` (trong /clarify response)

2. **Xử lý multi-option khi `need_clarification = true`:**
```javascript
if (response.need_clarification) {
  // Hiển thị candidates cho user chọn
  const candidates = response.candidates;
  // [{code: "MTH00012", name: "Giải tích 2A"}, ...]
  
  // Khi user chọn, gọi /clarify
  fetch('/clarify', {
    method: 'POST',
    body: JSON.stringify({
      session_id: currentSessionId,
      selected_code: selectedCandidate.code,
      original_question: originalQuestion
    })
  });
}
```

---

## Flow Demo

### Scenario 1: Query rõ ràng
```
User: "Giảng viên môn Giải tích 2A là ai?"
→ Backend: LLM verify → Match = MTH00012
→ Response: Answer with full context
```

### Scenario 2: Query mơ hồ
```
User: "Cách tính điểm môn giải tích?"
→ Backend: LLM verify → No match (nhiều môn giải tích)
→ Response: {
    "need_clarification": true,
    "candidates": [
      {"code": "MTH00011", "name": "Giải tích 1"},
      {"code": "MTH00012", "name": "Giải tích 2A"},
      ...
    ]
  }

Frontend: Hiển thị options cho user
User: Chọn "Giải tích 2A"
→ POST /clarify với selected_code = "MTH00012"
→ Response: Answer with full context
```

### Scenario 3: Follow-up
```
Conversation:
User: "Môn Giải tích 2A có bao nhiêu tín chỉ?"
AI: "4 tín chỉ"
  → Memory: current_subject = "MTH00012"

User: "Giảng viên của nó là ai?"
  → Backend: Refine query → "Giảng viên của môn Giải tích 2A là ai?"
  → Skip search (current_subject đã có)
  → Response: Answer từ chunks của MTH00012
```

---

## Troubleshooting

### ❌ Error: "Retriever not initialized"
**Nguyên nhân:** Chưa có index files

**Giải pháp:**
```bash
cd POC
python script/embedding_indexing_script.py
```

### ❌ Error: "Module 'langchain' not found"
**Nguyên nhân:** Chưa cài Langchain

**Giải pháp:**
```bash
pip install langchain langchain-openai langchain-core
```

### ❌ Error: LLM timeout
**Nguyên nhân:** LLM endpoint không khả dụng hoặc quá tải

**Giải pháp:**
1. Kiểm tra `LLM_BASE_URL` trong `config.py`
2. Tăng `LLM_TIMEOUT` trong `config.py`
3. Kiểm tra Ngrok tunnel còn active không

### ❌ Query refinement không hoạt động
**Kiểm tra:**
1. Logs có hiển thị "Query refined: ..." không?
2. LLM có trả về response không?
3. Temperature có quá cao không? (nên dùng 0.1)

---

## Files Quan trọng

```
POC/
├── backend/
│   ├── main.py                    # API endpoints
│   ├── langchain_memory.py        # Memory management (NEW)
│   ├── llm_refiner.py             # Query refinement (NEW)
│   ├── adaptive_retriever.py      # Retrieval logic
│   ├── llm_interface.py           # LLM calls
│   └── config.py                  # Configuration
├── requirements.txt               # Dependencies
├── test_backend_flow.py           # Test script (NEW)
├── BACKEND_README.md              # Full documentation (NEW)
└── CHANGELOG.md                   # Change log (NEW)
```

---

## API Endpoints

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/health` | GET | Health check |
| `/stats` | GET | System statistics |
| `/ask` | POST | Main Q&A với memory |
| `/clarify` | POST | User chọn môn sau khi ambiguous |
| `/suggest-questions` | POST | Generate follow-up questions |
| `/feedback` | POST | Submit feedback |
| `/session/{id}` | DELETE | Xóa session |

---

## Checklist

Trước khi deploy production:

- [ ] Cài đặt tất cả dependencies
- [ ] Config LLM_BASE_URL và LLM_API_KEY
- [ ] Index files đã được tạo
- [ ] Test script pass tất cả scenarios
- [ ] Frontend integration hoạt động
- [ ] Logs được setup đúng
- [ ] Error handling được test
- [ ] Performance acceptable (< 2s per query)

---

## Next Steps

1. **Monitor query refinement accuracy:**
   - Log original vs refined queries
   - Track improvement metrics

2. **Optimize LLM calls:**
   - Cache verification results
   - Batch requests nếu có thể

3. **Improve memory:**
   - Implement Redis-backed memory cho persistence
   - Add conversation summarization

4. **Analytics:**
   - Track clarification rate
   - Monitor which subjects are most queried
   - A/B test different refinement prompts

---

**Done!** Backend đã sẵn sàng sử dụng với Langchain integration.

Để biết thêm chi tiết, xem: `BACKEND_README.md` và `CHANGELOG.md`
