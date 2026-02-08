import logging
from typing import Dict, List, Optional
from backend.llm_interface import LLMInterface

logger = logging.getLogger("IntentRouter")

class IntentRouter:
    """
    Classifies user query intent relative to the current conversation context.
    Intents:
    - MAJOR_INFO: General program/major questions.
    - COURSE_INFO: Specific course/subject questions.
    - FOLLOW_UP: More details about the CURRENT context.
    - CHITCHAT: Social interaction.
    - OTHERS: Irrelevant or ambiguous.
    """

    def __init__(self, llm: LLMInterface):
        self.llm = llm

    def classify(self, query: str, current_subject_code: Optional[str] = None, current_subject_name: Optional[str] = None) -> str:
        """
        Determine intent of the query given the current subject context.
        """
        context_str = "None"
        if current_subject_name:
            context_str = f"{current_subject_name} (Code: {current_subject_code})"

        prompt = f"""You are an Intent Classifier for a University Q&A System.

Current Conversation Context: **{context_str}**
User Query: "{query}"

Task: Classify into one of 5 categories:
1. **MAJOR_INFO**: User asks about a **Major/Program/Field** (Ngành, Chuyên ngành) generally.
   - Keywords: "Ngành", "Chương trình đào tạo", "Cơ hội việc làm", "Ra trường làm gì", "Danh sách môn", "Khung chương trình", "Chuẩn đầu ra".
   - E.g. "Ngành Toán học học gì?", "Giới thiệu ngành KHDL", "Học phí ngành này bao nhiêu?", "Sinh viên tốt nghiệp làm gì?".

2. **COURSE_INFO**: User asks about a **Specific Subject/Course** (Môn học, Học phần).
   - Keywords: "Môn", "Học phần", "Đề cương", "Giáo trình", "Thầy nào dạy", "Mã môn", "Tài liệu", "Điểm số", "Cách tính điểm".
   - E.g. "Môn Giải tích 1 học gì?", "Ai dạy môn Python?", "Sách giáo trình môn Đại số", "Mã môn CSC10002".

3. **FOLLOW_UP**: User asks for more details about the **CURRENT** subject/context mentioned above.
   - E.g. Context="Math", Query="Who teaches it?" -> FOLLOW_UP
   - *IF Context is None, this cannot be FOLLOW_UP.*

4. **CHITCHAT**: Social interaction, greetings, thanks.

5. **OTHERS**: Irrelevant questions, out-of-domain topics, or ambiguous queries that don't fit above.

Output JSON ONLY:
{{
  "intent": "MAJOR_INFO" | "COURSE_INFO" | "FOLLOW_UP" | "CHITCHAT" | "OTHERS",
  "reasoning": "Brief explanation"
}}
"""
        response = self.llm._call_with_retry([{"role": "user", "content": prompt}], temperature=0.0)

        default_intent = "OTHERS"

        if response:
            try:
                # Clean response
                clean_resp = response
                if "</think>" in clean_resp:
                     clean_resp = clean_resp.split("</think>", 1)[1].strip()

                if "```json" in clean_resp:
                    clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_resp:
                    clean_resp = clean_resp.split("```")[1].split("```")[0].strip()

                # Try to extract JSON
                import json
                if "{" in clean_resp:
                    start = clean_resp.find("{")
                    end = clean_resp.rfind("}") + 1
                    clean_resp = clean_resp[start:end]

                data = json.loads(clean_resp)
                intent = data.get("intent", default_intent).upper()

                # Safety check: Cannot be FOLLOW_UP if no context
                if intent == "FOLLOW_UP" and not current_subject_name:
                    logger.warning("Classified as FOLLOW_UP but no context exists. Forcing COURSE_INFO (search attempt).")
                    return "COURSE_INFO"

                return intent

            except Exception as e:
                logger.error(f"Error parsing intent: {e}")
                return default_intent

        return default_intent
