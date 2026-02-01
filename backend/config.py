"""
Centralized Configuration for Backend
"""
import os

class Config:
    # --- LLM Settings (Cloudflare Tunnel) ---
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://along-climbing-clearing-looked.trycloudflare.com/v1")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "my_secret_token_123")
    LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
    LLM_TIMEOUT = 120.0
    LLM_MAX_RETRIES = 3
    
    # --- Memory Settings ---
    MEMORY_MAX_MESSAGES = 10  # Số messages tối đa giữ trong memory
    
    # --- Retrieval Settings ---
    TOP_K_SEARCH = 5  # Số candidates lấy từ hybrid search
    TOP_K_SUBJECTS = 5  # Số subjects đưa cho LLM verify
    SIMILARITY_THRESHOLD = 0.35
    HYBRID_ALPHA = 0.8  # FAISS weight 80% (semantic search chiếm ưu thế)
    
    # --- Paths ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INDEX_DIR = os.path.join(BASE_DIR, "index")
    CHUNKS_FILE = os.path.join(INDEX_DIR, "chunks.json")
