"""
LLM Interface for Self-Hosted Model via Ngrok
Refactored with centralized config and retry logic.
"""
import os
import json
import time
import re
from openai import OpenAI
from typing import List, Dict, Any, Optional

import logging

from backend.config import Config

logger = logging.getLogger("LLM")


class LLMInterface:
    def __init__(self):
        # Load from centralized config
        self.base_url = Config.LLM_BASE_URL
        self.api_key = Config.LLM_API_KEY
        self.model = Config.LLM_MODEL
        self.timeout = Config.LLM_TIMEOUT
        self.max_retries = Config.LLM_MAX_RETRIES
        
        logger.info(f"Initializing LLM connection to {self.base_url}...")
        
        try:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                default_headers={"ngrok-skip-browser-warning": "true"},
                timeout=self.timeout
            )
            self.enabled = True
            logger.info(f"LLM initialized successfully with model: {self.model}")
        except Exception as e:
            logger.error(f"Error configuring LLM: {e}")
            self.enabled = False

    def _call_with_retry(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = None) -> Optional[str]:
        """
        Call LLM with exponential backoff retry logic.
        Returns response content or None on failure.
        """
        for attempt in range(self.max_retries):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                    
                response = self.client.chat.completions.create(**kwargs)
                if response and response.choices:
                    return response.choices[0].message.content
                return None
            except Exception as e:
                wait_time = 2 ** attempt
                logger.warning(f"LLM call failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All retries failed: {e}")
                    return None
        return None

    def generate_answer(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Generate answer based on context chunks."""
        if not self.enabled:
            return "LLM integration is not enabled. Please check your configuration."
        
        # Build context from chunks
        context_text = ""
        for i, chunk in enumerate(context_chunks):
            source = chunk.get('course_name', 'Unknown Source')
            content = chunk.get('text', '')
            context_text += f"Source {i+1} ({source}):\n{content}\n\n"
        
        prompt = f"""
Bạn là một trợ lý giảng dạy nhiệt tình và hữu ích. Hãy sử dụng thông tin từ các đoạn văn bản trong đề cương môn học được cung cấp dưới đây để trả lời câu hỏi của sinh viên.

**Yêu cầu quan trọng:**
1. **Trả lời bằng TIẾNG VIỆT**.
2. **Ngắn gọn và đúng trọng tâm**: Trình bày thông tin súc tích, tránh viết quá dài dòng. Ưu tiên tóm tắt các ý chính.
3. **Trích xuất thông tin chính xác**: Đặc biệt chú ý đến các số liệu, phần trăm, trọng số điểm.
4. **Xác nhận môn học**: Bắt đầu câu trả lời bằng việc nhắc lại tên môn học đang được đề cập (Ví dụ: "Đối với môn [Tên Môn]...").
5. **Định dạng tối ưu**: 
   - KHÔNG sử dụng LaTeX (như \\[ \\], \\( \\)) hoặc các khối công thức phức tạp.
   - Thay vào đó, hãy viết công thức bằng văn bản thuần túy (Plain Text) một cách đơn giản nhất.
   - Ví dụ: "Điểm tổng kết = (Quá trình * 50%) + (Cuối kỳ * 50%)"
   - Sử dụng bảng hoặc danh sách gạch đầu dòng để dễ đọc.
5. Nếu thông tin không có trong ngữ cảnh, hãy nói rõ là bạn không tìm thấy thông tin trong tài liệu được cung cấp.

Ngữ cảnh (Context):
{context_text}

Câu hỏi: {query}
Câu trả lời:
"""
        content = self._call_with_retry([{"role": "user", "content": prompt}])
        
        if content:
            logger.info("LLM Generation complete.")
            return content
        
        # Fallback response
        logger.warning("Using fallback response due to LLM failure")
        fallback = "**[Lưu ý: Hệ thống đang quá tải, dưới đây là thông tin trích xuất thô]**\n\n"
        for i, chunk in enumerate(context_chunks[:3]):
            source = chunk.get('course_name', 'Unknown')
            text = chunk.get('text', '')[:300]
            fallback += f"- **{source}**: {text}...\n\n"
        return fallback

    def verify_subject_in_top5(self, query: str, subjects: List[Dict[str, str]]) -> Optional[str]:
        """
        Check if query refers to ONE specific subject from top 5.
        Uses string matching first, LLM only for ambiguous cases.
        
        Returns:
            course_code if match found, None if ambiguous
        """
        if not subjects:
            return None
        
        # === QUICK MATCH: String matching first (no LLM needed) ===
        query_lower = query.lower()
        matches = []
        
        for s in subjects:
            name_lower = s['name'].lower()
            # Check if full subject name appears in query
            if name_lower in query_lower:
                matches.append(s)
        
        # If exactly ONE match, return immediately (skip LLM)
        if len(matches) == 1:
            logger.info(f"Quick match found: {matches[0]['name']} ({matches[0]['code']})")
            return matches[0]['code']
        
        # If multiple matches or no matches, check with LLM
        if not self.enabled:
            return None
            
        # === LLM FALLBACK: Only for ambiguous cases ===
        subject_list = "\n".join([f"- {s['name']} ({s['code']})" for s in subjects])
        
        prompt = f"""You are a subject matcher. DO NOT explain or reason. Just output JSON.

Query: "{query}"
Subjects: {subject_list}

If query mentions exact subject name from list → return its code.
Otherwise → return null.

Respond with ONLY: {{"match": "CODE"}} or {{"match": null}}"""
        
        # Không giới hạn max_tokens, dùng prompt để control
        content = self._call_with_retry([{"role": "user", "content": prompt}], temperature=0.1)
        
        if not content:
            return None
            
        # Parse JSON response
        try:
            # Strip thinking chain (GLM model outputs: ...thinking...</think>JSON)
            if "</think>" in content:
                content = content.split("</think>", 1)[1].strip()
            
            # Strip markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Try to find JSON object in content
            if "{" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                if end > start:
                    content = content[start:end]
            
            result = json.loads(content)
            match = result.get("match")
            reason = result.get("reason", "")
            
            logger.info(f"LLM Verification: match={match}, reason={reason}")
            return match
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response: {content}")
            # Try regex extraction as fallback
            match_search = re.search(r'"match":\s*"?([A-Za-z0-9_]+)"?', content)
            if match_search:
                extracted = match_search.group(1)
                if extracted.lower() != "null":
                    return extracted
            return None

    def contextualize_query(self, query: str, chat_history: List[Dict[str, str]]) -> str:
        """
        Rewrite query to include context from chat history.
        Resolves pronouns like 'nó', 'môn đó'.
        """
        if not self.enabled or not chat_history:
            return query
            
        # Limit to last 6 messages
        recent_history = chat_history[-6:]
        
        prompt = f"""You are a query rewriter. DO NOT explain. Just rewrite.

Replace pronouns (nó, môn đó, nó ấy) with the actual subject name from chat history.
If no pronoun needs replacing, return the original question.

Chat History: {json.dumps(recent_history, ensure_ascii=False)}

Rewrite this: {query}

Output ONLY the rewritten question (one line, Vietnamese):"""
        
        rewritten = self._call_with_retry([{"role": "user", "content": prompt}], temperature=0.1)
        
        if rewritten and rewritten.strip():
            # Strip thinking chain (GLM model outputs: ...thinking...</think>ANSWER)
            if "</think>" in rewritten:
                rewritten = rewritten.split("</think>", 1)[1].strip()
            logger.info(f"Query contextualized: '{query}' -> '{rewritten.strip()}'")
            return rewritten.strip()
        
        return query

    def refine_intent(self, query: str) -> Dict[str, Any]:
        """Classify query intent."""
        if not self.enabled:
            return {"category": "GENERAL_ACADEMIC"}

        prompt = f"""You are a classifier. DO NOT explain. Just output JSON.

Query: "{query}"

Classify into:
- category: SPECIFIC_COURSE (asks about a named course) | GENERAL_ACADEMIC | IRRELEVANT
- section_intent: lecturer_info | grading | schedule | objectives | materials | null

Output ONLY: {{"category": "...", "section_intent": "..."}}"""
        content = self._call_with_retry([{"role": "user", "content": prompt}], temperature=0.1)
        
        if not content:
            return {"category": "GENERAL_ACADEMIC", "section_intent": None}
            
        try:
            # Strip thinking chain (GLM model outputs: ...thinking...</think>JSON)
            if "</think>" in content:
                content = content.split("</think>", 1)[1].strip()
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Try to find JSON object in content
            if "{" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                if end > start:
                    content = content[start:end]
                
            result = json.loads(content)
            return result
            return result
        except Exception as e:
            logger.error(f"Intent parsing error: {e}")
            return {"category": "GENERAL_ACADEMIC", "section_intent": None}

    def match_course_from_list(self, query: str, course_batch: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Ask LLM to find the specific subject in the query from a batch of courses.
        Returns: {"code": "...", "name": "..."} or None
        """
        if not course_batch:
            return None
            
        subject_list_str = "\n".join([f"- {c['name']} (Code: {c['code']})" for c in course_batch])
        
        prompt = f"""You are a strict course matcher.
        
Query: "{query}"

Course List:
{subject_list_str}

Task:
1. Check if the user's query matches the NAME of any course in the list.
2. The match must be SPECIFIC. 
   - "topo" MATCHES "Tôpô" (accent/spelling difference is OK).
   - "đại số 1" MATCHES "Đại số 1" (exact match).
   - "đại số" does NOT match "Đại số 1" (ambiguous, missing number).
3. DO NOT match based on meaning or category.
4. If the query does not specifically name any course in this list, return null. 
5. BE SKEPTICAL. If unsure, return null.

Output JSON ONLY:
{{
  "match": {{
    "code": "COURSE_CODE",
    "name": "COURSE_NAME"
  }}
}}
OR
{{
  "match": null
}}
"""
        response = self._call_with_retry([{"role": "user", "content": prompt}], temperature=0.0)
        
        if response:
            try:
                # Clean markdown
                clean_resp = response
                if "</think>" in clean_resp:
                     clean_resp = clean_resp.split("</think>", 1)[1].strip()
                
                if "```json" in clean_resp:
                    clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_resp:
                    clean_resp = clean_resp.split("```")[1].split("```")[0].strip()
                
                # Try to find JSON object in content
                if "{" in clean_resp:
                    start = clean_resp.find("{")
                    end = clean_resp.rfind("}") + 1
                    if end > start:
                        clean_resp = clean_resp[start:end]

                import json
                data = json.loads(clean_resp)
                return data.get("match")
            except Exception as e:
                logger.error(f"Error parsing batch match response: {e}")
                
        return None
