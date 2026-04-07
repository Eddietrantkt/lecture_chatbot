"""
Adaptive Retriever with Domain-First Pipeline
Separates Major (Program) vs Course (Subject) retrieval flows.
"""
import logging
from typing import List, Dict, Any, Optional
import sys
import os

# Configure Logger
logger = logging.getLogger("Retriever")

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from script.embedding_indexing_script import HybridRetriever
from backend.course_loader import CourseLoader
from backend.intent_router import IntentRouter
from backend.subject_manager import SubjectManager, SubjectInfo
from backend.llm_interface import LLMInterface
from backend.config import Config


class AdaptiveRetriever:
    def __init__(self, index_dir: str, chunks_file: str):
        """Initialize retriever with index and LLM."""
        # Initialize Hybrid Retriever
        self.retriever = HybridRetriever()

        # Load existing index
        if os.path.exists(index_dir):
            self.retriever.load_index(index_dir)
            logger.info(f"Index loaded from {index_dir}")
        else:
            raise FileNotFoundError(
                f"Index not found at {index_dir}. "
                "Please run 'python embedding_indexing_script.py' first."
            )

        # Initialize Subject Manager
        self.subject_manager = SubjectManager(chunks_file)

        # Initialize Course Loader (for full context)
        self.course_loader = CourseLoader(index_dir)

        # Initialize LLM Interface
        self.llm = LLMInterface()

        # Initialize Intent Router
        self.intent_router = IntentRouter(self.llm)

        logger.info("AdaptiveRetriever initialized successfully")

    def search_and_answer(
        self,
        query: str,
        top_k: int = 5,
        chat_history: Optional[List[Dict[str, str]]] = None,
        current_subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Domain-First RAG Pipeline:
        1. Classify Intent (MAJOR_INFO, COURSE_INFO, etc.)
        2. Route to specialized flow.
        """
        original_query = query

        # 1. Contextualize Query if needed (resolve pronouns)
        if chat_history:
            # We contextualize first to get the best intent classification
            query_ctx = self.llm.contextualize_query(query, chat_history)
            logger.info(f"Contextualized query: '{original_query}' -> '{query_ctx}'")
            query = query_ctx

        # 2. Intent Routing
        current_subject_name = None
        if current_subject:
             subj_info = self.subject_manager.get_subject_by_code(current_subject)
             if subj_info:
                 current_subject_name = subj_info.name

        intent = self.intent_router.classify(query, current_subject, current_subject_name)
        logger.info(f"Routing Intent: {intent} (Context: {current_subject_name})")

        # 3. Dispatch to Handlers
        if intent == "CHITCHAT":
            return {
                "query": query,
                "answer": "Xin chào! Tôi có thể giúp gì cho bạn về chương trình đào tạo và các môn học?",
                "sources": [],
                "intent": "CHITCHAT"
            }

        if intent == "MAJOR_INFO":
            return self._handle_major_flow(query)

        if intent == "COURSE_INFO":
            return self._handle_course_flow(query, top_k)

        if intent == "FOLLOW_UP" and current_subject:
            # Determine if current context is Major or Course
            subj_info = self.subject_manager.get_subject_by_code(current_subject)
            if subj_info and subj_info.is_major:
                return self._answer_for_major(query, subj_info)
            else:
                section_intent = self._detect_section_intent(query)
                return self._answer_with_subject(query, current_subject, section_intent)

        # Fallback / OTHERS: Try general hybrid search
        return self._handle_general_search(query, top_k)

    def _handle_major_flow(self, query: str) -> Dict[str, Any]:
        """Pipeline for Major/Program queries"""
        logger.info("Entering Major Pipeline...")

        # 1. Detect Major Entity
        candidates = self.subject_manager.detect_majors(query)

        if not candidates:
            # If no major detected by name, try fuzzy search or general fallback
            logger.warning("No major name detected in query.")

            # Get all majors as candidates
            all_majors = self.course_loader.get_all_majors_list()

            return {
                "query": query,
                "answer": "Bạn đang hỏi về ngành nào? (Ví dụ: Ngành Toán học, Ngành Khoa học dữ liệu...)",
                "sources": [],
                "intent": "AMBIGUOUS_MAJOR",
                "need_clarification": True,
                "candidates": all_majors
            }

        # 2. Select Top Major (assuming single intent for now)
        target_major = candidates[0]
        logger.info(f"Identified Major: {target_major.name}")

        return self._answer_for_major(query, target_major)

    def _handle_course_flow(self, query: str, top_k: int) -> Dict[str, Any]:
        """Pipeline for Specific Course queries"""
        logger.info("Entering Course Pipeline...")

        # 1. Detect Course Entity
        candidates = self.subject_manager.detect_courses(query)

        # 2. Logic to pick best candidate
        target_course = None

        if candidates:
            # If explicit course code/name match
            top_candidate = candidates[0]
            # Simple heuristic: if score is decent or it's the only one
            target_course = top_candidate
            logger.info(f"Identified Course: {target_course.name} ({target_course.code})")

        if target_course:
            section_intent = self._detect_section_intent(query)
            return self._answer_with_subject(query, target_course.code, section_intent, subject_name_hint=target_course.name)

        # 3. If no explicit detection, fallback to Hybrid Search + LLM Verification
        # This handles vague queries like "môn học về đạo hàm"
        return self._handle_general_search(query, top_k)

    def _handle_general_search(self, query: str, top_k: int) -> Dict[str, Any]:
        """Fallback hybrid search when no specific entity is detected"""
        logger.info("Performing General Hybrid Search...")
        raw_results = self.retriever.hybrid_search(query, top_k=Config.TOP_K_SEARCH, alpha=Config.HYBRID_ALPHA)

        # Try to extract top subjects from results to see if we can converge
        top_subjects = self._extract_top_subjects_from_chunks(raw_results)

        if not top_subjects:
             return self._generate_general_answer(query, raw_results[:top_k])

        # LLM Verification
        matched_code = self.llm.verify_subject_in_top5(query, top_subjects)
        if matched_code:
            return self._answer_with_subject(query, matched_code, self._detect_section_intent(query))

        return self._generate_general_answer(query, raw_results[:top_k])

    def _extract_top_subjects_from_chunks(self, results: List[Dict], max_subjects: int = 5) -> List[Dict[str, Any]]:
        """Extract unique subjects purely from search results."""
        seen = set()
        top = []
        for res in results:
            chunk = res.get('chunk', {})
            code = chunk.get('course_code', '').strip()
            name = chunk.get('course_name', '').strip()
            if code and code not in seen:
                seen.add(code)
                # Check if it's major or course
                subj_info = self.subject_manager.get_subject_by_code(code)
                is_major = getattr(subj_info, 'is_major', False) if subj_info else False

                top.append({"code": code, "name": name, "is_major": is_major})
                if len(top) >= max_subjects:
                    break
        return top

    def _answer_for_major(self, query: str, major_info: SubjectInfo) -> Dict[str, Any]:
        """Generate answer for a specific major."""
        logger.info(f"Answering MAJOR info for: {major_info.name}")

        # 1. Get Major Metadata (Course List)
        major_meta = self.course_loader.get_major_full_details(major_info.code)

        # 2. Get Major Text Chunks
        major_chunks = self.subject_manager.get_all_chunks_by_code(major_info.code)

        # 3. Construct Context
        courses_str = ""
        if major_meta and "courses_list" in major_meta:
            lines = ["**Danh sách các môn học trong chương trình:**"]
            for c in major_meta["courses_list"]:
                lines.append(f"- {c['code']} - {c['name']} ({c['type']})")
            courses_str = "\n".join(lines)

        # Select relevant chunks (simple relevance sort)
        sorted_chunks = self._sort_chunks_by_relevance(major_chunks, query)[:5]

        context_text = f"# THÔNG TIN NGÀNH {major_info.name}\n\n"
        if courses_str:
            context_text += courses_str + "\n\n"

        context_text += "## MÔ TẢ CHI TIẾT\n"
        for c in sorted_chunks:
            context_text += f"{c.get('text', '')}\n---\n"

        # 4. Ask LLM
        prompt = f"""Based on the following information about the major "{major_info.name}", please answer the user's question.
If the user asks for a list of subjects, refer to the "Danh sách các môn học" section provided.

Context:
{context_text}

Question: {query}
Answer:"""

        answer = self.llm._call_with_retry(
            [{"role": "user", "content": prompt}],
            temperature=1.0,
            top_p=0.95,
            presence_penalty=1.5,
            enable_thinking=True
        )

        return {
            "query": query,
            "answer": answer,
            "sources": [{"chunk": c, "score": 1.0} for c in sorted_chunks[:3]],
            "intent": "MAJOR_INFO",
            "subjects": [major_info.name],
            "matched_code": major_info.code
        }

    def _answer_with_subject(
        self,
        query: str,
        subject_code: str,
        section_intent: Optional[str] = None,
        subject_name_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate answer using specific COURSE context."""
        # 1. Load Full JSON Context
        subj_info = self.subject_manager.get_subject_by_code(subject_code)
        subject_name = subject_name_hint if subject_name_hint else (subj_info.name if subj_info else None)

        # Safety: If somehow a Major code got here, redirect
        if subj_info and subj_info.is_major:
            return self._answer_for_major(query, subj_info)

        full_course_data = self.course_loader.load_full_course_json(course_code=subject_code, course_name=subject_name)

        context_chunks = []
        is_full_context = False
        display_name = subject_name or subject_code

        if full_course_data:
            logger.info(f"Using FULL JSON context for course {subject_code}")
            full_text = self.course_loader.format_course_as_context(full_course_data)
            display_name = full_course_data['_metadata'].get('course_name', display_name)

            context_chunks = [{
                "text": full_text,
                "course_name": display_name,
                "section_name": "Full Course Document",
                "score": 1.0
            }]
            is_full_context = True
        else:
            # Fallback to chunks
            logger.warning(f"Full JSON not found for {subject_code}, falling back to chunks.")
            context_chunks = self.subject_manager.get_all_chunks_by_code(subject_code)

            if not context_chunks:
                return {
                    "query": query,
                    "answer": f"Không tìm thấy thông tin chi tiết cho môn học {display_name}.",
                    "sources": [],
                    "intent": "NOT_FOUND"
                }

            if section_intent:
                context_chunks = self._sort_chunks_by_intent(context_chunks, section_intent, query)

        # Generate answer
        answer = self.llm.generate_answer(query, context_chunks)

        return {
            "query": query,
            "answer": answer,
            "sources": [{"chunk": c, "score": 1.0} for c in context_chunks[:5]],
            "intent": "SPECIFIC_COURSE",
            "subjects": [display_name],
            "matched_code": subject_code,
            "is_full_context": is_full_context
        }

    def _generate_general_answer(self, query: str, results: List[Dict]) -> Dict[str, Any]:
        """Generate general answer from raw chunks."""
        context_chunks = [r.get('chunk', r) for r in results]
        answer = self.llm.generate_answer(query, context_chunks)
        return {
            "query": query,
            "answer": answer,
            "sources": results,
            "intent": "GENERAL_SEARCH",
            "subjects": []
        }

    def _detect_section_intent(self, query: str) -> Optional[str]:
        """Detect section intent using keyword heuristics."""
        q_lower = query.lower()
        if any(w in q_lower for w in ["điểm", "đánh giá", "thi", "trọng số", "cách tính"]): return "grading"
        elif any(w in q_lower for w in ["giảng viên", "thầy", "cô", "email", "liên hệ"]): return "lecturer"
        elif any(w in q_lower for w in ["tài liệu", "giáo trình", "sách"]): return "materials"
        elif any(w in q_lower for w in ["mục tiêu", "chuẩn đầu ra", "kỹ năng"]): return "objectives"
        elif any(w in q_lower for w in ["lịch", "tuần", "tiết"]): return "schedule"
        return None

    def _sort_chunks_by_intent(self, chunks: List[Dict], section_intent: str, query: str) -> List[Dict]:
        """Sort chunks based on section intent."""
        section_keywords = {
            "grading": ["đánh giá", "điểm", "trọng số", "thi"],
            "lecturer": ["giảng viên", "liên hệ", "email"],
            "materials": ["tài liệu", "giáo trình"],
            "objectives": ["mục tiêu", "chuẩn đầu ra"],
            "schedule": ["lịch", "tuần", "tiết"]
        }
        keywords = section_keywords.get(section_intent, [])

        def priority_key(chunk):
            score = 0
            text_lower = chunk.get('text', '').lower()
            sec_lower = chunk.get('section_name', '').lower()
            for kw in keywords:
                if kw in sec_lower: score += 100
                elif kw in text_lower: score += 10
            return score

        return sorted(chunks, key=priority_key, reverse=True)

    def _sort_chunks_by_relevance(self, chunks: List[Dict], query: str) -> List[Dict]:
        """Simple keyword overlap sort."""
        q_words = set(query.lower().split())
        def score(c):
            text = c.get('text', '').lower()
            return sum(1 for w in q_words if w in text)
        return sorted(chunks, key=score, reverse=True)
