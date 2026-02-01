"""
Conversation Memory Manager
Manages chat history and subject tracking for sessions.
"""
from typing import List, Dict, Optional
import logging

logger = logging.getLogger("Memory")


class ConversationMemory:
    """
    Manages conversation history for a single session.
    Features:
    - Buffer window (keep last N messages)
    - Subject tracking (remember current subject being discussed)
    """
    
    def __init__(self, max_messages: int = 10):
        self.messages: List[Dict[str, str]] = []
        self.current_subject_code: Optional[str] = None
        self.current_subject_name: Optional[str] = None
        self.max_messages = max_messages
    
    def add_message(self, role: str, content: str):
        """Add message and trim if exceeds max"""
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get a copy of conversation history"""
        return self.messages.copy()
    
    def set_subject(self, code: str, name: str = None):
        """Track the current subject being discussed"""
        self.current_subject_code = code
        self.current_subject_name = name
        logger.debug(f"Subject set: {name} ({code})")
    
    def get_current_subject(self) -> Optional[str]:
        """Get current subject code"""
        return self.current_subject_code
    
    def clear(self):
        """Clear all memory"""
        self.messages = []
        self.current_subject_code = None
        self.current_subject_name = None


class MemoryManager:
    """
    Manages multiple conversation sessions.
    Key = session_id (from frontend)
    """
    def __init__(self, max_messages_per_session: int = 10):
        self.sessions: Dict[str, ConversationMemory] = {}
        self.max_messages = max_messages_per_session
        logger.info("MemoryManager initialized")
    
    def get_or_create(self, session_id: str) -> ConversationMemory:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationMemory(self.max_messages)
            logger.info(f"New session created: {session_id}")
        return self.sessions[session_id]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session, returns True if existed"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session deleted: {session_id}")
            return True
        return False
    
    def get_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.sessions)
