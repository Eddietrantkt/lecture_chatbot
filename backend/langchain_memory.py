"""
Langchain-based Conversation Memory Manager
Manages chat history using Langchain's memory components
"""
from typing import List, Dict, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
import logging

logger = logging.getLogger("LangchainMemory")


class SessionMemory:
    """
    Manages conversation history for a single session using Langchain.
    Features:
    - Buffer window (keep last N messages)
    - Subject tracking (remember current subject being discussed)
    - Langchain-compatible message history
    """
    
    def __init__(self, max_messages: int = 10):
        self.max_messages = max_messages
        
        # Langchain message history (simple buffer)
        self.chat_history = InMemoryChatMessageHistory()
        
        # Additional tracking
        self.current_subject_code: Optional[str] = None
        self.current_subject_name: Optional[str] = None
        
    def add_user_message(self, content: str):
        """Add user message to history"""
        self.chat_history.add_user_message(content)
        self._trim_history()
        
    def add_ai_message(self, content: str):
        """Add AI message to history"""
        self.chat_history.add_ai_message(content)
        self._trim_history()
    
    def add_message_pair(self, user_msg: str, ai_msg: str):
        """Add a complete user-ai message pair"""
        self.chat_history.add_user_message(user_msg)
        self.chat_history.add_ai_message(ai_msg)
        self._trim_history()
    
    def _trim_history(self):
        """Keep only the last max_messages"""
        messages = self.chat_history.messages
        if len(messages) > self.max_messages:
            # Keep only last N messages
            self.chat_history.messages = messages[-self.max_messages:]
    
    def get_history_as_list(self) -> List[Dict[str, str]]:
        """Get conversation history as list of dicts (compatible with OpenAI format)"""
        messages = []
        for msg in self.chat_history.messages:
            if isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages.append({"role": "assistant", "content": msg.content})
        return messages
    
    def get_langchain_messages(self) -> List[BaseMessage]:
        """Get Langchain-format messages"""
        return list(self.chat_history.messages)
    
    def get_memory_variables(self) -> Dict:
        """Get memory variables (compatibility method)"""
        return {"chat_history": self.get_langchain_messages()}
    
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
        self.chat_history.clear()
        self.current_subject_code = None
        self.current_subject_name = None


class LangchainMemoryManager:
    """
    Manages multiple conversation sessions using Langchain.
    Key = session_id (from frontend)
    """
    def __init__(self, max_messages_per_session: int = 10):
        self.sessions: Dict[str, SessionMemory] = {}
        self.max_messages = max_messages_per_session
        logger.info("LangchainMemoryManager initialized")
    
    def get_or_create(self, session_id: str) -> SessionMemory:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionMemory(self.max_messages)
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
