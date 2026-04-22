"""
LLM Query Refiner using Langchain
Handles query refinement/contextualization with conversation history
"""
import logging
from typing import List, Dict, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory

from backend.config import Config

logger = logging.getLogger("QueryRefiner")


class QueryRefiner:
    """
    Refines user queries based on conversation history using Langchain.
    """
    
    def __init__(self):
        # Initialize Langchain ChatOpenAI with custom config
        self.llm = ChatOpenAI(
            base_url=Config.LLM_BASE_URL,
            api_key=Config.LLM_API_KEY,
            model=Config.LLM_MODEL,
            temperature=0.1,
            timeout=Config.LLM_TIMEOUT,
            extra_body={
                "top_k": 20,
                "chat_template_kwargs": {"enable_thinking": False}
            }
        )
        
        # Create prompt template for query refinement
        self.refine_prompt = ChatPromptTemplate.from_messages([
            ("system", """Bạn là một trợ lý thông minh giúp làm rõ câu hỏi của sinh viên.

Nhiệm vụ: Dựa vào lịch sử hội thoại, hãy viết lại câu hỏi mới nhất thành một câu hỏi độc lập, đầy đủ ngữ cảnh.

Nguyên tắc:
1. Giải quyết các đại từ: "nó", "môn đó", "thầy ấy" -> thay bằng tên cụ thể từ lịch sử
2. Bổ sung ngữ cảnh từ câu hỏi trước nếu cần
3. Nếu câu hỏi đã rõ ràng, giữ nguyên
4. Luôn trả lời bằng TIẾNG VIỆT
5. KHÔNG trả lời câu hỏi, CHỈ viết lại câu hỏi

Ví dụ:
- Lịch sử: "Môn Giải tích 2A có bao nhiêu tín chỉ?" -> "4 tín chỉ"
  Câu hỏi mới: "Giảng viên của nó là ai?"
  Viết lại: "Giảng viên của môn Giải tích 2A là ai?"
  
- Câu hỏi: "Cách tính điểm môn Cấu trúc dữ liệu?"
  Viết lại: "Cách tính điểm môn Cấu trúc dữ liệu?" (đã rõ ràng)
"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", "Câu hỏi cần viết lại: {question}")
        ])
        
        # Create chain
        self.refine_chain = self.refine_prompt | self.llm
        
        logger.info("QueryRefiner initialized with Langchain")
    
    def refine_query(
        self, 
        query: str, 
        history_messages: List[BaseMessage]
    ) -> str:
        """
        Refine query based on conversation history.
        
        Args:
            query: Current user question
            history_messages: List of Langchain messages (HumanMessage, AIMessage)
            
        Returns:
            Refined query string
        """
        if not history_messages or len(history_messages) == 0:
            # No history, return original query
            return query
        
        try:
            # Only use last 6 messages (3 turns) for efficiency
            recent_history = history_messages[-6:] if len(history_messages) > 6 else history_messages
            
            # Invoke chain
            response = self.refine_chain.invoke({
                "question": query,
                "history": recent_history
            })
            
            refined = response.content.strip()
            if "</think>" in refined:
                refined = refined.split("</think>", 1)[1].strip()
            
            if refined and len(refined) > 0:
                logger.info(f"Query refined: '{query}' -> '{refined}'")
                return refined
            else:
                logger.warning("Refinement returned empty, using original")
                return query
                
        except Exception as e:
            logger.error(f"Error refining query: {e}")
            return query
    
    def refine_query_from_dict_history(
        self, 
        query: str, 
        history: List[Dict[str, str]]
    ) -> str:
        """
        Refine query from dict-format history (backward compatibility).
        
        Args:
            query: Current user question
            history: List of {"role": "user/assistant", "content": "..."}
            
        Returns:
            Refined query string
        """
        # Convert dict history to Langchain messages
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        return self.refine_query(query, messages)
