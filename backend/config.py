"""
Centralized Configuration for Backend
"""
import os
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

class Config:
    # --- LLM Settings (Remote vLLM via tunnel by default) ---
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://penguin-architects-sie-descending.trycloudflare.com/v1")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "my_secret_token_123")
    LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
    LLM_TIMEOUT = 120.0
    LLM_MAX_RETRIES = 3

    # --- Embedding Settings ---
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "microsoft/harrier-oss-v1-270m")
    EMBEDDING_QUERY_PROMPT_NAME = os.getenv("EMBEDDING_QUERY_PROMPT_NAME", "web_search_query")
    EMBEDDING_MAX_SEQ_LENGTH = int(os.getenv("EMBEDDING_MAX_SEQ_LENGTH", "1024"))
    
    # --- Memory Settings ---
    MEMORY_MAX_MESSAGES = 10  # Số messages tối đa giữ trong memory
    
    # --- Retrieval Settings ---
    TOP_K_SEARCH = 50  # Số candidates lấy từ hybrid search (FIXED: was 5, should be 50)
    TOP_K_SUBJECTS = 5  # Số subjects đưa cho LLM verify
    SIMILARITY_THRESHOLD = 0.35
    HYBRID_ALPHA = 0.8  # FAISS weight 80% (semantic search chiếm ưu thế)

    # --- Domain Settings ---
    DOMAIN_KEYWORDS = {
        "major": ["ngành", "chuyên ngành", "cử nhân", "chương trình đào tạo"],
        "subject": ["môn", "học phần", "môn học", "khóa học"]
    }
    
    # --- Paths ---
    BASE_DIR = BASE_DIR
    INDEX_DIR = os.path.join(BASE_DIR, "index")
    CHUNKS_FILE = os.path.join(INDEX_DIR, "chunks.json")
    KNOWLEDGE_GRAPH_DIR = os.path.join(INDEX_DIR, "knowledge_graph")
