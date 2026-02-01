"""
Backend API for Course Syllabus Q&A
Refactored with session-based memory management.
"""
import os
import sys
import uvicorn
import time
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import json

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("API")

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.adaptive_retriever import AdaptiveRetriever
from backend.llm_interface import LLMInterface
from backend.langchain_memory import LangchainMemoryManager
from backend.config import Config

# Initialize FastAPI
app = FastAPI(
    title="Course Syllabus Q&A API", 
    description="Backend for University Course Q&A with Memory Management"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Components ---
retriever = None
llm = None
memory_manager = None


@app.on_event("startup")
async def startup_event():
    global retriever, llm, memory_manager
    logger.info(f"Loading resources from {Config.BASE_DIR}...")
    
    # Initialize Langchain Memory Manager
    memory_manager = LangchainMemoryManager(max_messages_per_session=Config.MEMORY_MAX_MESSAGES)
    
    # Initialize LLM
    llm = LLMInterface()
    
    # Initialize Retriever
    try:
        retriever = AdaptiveRetriever(Config.INDEX_DIR, Config.CHUNKS_FILE)
        logger.info("Retriever initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing retriever: {e}")


# --- Pydantic Models ---

class ChatMessage(BaseModel):
    role: str
    content: str

class QuestionRequest(BaseModel):
    question: str
    session_id: str = "default"  # Session ID for memory tracking
    use_advanced: bool = True
    model_mode: str = 'detail'
    chat_history: List[ChatMessage] = []  # Legacy support
    previous_context: Optional[str] = None

class FeedbackRequest(BaseModel):
    query: str
    answer: str
    context: List[Dict[str, str]]
    status: str
    comment: Optional[str] = None

class SuggestRequest(BaseModel):
    question: str
    answer: str
    max_questions: int = 3

class ClarifyRequest(BaseModel):
    session_id: str = "default"
    selected_code: str  # The course code user selected
    original_question: str


# --- Endpoints ---

@app.get("/health")
async def health_check():
    return {
        "status": "ok", 
        "models_loaded": retriever is not None,
        "total_chunks": len(retriever.retriever.chunks) if retriever and retriever.retriever else 0,
        "active_sessions": memory_manager.get_session_count() if memory_manager else 0
    }

@app.get("/stats")
async def get_stats():
    if not retriever:
        return {"total_chunks": 0}
    
    return {
        "total_chunks": len(retriever.retriever.chunks),
        "models": {
            "embedder": "sentence-transformers",
            "llm": Config.LLM_MODEL
        },
        "active_sessions": memory_manager.get_session_count() if memory_manager else 0
    }


# --- Auth Endpoint (Mock) ---
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == "admin" and form_data.password == "admin123":
        return {"access_token": "demo-token-123", "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Tài khoản hoặc mật khẩu không chính xác")


@app.post("/ask")
async def ask_question(request: QuestionRequest):
    """
    Main Q&A endpoint with Langchain-based session memory and query refinement.
    
    Flow:
    1. Lấy session memory (Langchain)
    2. Refine query với context từ history
    3. Hybrid search -> Top 5 subjects
    4. LLM verification
    5a. Match found -> Generate answer với full JSON context
    5b. Ambiguous -> Return candidates cho user chọn
    """
    logger.info(f"[Session: {request.session_id}] Query: '{request.question}'")
    
    if not retriever:
        logger.error("Retriever is not initialized!")
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    start_time = time.time()
    
    # Get or create session memory (Langchain)
    memory = memory_manager.get_or_create(request.session_id)
    
    # Get conversation history as list (for backward compatibility)
    history = memory.get_history_as_list()
    
    # Refine query using LLM contextualize
    refined_query = request.question
    if llm and llm.enabled and len(history) > 0:
        refined_query = llm.contextualize_query(request.question, history)
        logger.info(f"Query refined: '{request.question}' -> '{refined_query}'")
    
    # Get current subject from memory (for follow-up questions)
    current_subject = memory.get_current_subject()
    
    # Search and Answer
    result = retriever.search_and_answer(
        refined_query,  # Use refined query
        top_k=5, 
        chat_history=history,
        current_subject=current_subject
    )
    
    # Update memory with this Q&A (Langchain format)
    memory.add_message_pair(request.question, result.get("answer", ""))
    
    # Track subject if matched
    if result.get("matched_code"):
        subjects = result.get("subjects", [])
        subject_name = subjects[0] if subjects else result["matched_code"]
        memory.set_subject(result["matched_code"], subject_name)
    
    # Format response for Frontend
    sources = []
    for src in result.get("sources", []):
        chunk = src.get('chunk', src)
        sources.append({
            "source": chunk.get("course_name", "Unknown"),
            "content": chunk.get("text", "")
        })
    
    total_ms = (time.time() - start_time) * 1000
    
    response_payload = {
        "answer": result.get("answer", ""),
        "sources": sources,
        "pdf_sources": [],
        "search_mode": "hybrid",
        "search_method": result.get("intent", "GENERAL"),
        "timing": {
            "total_ms": total_ms,
            "status": "success"
        },
        "timing_ms": total_ms,
        "refined_query": refined_query  # Include refined query for transparency
    }
    
    # Add candidates if ambiguous (needs clarification)
    if result.get("need_clarification"):
        response_payload["candidates"] = result["candidates"]
        response_payload["need_clarification"] = True
        
    return response_payload


@app.post("/clarify")
async def clarify_subject(request: ClarifyRequest):
    """
    Handle user clarification when multiple subjects were found.
    User selected a specific subject from candidates.
    
    Flow:
    - User chọn môn học từ multi-option
    - Lấy tất cả JSON chunks của môn đó
    - Generate answer với full context
    """
    logger.info(f"[Session: {request.session_id}] Clarified: {request.selected_code}")
    
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    start_time = time.time()
    
    # Get memory and set the selected subject
    memory = memory_manager.get_or_create(request.session_id)
    
    # Get subject info for display name
    subject_info = retriever.subject_manager.get_subject_by_code(request.selected_code)
    subject_name = subject_info.name if subject_info else request.selected_code
    memory.set_subject(request.selected_code, subject_name)
    
    # Answer with the selected subject (using ALL JSON chunks)
    result = retriever._answer_with_subject(request.original_question, request.selected_code)
    
    # Update memory with Langchain format
    memory.add_message_pair(request.original_question, result.get("answer", ""))
    
    # Format response
    sources = []
    for src in result.get("sources", []):
        chunk = src.get('chunk', src)
        sources.append({
            "source": chunk.get("course_name", "Unknown"),
            "content": chunk.get("text", "")
        })
    
    total_ms = (time.time() - start_time) * 1000
    
    return {
        "answer": result.get("answer", ""),
        "sources": sources,
        "search_method": "SPECIFIC_COURSE",
        "timing_ms": total_ms,
        "selected_subject": subject_name
    }


@app.post("/suggest-questions")
async def suggest_questions(request: SuggestRequest):
    if not llm or not llm.enabled:
        return {"questions": []}
        
    prompt = f"""
Based on the following Q&A about university courses, suggest {request.max_questions} short, relevant follow-up questions a student might ask.

User Question: {request.question}
AI Answer: {request.answer}

Return ONLY a JSON array of strings in VIETNAMESE. Example: ["Câu hỏi 1?", "Câu hỏi 2?"]
"""
    
    try:
        content = llm._call_with_retry([{"role": "user", "content": prompt}])
        if content:
            # Try to parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            questions_json = json.loads(content)
            if isinstance(questions_json, list):
                return {"questions": questions_json}
            elif isinstance(questions_json, dict) and "questions" in questions_json:
                return {"questions": questions_json["questions"]}
    except Exception as e:
        logger.error(f"Error suggesting questions: {e}")
    
    return {"questions": []}


@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Log feedback to file."""
    feedback_file = os.path.join(Config.BASE_DIR, "feedback.jsonl")
    with open(feedback_file, "a", encoding="utf-8") as f:
        json.dump(request.dict(), f, ensure_ascii=False)
        f.write("\n")
    return {"success": True, "message": "Feedback received"}


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session."""
    if memory_manager:
        deleted = memory_manager.delete_session(session_id)
        return {"success": deleted, "session_id": session_id}
    return {"success": False, "error": "Memory manager not initialized"}


@app.get("/api/pdf-file/{domain_id}/{filename}")
async def get_pdf(domain_id: str, filename: str):
    """Placeholder for PDF files."""
    raise HTTPException(status_code=404, detail="PDF file not found")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
