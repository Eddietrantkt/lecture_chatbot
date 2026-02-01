# University Course Q&A System

Hệ thống hỏi đáp thông tin học phần sử dụng RAG (Retrieval-Augmented Generation).

## Cấu trúc dự án

- **backend/**: Mã nguồn xử lý chính (Python/FastAPI)
    - `main.py`: API Server
    - `adaptive_retriever.py`: Logic tìm kiếm thông minh
    - `llm_interface.py`: Kết nối LLM (OpenRouter)
    - `subject_manager.py`: Quản lý thông tin môn học
- **frontend/**: Giao diện người dùng (React/Vite)
- **script/**: Các script tiện ích (Indexing, Data processing)
    - `embedding_indexing_script.py`: Tạo index dữ liệu
    - `chunking_script.py`: Chia nhỏ dữ liệu
- **demo/**: Các file demo/test
    - `search_demo.py`: Demo tìm kiếm
    - `adaptive_search_demo.py`: Demo tìm kiếm nâng cao
- **BM_.../**: Dữ liệu JSON các bộ môn

## Cài đặt & Chạy

### 1. Backend

Yêu cầu Python 3.8+

```bash
# Cài đặt dependencies
pip install fastapi uvicorn openai sentence-transformers faiss-cpu rank-bm25 numpy

# Chạy Server (tại thư mục gốc)
python backend/main.py
# Server sẽ chạy tại http://localhost:7860
```

### 2. Frontend

Yêu cầu Node.js 16+

```bash
cd frontend
npm install
npm run dev
# App sẽ chạy tại http://localhost:5173
```

## Lưu ý

- Đảm bảo đã cập nhật API Key trong `backend/llm_interface.py` hoặc biến môi trường `OPENROUTER_API_KEY`.
- Nếu chưa có index, chạy `python script/embedding_indexing_script.py` để tạo index trước.
