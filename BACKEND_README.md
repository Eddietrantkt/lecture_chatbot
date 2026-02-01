# Backend Q&A với Langchain Integration

## Tổng quan

Backend đã được refactor để sử dụng **Langchain** cho memory management và query refinement, theo logic flow sau:

```
User Query 
  ↓
[1] LLM Refine Query (dựa trên conversation context)
  ↓
[2] Hybrid Retrieval (FAISS + BM25) → Top 50 candidates
  ↓
[3] Extract Top 5 môn học (unique subjects)
  ↓
[4] LLM Verification: Query có đề cập đến 1 môn cụ thể?
  ↓
  ├─ YES → [5a] Lấy TẤT CẢ JSON chunks của môn đó
  │         → LLM Generate Answer với full context
  │         → Trả về câu trả lời cho user
  │
  └─ NO  → [5b] Trả về multi-option cho user chọn
            → User chọn môn học
            → Lấy JSON chunks → Generate Answer
```

## Các thành phần chính

### 1. **Langchain Memory Management** (`langchain_memory.py`)

- **SessionMemory**: Quản lý conversation history cho 1 session
  - Sử dụng `ConversationBufferWindowMemory` (giữ N messages gần nhất)
  - Lưu trữ messages theo format Langchain (HumanMessage, AIMessage)
  - Track current subject đang được thảo luận
  
- **LangchainMemoryManager**: Quản lý multiple sessions
  - Map `session_id` → `SessionMemory`
  - Auto-create session khi chưa tồn tại

**API:**
```python
memory = memory_manager.get_or_create(session_id)
memory.add_message_pair(user_msg, ai_msg)
history = memory.get_history_as_list()  # List[Dict] format
langchain_msgs = memory.get_langchain_messages()  # Langchain format
```

### 2. **Query Refinement** (`llm_refiner.py`)

Sử dụng Langchain để viết lại câu hỏi dựa trên context từ conversation history.

**Ví dụ:**
- Lịch sử: 
  - User: "Môn Giải tích 2A có bao nhiêu tín chỉ?"
  - AI: "4 tín chỉ"
- Câu hỏi mới: "Giảng viên của nó là ai?"
- **Refined Query**: "Giảng viên của môn Giải tích 2A là ai?"

**API:**
```python
refiner = QueryRefiner()
refined = refiner.refine_query(query, langchain_messages)
```

### 3. **Adaptive Retriever** (`adaptive_retriever.py`)

**Flow chính:**

1. **Step 0**: Nếu `current_subject` được set (từ memory) → Trả lời trực tiếp
2. **Step 1**: Contextualize query (giải quyết đại từ)
3. **Step 2**: Hybrid Search (FAISS + BM25) → Lấy top 50 chunks
4. **Step 3**: Extract top 5 unique subjects
5. **Step 4**: LLM verify query có đề cập đến 1 môn cụ thể không?
6. **Step 5a/5b**: 
   - Match found → Lấy ALL chunks của môn đó → Generate answer
   - Ambiguous → Return candidates cho user

**Cải tiến:**
- Hỗ trợ `Optional[str]` cho `current_subject` và `chat_history`
- Section intent detection (grading, lecturer, materials, etc.)
- Sort chunks theo relevance với section intent

### 4. **Main API** (`main.py`)

**Endpoints chính:**

#### `POST /ask`
```json
{
  "question": "Cách tính điểm môn Giải tích 2A?",
  "session_id": "user123",
  "use_advanced": true
}
```

**Response (Match found):**
```json
{
  "answer": "Điểm tổng kết = ...",
  "sources": [...],
  "refined_query": "Cách tính điểm môn Giải tích 2A?",
  "search_method": "SPECIFIC_COURSE",
  "timing_ms": 1250.5
}
```

**Response (Ambiguous - need clarification):**
```json
{
  "answer": "Tôi tìm thấy các môn học sau...",
  "need_clarification": true,
  "candidates": [
    {"code": "MTH00012", "name": "Giải tích 2A"},
    {"code": "MTH00013", "name": "Giải tích 2B"},
    ...
  ]
}
```

#### `POST /clarify`
Khi user chọn môn học từ multi-option:

```json
{
  "session_id": "user123",
  "selected_code": "MTH00012",
  "original_question": "Cách tính điểm?"
}
```

**Response:**
```json
{
  "answer": "Điểm tổng kết = ...",
  "sources": [...],
  "selected_subject": "Giải tích 2A"
}
```

## Cài đặt

### 1. Install dependencies
```bash
cd POC
pip install -r requirements.txt
```

### 2. Cấu hình LLM
Sửa `backend/config.py`:
```python
LLM_BASE_URL = "https://your-llm-endpoint.com/v1"
LLM_API_KEY = "your-api-key"
LLM_MODEL = "glm-4.7-flash"
```

### 3. Index data (nếu chưa có)
```bash
cd POC
python script/chunking_script.py
python script/embedding_indexing_script.py
```

### 4. Run server
```bash
cd POC
python backend/main.py
```

Server sẽ chạy tại `http://0.0.0.0:7860`

## Flow ví dụ

### Scenario 1: User hỏi về 1 môn cụ thể

**Request:**
```
POST /ask
{"question": "Giảng viên môn Giải tích 2A là ai?", "session_id": "abc123"}
```

**Backend xử lý:**
1. Refine query: "Giảng viên môn Giải tích 2A là ai?" (không đổi vì đã rõ)
2. Hybrid search → Top 5 subjects: ["Giải tích 2A", "Giải tích 2B", ...]
3. LLM verify: Match found = "MTH00012" (Giải tích 2A)
4. Lấy ALL chunks của MTH00012
5. Generate answer với full context

**Response:**
```json
{
  "answer": "Giảng viên môn Giải tích 2A là...",
  "search_method": "SPECIFIC_COURSE"
}
```

### Scenario 2: User hỏi mơ hồ

**Request:**
```
POST /ask
{"question": "Cách tính điểm môn giải tích?", "session_id": "abc123"}
```

**Backend xử lý:**
1. Hybrid search → Top 5: ["Giải tích 1", "Giải tích 2A", "Giải tích 2B", ...]
2. LLM verify: Ambiguous (nhiều môn giải tích)
3. Return candidates

**Response:**
```json
{
  "need_clarification": true,
  "candidates": [
    {"code": "MTH00011", "name": "Giải tích 1"},
    {"code": "MTH00012", "name": "Giải tích 2A"},
    ...
  ]
}
```

**Frontend hiển thị multi-option:**
```
Bạn đang muốn hỏi về môn nào?
○ Giải tích 1 (MTH00011)
○ Giải tích 2A (MTH00012)
○ Giải tích 2B (MTH00013)
```

**User chọn → Frontend gọi:**
```
POST /clarify
{"session_id": "abc123", "selected_code": "MTH00012", "original_question": "Cách tính điểm?"}
```

**Backend:**
1. Set `current_subject = MTH00012` vào memory
2. Lấy ALL chunks của MTH00012
3. Generate answer

### Scenario 3: Follow-up questions

**Conversation:**
```
User: "Môn Giải tích 2A có bao nhiêu tín chỉ?"
AI: "4 tín chỉ"

User: "Giảng viên của nó là ai?"
```

**Backend xử lý:**
1. Refine query: "Giảng viên của nó là ai?" → "Giảng viên của môn Giải tích 2A là ai?"
2. Memory đã có `current_subject = MTH00012` → Skip search, trả lời trực tiếp
3. Generate answer với ALL chunks của MTH00012

## Ưu điểm của kiến trúc mới

✅ **Langchain Integration**: Chuẩn hóa memory management, dễ mở rộng  
✅ **Query Refinement**: Hiểu context tốt hơn, giải quyết đại từ  
✅ **Subject Verification**: LLM verify trước khi retrieve → Chính xác cao  
✅ **Full Context**: Lấy ALL chunks khi biết môn học → Câu trả lời đầy đủ  
✅ **Multi-option UX**: User chọn khi ambiguous → Trải nghiệm tốt hơn  
✅ **Session Memory**: Track conversation → Follow-up questions tự nhiên  

## Troubleshooting

### Lỗi: "Retriever not initialized"
- Chạy indexing script trước: `python script/embedding_indexing_script.py`
- Check file `POC/index/faiss.index` và `POC/index/chunks.json` có tồn tại

### Lỗi: Langchain import error
```bash
pip install langchain langchain-openai langchain-core
```

### LLM connection timeout
- Kiểm tra `LLM_BASE_URL` trong `config.py`
- Tăng `LLM_TIMEOUT` nếu cần

## Tham khảo

- Langchain Docs: https://python.langchain.com/docs/
- FastAPI Docs: https://fastapi.tiangolo.com/
- Sentence Transformers: https://www.sbert.net/
