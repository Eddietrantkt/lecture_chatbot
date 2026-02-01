# Changelog - Backend Refactor với Langchain

## Tổng quan

Backend đã được refactor hoàn toàn để implement logic mới theo yêu cầu:

```
User Query → LLM Refine Query → Retrieval → Top 5 Subjects → LLM Verification
  → Match: Generate với full JSON context
  → No Match: Multi-option cho user chọn
```

## Files mới được tạo

### 1. `backend/langchain_memory.py` (NEW)
**Mục đích**: Thay thế `memory.py` bằng Langchain memory management

**Classes:**
- `SessionMemory`: 
  - Sử dụng `ConversationBufferWindowMemory` từ Langchain
  - Lưu messages theo format Langchain (HumanMessage, AIMessage)
  - Track current subject đang thảo luận
  
- `LangchainMemoryManager`:
  - Quản lý multiple sessions (session_id → SessionMemory)
  - Auto-create sessions

**API:**
```python
memory = memory_manager.get_or_create(session_id)
memory.add_message_pair(user_msg, ai_msg)
history = memory.get_history_as_list()  # OpenAI format
langchain_msgs = memory.get_langchain_messages()  # Langchain format
```

### 2. `backend/llm_refiner.py` (NEW)
**Mục đích**: Query refinement với Langchain

**Features:**
- Sử dụng `ChatPromptTemplate` với `MessagesPlaceholder` cho history
- Resolve pronouns: "nó", "môn đó" → tên cụ thể
- Bổ sung context từ conversation history
- Temperature = 0.1 để output consistent

**Example:**
```
History: "Môn Giải tích 2A có bao nhiêu tín chỉ?" → "4 tín chỉ"
Query: "Giảng viên của nó là ai?"
→ Refined: "Giảng viên của môn Giải tích 2A là ai?"
```

### 3. `test_backend_flow.py` (NEW)
**Mục đích**: Test script demo 3 scenarios

**Scenarios:**
1. **Specific subject**: Query rõ ràng → LLM verify match → Generate
2. **Ambiguous**: Query mơ hồ → Need clarification → User chọn → Generate
3. **Follow-up**: Conversation với memory → Query refinement → Generate

**Usage:**
```bash
cd POC
python test_backend_flow.py
```

### 4. `BACKEND_README.md` (NEW)
**Mục đích**: Documentation đầy đủ về kiến trúc mới

**Nội dung:**
- Flow diagram
- API documentation
- Installation guide
- Examples cho từng scenario
- Troubleshooting

## Files đã được update

### 1. `backend/main.py`
**Thay đổi:**

✅ Import Langchain components:
```python
from backend.langchain_memory import LangchainMemoryManager
from backend.llm_refiner import QueryRefiner
```

✅ Initialize query_refiner trong startup:
```python
query_refiner = QueryRefiner()
memory_manager = LangchainMemoryManager(...)
```

✅ `/ask` endpoint - Thêm query refinement:
```python
# Refine query using Langchain
if query_refiner and len(history) > 0:
    langchain_messages = memory.get_langchain_messages()
    refined_query = query_refiner.refine_query(question, langchain_messages)

# Use refined query for search
result = retriever.search_and_answer(
    refined_query,  # ← Changed
    top_k=5,
    chat_history=history,
    current_subject=current_subject
)

# Update memory với Langchain format
memory.add_message_pair(question, answer)
```

✅ Response include refined query:
```python
response_payload = {
    ...
    "refined_query": refined_query  # NEW field
}
```

✅ `/clarify` endpoint - Thêm subject display name:
```python
# Get subject info
subject_info = retriever.subject_manager.get_subject_by_code(selected_code)
subject_name = subject_info.name if subject_info else selected_code

# Set subject in memory
memory.set_subject(selected_code, subject_name)

# Return selected subject
return {
    ...
    "selected_subject": subject_name  # NEW field
}
```

### 2. `backend/adaptive_retriever.py`
**Thay đổi:**

✅ Fix type hints để hỗ trợ Optional:
```python
def search_and_answer(
    self,
    query: str,
    top_k: int = 5,
    chat_history: Optional[List[Dict[str, str]]] = None,  # ← Changed
    current_subject: Optional[str] = None  # ← Changed
) -> Dict[str, Any]:
```

✅ Fix `_answer_with_subject`:
```python
def _answer_with_subject(
    self,
    query: str,
    subject_code: str,
    section_intent: Optional[str] = None  # ← Changed
) -> Dict[str, Any]:
```

✅ Step 0 - Thêm section intent detection khi dùng current_subject:
```python
if current_subject:
    section_intent = self._detect_section_intent(query)  # NEW
    return self._answer_with_subject(query, current_subject, section_intent)
```

**Logic flow không đổi:**
- Step 1: Contextualize query (LLM)
- Step 2: Hybrid search
- Step 3: Extract top 5 subjects
- Step 4: LLM verification
- Step 5a/5b: Generate hoặc return candidates

### 3. `requirements.txt`
**Thay đổi:**

✅ Thêm Langchain dependencies:
```txt
# Langchain for Memory Management and Query Refinement
langchain>=0.1.0
langchain-openai>=0.0.5
langchain-core>=0.1.0
```

## Migration Guide

### Để chạy backend mới:

1. **Cài đặt dependencies mới:**
```bash
cd POC
pip install -r requirements.txt
```

2. **Kiểm tra config:**
- File `backend/config.py` đã có sẵn LLM settings
- Đảm bảo `LLM_BASE_URL` và `LLM_API_KEY` đúng

3. **Run server:**
```bash
python backend/main.py
```

4. **Test flow:**
```bash
python test_backend_flow.py
```

### Backward Compatibility

✅ **API endpoints không đổi:**
- `POST /ask` - vẫn nhận cùng request format
- `POST /clarify` - vẫn nhận cùng request format
- Response thêm fields mới (`refined_query`, `selected_subject`) nhưng không breaking

✅ **Session ID vẫn hoạt động:**
- Frontend không cần thay đổi gì
- Session memory tự động migrate sang Langchain format

### Breaking Changes

⚠️ **Old memory.py không còn được sử dụng:**
- Nếu code cũ import `from backend.memory import MemoryManager`
- Cần đổi thành `from backend.langchain_memory import LangchainMemoryManager`

⚠️ **Memory API thay đổi:**
```python
# OLD
memory.add_message("user", content)
memory.add_message("assistant", content)

# NEW  
memory.add_message_pair(user_content, ai_content)
# hoặc
memory.add_user_message(content)
memory.add_ai_message(content)
```

## Key Improvements

### 1. Query Refinement
**Before:** 
- `contextualize_query()` trong `llm_interface.py` dùng JSON.dumps cho history
- Không tận dụng Langchain prompting

**After:**
- Dedicated `QueryRefiner` class với Langchain
- Sử dụng `ChatPromptTemplate` + `MessagesPlaceholder`
- Prompts được tối ưu cho Vietnamese
- Retry logic tốt hơn

### 2. Memory Management
**Before:**
- Custom `ConversationMemory` class
- Lưu messages dạng list of dicts
- Không integrate với Langchain ecosystem

**After:**
- Sử dụng `ConversationBufferWindowMemory` (Langchain built-in)
- Hỗ trợ cả OpenAI format (dict) và Langchain format (Messages)
- Dễ mở rộng với các Langchain tools khác (agents, chains, etc.)

### 3. Type Safety
**Before:**
- `chat_history: List[Dict[str, str]] = None` (LSP warning)
- `current_subject: str = None` (LSP warning)

**After:**
- `chat_history: Optional[List[Dict[str, str]]] = None`
- `current_subject: Optional[str] = None`
- Proper type hints

### 4. Documentation
**Before:**
- Docstrings cơ bản
- Không có hướng dẫn deployment

**After:**
- Full README với flow diagrams
- API documentation
- Test script với examples
- Migration guide

## Testing

### Manual Testing
1. Start server: `python backend/main.py`
2. Run test script: `python test_backend_flow.py`
3. Check 3 scenarios pass

### Expected Behavior

**Scenario 1 - Specific Subject:**
```
Input: "Giảng viên môn Giải tích 2A là ai?"
→ LLM verify: Match = "MTH00012"
→ Generate answer với ALL chunks của MTH00012
→ Response: { "search_method": "SPECIFIC_COURSE" }
```

**Scenario 2 - Ambiguous:**
```
Input: "Cách tính điểm môn giải tích?"
→ LLM verify: No match (nhiều môn giải tích)
→ Return candidates: [Giải tích 1, 2A, 2B, ...]
→ Response: { "need_clarification": true, "candidates": [...] }

User chọn → POST /clarify
→ Generate answer với ALL chunks của môn được chọn
```

**Scenario 3 - Follow-up:**
```
Q1: "Môn Giải tích 2A có bao nhiêu tín chỉ?"
A1: "4 tín chỉ"
→ Memory: Set current_subject = "MTH00012"

Q2: "Giảng viên của nó là ai?"
→ Refine: "Giảng viên của môn Giải tích 2A là ai?"
→ Skip search (current_subject already set)
→ Generate answer với chunks của MTH00012
```

## Next Steps

### Recommended Enhancements

1. **Streaming Response:**
   - Implement streaming cho LLM generation
   - Cải thiện UX khi answer dài

2. **Caching:**
   - Cache refined queries
   - Cache subject verifications

3. **Analytics:**
   - Log refined queries vs original
   - Track clarification rate
   - Monitor LLM verification accuracy

4. **Advanced Memory:**
   - `ConversationSummaryMemory` cho long conversations
   - `VectorStoreRetrieverMemory` để recall long-term context

5. **Multi-Agent:**
   - Tách subject verification thành separate agent
   - Grading calculator agent
   - Schedule parser agent

## Troubleshooting

### Issue: "Module 'langchain' has no attribute..."
**Solution:**
```bash
pip install --upgrade langchain langchain-openai langchain-core
```

### Issue: Query refinement không hoạt động
**Check:**
1. LLM_BASE_URL có đúng không?
2. LLM có hỗ trợ `ChatPromptTemplate` format không?
3. Check logs: `logger.info(f"Query refined: ...")`

### Issue: Memory không persist
**Expected:** Memory chỉ persist trong runtime, không lưu vào database
**Solution:** Implement Redis/PostgreSQL-backed memory nếu cần

## Files Structure Summary

```
POC/
├── backend/
│   ├── main.py                    # ✏️ UPDATED (Langchain integration)
│   ├── adaptive_retriever.py      # ✏️ UPDATED (Type hints)
│   ├── langchain_memory.py        # ✨ NEW (Langchain memory)
│   ├── llm_refiner.py             # ✨ NEW (Query refinement)
│   ├── llm_interface.py           # ⚪ No changes
│   ├── subject_manager.py         # ⚪ No changes
│   └── config.py                  # ⚪ No changes
├── requirements.txt               # ✏️ UPDATED (Add langchain)
├── test_backend_flow.py           # ✨ NEW (Test script)
├── BACKEND_README.md              # ✨ NEW (Documentation)
└── CHANGELOG.md                   # ✨ NEW (This file)
```

## Credits

Refactored by: OpenCode Assistant  
Date: 2026-01-28  
Framework: Langchain v0.1+  
