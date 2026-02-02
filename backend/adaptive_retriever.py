"""
Adaptive Retriever with Top 5 Subject Verification Workflow
Refactored for cleaner code structure.
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
        Full RAG flow with Top 5 Subject Verification.
        
        Workflow:
        1. Contextualize query (if chat history exists)
        2. Hybrid Search -> Get candidates
        3. Extract Top 5 unique subjects
        4. LLM Verify: Does query refer to one specific subject?
        5a. If YES: Get ALL chunks of that subject -> LLM Answer
        5b. If NO: Return candidates for user clarification
        """
        original_query = query
        
        # Step 0: Intent Routing
        intent = "NEW_TOPIC"
        current_subject_name = None
        
        # Get subject name for routing context
        if current_subject:
             subj_info = self.subject_manager.get_subject_by_code(current_subject)
             if subj_info:
                 current_subject_name = subj_info.name
        
        # Classify Intent
        if current_subject:
            intent = self.intent_router.classify(query, current_subject, current_subject_name)
            logger.info(f"Routing: {intent} (Context: {current_subject_name})")
        
        # Branch 1: CHITCHAT
        if intent == "CHITCHAT":
            return {
                "query": query,
                "answer": "Xin chào! Tôi có thể giúp gì cho bạn về các môn học?",
                "sources": [],
                "intent": "CHITCHAT"
            }
            
        # Branch 2: FOLLOW_UP (Reuse current subject)
        if intent == "FOLLOW_UP" and current_subject:
            logger.info(f"Follow-up detected -> Using kept subject {current_subject}")
            section_intent = self._detect_section_intent(query)
            return self._answer_with_subject(query, current_subject, section_intent)
            
        # Branch 3: NEW_TOPIC -> Proceed to Contextualize & Search
        logger.info("New Topic/Search detected -> Proceeding with RAG")
        
        # Step 1: Contextualize Query (resolve pronouns)
        if chat_history:
            query = self.llm.contextualize_query(query, chat_history)
            logger.info(f"Contextualized query: '{original_query}' -> '{query}'")
        
        logger.info(f"--- Processing Query: '{query}' ---")
        
        try:
            # Step 2: Detect Section Intent (heuristic, no LLM call)
            section_intent = self._detect_section_intent(query)
            
            # Step 3: Hybrid Search
            logger.info("Step 1: Performing Hybrid Search...")
            raw_results = self.retriever.hybrid_search(query, top_k=Config.TOP_K_SEARCH, alpha=Config.HYBRID_ALPHA)
            logger.info(f"Found {len(raw_results)} raw chunks")
            
            # Step 4: Extract Top 5 unique subjects
            top_5_subjects = self._extract_top_subjects(raw_results, query, max_subjects=Config.TOP_K_SUBJECTS)
            logger.info(f"Step 2: Top {len(top_5_subjects)} subjects: {[s['name'] for s in top_5_subjects]}")
            
            if not top_5_subjects:
                # No subjects found -> General response
                return self._general_answer(query, raw_results[:top_k])
            
            # Step 5: LLM Verification
            logger.info("Step 3: LLM Verification...")
            matched_code = self.llm.verify_subject_in_top5(query, top_5_subjects)
            
            if matched_code:
                # Step 6a: Match found -> Answer with full context
                logger.info(f"Step 4: MATCH FOUND -> {matched_code}")
                return self._answer_with_subject(query, matched_code, section_intent)
            else:
                # Step 6b: Try Metadata Lookup (LLM-based Fallback)
                logger.info("Step 4a: Ambiguous -> Verifying with LLM Batch Metadata Search...")
                
                # Get all courses and batch them
                all_courses = self.course_loader.get_course_list_for_matching()
                batch_size = 30
                
                matched_meta = None
                
                for i in range(0, len(all_courses), batch_size):
                    batch = all_courses[i:i+batch_size]
                    logger.info(f"Scanning batch {i//batch_size + 1}/{(len(all_courses)-1)//batch_size + 1}...")
                    
                    match_result = self.llm.match_course_from_list(query, batch)
                    if match_result:
                        matched_meta = match_result
                        logger.info(f"Step 4b: METADATA FALLBACK FOUND -> {matched_meta['name']} ({matched_meta['code']})")
                        break
                
                if matched_meta:
                    return self._answer_with_subject(
                        query, 
                        matched_meta['code'], 
                        section_intent, 
                        subject_name_hint=matched_meta['name'] # Ensure name from matching is used
                    )
                
                # Step 6c: Ambiguous -> Ask for clarification
                logger.info("Step 4c: AMBIGUOUS -> Need Clarification")
                return {
                    "query": query,
                    "answer": "Tôi tìm thấy các môn học sau có thể liên quan. Bạn đang muốn hỏi về môn nào?",
                    "sources": raw_results[:top_k],
                    "intent": "AMBIGUOUS",
                    "subjects": [s['name'] for s in top_5_subjects],
                    "candidates": top_5_subjects,
                    "need_clarification": True
                }
                
        except Exception as e:
            logger.error(f"Error in search_and_answer: {e}", exc_info=True)
            return {
                "query": query,
                "answer": "Xin lỗi, đã có lỗi xảy ra trong quá trình xử lý.",
                "sources": [],
                "intent": "ERROR"
            }

    def _detect_section_intent(self, query: str) -> Optional[str]:
        """Detect section intent using keyword heuristics."""
        q_lower = query.lower()
        
        if any(w in q_lower for w in ["điểm", "đánh giá", "thi", "trọng số", "cách tính"]):
            return "grading"
        elif any(w in q_lower for w in ["giảng viên", "thầy", "cô", "email", "liên hệ", "ai dạy"]):
            return "lecturer"
        elif any(w in q_lower for w in ["tài liệu", "giáo trình", "sách", "tham khảo"]):
            return "materials"
        elif any(w in q_lower for w in ["mục tiêu", "chuẩn đầu ra", "kỹ năng"]):
            return "objectives"
        elif any(w in q_lower for w in ["lịch", "tuần", "tiết"]):
            return "schedule"
        
        return None

    def _extract_top_subjects(
        self, 
        results: List[Dict], 
        query: str,
        max_subjects: int = 5
    ) -> List[Dict[str, str]]:
        """
        Extract unique subjects from search results.
        Returns list of {"code": "...", "name": "..."} dicts.
        """
        top_subjects = []
        seen_codes = set()
        seen_names = set()  # Avoid duplicate names with different codes
        
        # Also check name-based detection
        detected_by_name = self.subject_manager.detect_subjects(query)
        
        # Priority 1: Add name-based matches first (more accurate)
        for subj in detected_by_name:
            if subj.name not in seen_names and subj.code not in seen_codes:
                seen_codes.add(subj.code)
                seen_names.add(subj.name)
                top_subjects.append({"code": subj.code, "name": subj.name})
                if len(top_subjects) >= max_subjects:
                    break
        
        # Priority 2: Add from vector search results
        if len(top_subjects) < max_subjects:
            for res in results:
                chunk = res.get('chunk', {})
                code = chunk.get('course_code', '').strip()
                name = chunk.get('course_name', '').strip()
                
                if code and name and code not in seen_codes and name not in seen_names:
                    seen_codes.add(code)
                    seen_names.add(name)
                    top_subjects.append({"code": code, "name": name})
                    if len(top_subjects) >= max_subjects:
                        break
        
        return top_subjects

    def _answer_with_subject(
        self, 
        query: str, 
        subject_code: str,
        section_intent: Optional[str] = None,
        subject_name_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate answer using ALL information about the subject.
        Priority: Full JSON Context > All Chunks > General Answer
        """
        # 1. Try Loading Full JSON Context
        # Lookup name to help finding metadata if code is invalid (e.g. "...")
        subj_info = self.subject_manager.get_subject_by_code(subject_code)
        subject_name = subject_name_hint if subject_name_hint else (subj_info.name if subj_info else None)
        
        full_course_data = self.course_loader.load_full_course_json(course_code=subject_code, course_name=subject_name)
        
        context_chunks = []
        is_full_context = False
        
        if full_course_data:
            logger.info(f"Using FULL JSON context for subject {subject_code}")
            full_text = self.course_loader.format_course_as_context(full_course_data)
            
             # Update subject display name from metadata
            display_name = full_course_data['_metadata'].get('course_name', subject_code)
            
            # Wrap into a single chunk for LLMInterface
            context_chunks = [{
                "text": full_text,
                "course_name": display_name,
                "section_name": "Full Course Document",
                "score": 1.0
            }]
            is_full_context = True
            
        else:
            # 2. Fallback: Get all chunks from chunks.json
            logger.warning(f"Full JSON not found for {subject_code}, falling back to chunks.")
            context_chunks = self.subject_manager.get_all_chunks_by_code(subject_code)
            
            if not context_chunks:
                return {
                    "query": query,
                    "answer": f"Không tìm thấy thông tin chi tiết cho môn học {subject_code}.",
                    "sources": [],
                    "intent": "NOT_FOUND"
                }
            
            # Sort chunks by relevance if using fallback chunks
            if section_intent:
                context_chunks = self._sort_chunks_by_intent(context_chunks, section_intent, query)
            
            # Get display name from SubjectManager
            subj_info = self.subject_manager.get_subject_by_code(subject_code)
            display_name = subj_info.name if subj_info else subject_code

        # Generate answer using LLM
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

    def _sort_chunks_by_intent(
        self, 
        chunks: List[Dict], 
        section_intent: str,
        query: str
    ) -> List[Dict]:
        """Sort chunks by relevance to section intent."""
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
            
            # Check section intent keywords
            for kw in keywords:
                if kw in sec_lower:
                    score += 100  # Section title match
                elif kw in text_lower:
                    score += 10   # Content match
            
            # Check query word matches
            q_words = [w for w in query.lower().split() if len(w) > 3]
            for w in q_words:
                if w in text_lower:
                    score += 1
                    
            return score
        
        return sorted(chunks, key=priority_key, reverse=True)

    def _general_answer(self, query: str, results: List[Dict]) -> Dict[str, Any]:
        """Generate general answer without specific subject context."""
        context_chunks = [r.get('chunk', r) for r in results]
        
        if self.llm and self.llm.enabled:
            answer = self.llm.generate_answer(query, context_chunks)
        else:
            answer = "Top results:\n" + "\n".join([c.get('text', '')[:200] for c in context_chunks])

        return {
            "query": query,
            "answer": answer,
            "sources": results,
            "intent": "GENERAL_ACADEMIC",
            "subjects": []
        }