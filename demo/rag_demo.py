"""
Demo RAG Q&A - VERBOSE DEBUG Mode (Fixed)
==========================================
Script demo hỏi đáp với full log từng bước chi tiết.

Chạy: python demo/rag_demo.py
"""
import sys
import os
import time
import json
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
from backend.llm_interface import LLMInterface
from backend.langchain_memory import LangchainMemoryManager
from backend.adaptive_retriever import AdaptiveRetriever
from backend.subject_manager import SubjectManager


def print_step(step_num: int, step_name: str, status: str = "⏳"):
    print(f"\n   {status} Step {step_num}: {step_name}")


def print_debug(msg: str, indent: int = 6):
    print(" " * indent + msg)


def main():
    print("\n" + "=" * 70)
    print("🔬 COURSE Q&A DEMO - VERBOSE DEBUG MODE")
    print("=" * 70)
    
    # ===== INITIALIZATION =====
    print("\n📦 KHỞI TẠO...")
    
    try:
        memory_manager = LangchainMemoryManager(max_messages_per_session=Config.MEMORY_MAX_MESSAGES)
        print(f"✅ Memory Manager")
        
        llm = LLMInterface()
        print(f"✅ LLM: {Config.LLM_MODEL}")
        
        retriever = AdaptiveRetriever(Config.INDEX_DIR, Config.CHUNKS_FILE)
        chunk_count = len(retriever.retriever.chunks) if retriever.retriever else 0
        print(f"✅ Retriever: {chunk_count} chunks")
        
        subject_manager = SubjectManager(Config.CHUNKS_FILE)
        print(f"✅ Subject Manager: {len(subject_manager.subjects)} subjects")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    session_id = "demo_verbose"
    memory = memory_manager.get_or_create(session_id)
    
    print("\n" + "=" * 70)
    print("💬 Gõ câu hỏi | 'exit' thoát | 'clear' xóa history")
    print("=" * 70)
    
    while True:
        try:
            print("\n" + "-" * 70)
            question = input("👤 Bạn: ").strip()
            
            if not question:
                continue
            if question.lower() == 'exit':
                break
            if question.lower() == 'clear':
                memory = memory_manager.get_or_create(f"demo_{int(time.time())}")
                print("🔄 Cleared!")
                continue
            
            total_start = time.time()
            
            # ===== STEP 1: HISTORY =====
            print_step(1, "Chat History")
            history = memory.get_history_as_list()
            print_debug(f"Messages: {len(history)}")
            
            # ===== STEP 2: CURRENT SUBJECT =====
            print_step(2, "Current Subject (from memory)")
            current_subject = memory.get_current_subject()
            if current_subject:
                print_debug(f"Subject: {current_subject}")
                print_debug("→ Sẽ dùng subject này cho follow-up!")
            else:
                print_debug("None")

            # ===== STEP 2a: INTENT ROUTING =====
            print_step("2a", "Intent Routing")
            intent = "NEW_TOPIC"
            matched_code = None # Initialize
            
            if current_subject:
                # Find subject name
                subj_info = retriever.subject_manager.get_subject_by_code(current_subject)
                subj_name = subj_info.name if subj_info else "Unknown"
                
                # Classify
                intent = retriever.intent_router.classify(question, current_subject, subj_name)
                print_debug(f"Context: {subj_name}")
                print_debug(f"Intent: {intent}")
                
                if intent == "FOLLOW_UP":
                    print_debug("👉 Follow-up detected -> Skipping Search")
                    matched_code = current_subject
                elif intent == "CHITCHAT":
                    print("="*70)
                    print("🤖 AI: Xin chào! Tôi có thể giúp gì cho bạn?")
                    print("="*70)
                    continue
            else:
                # Check for simple Chitchat even without context if desired, or skip
                pass
            
            # ===== STEP 3: CONTEXTUALIZE QUERY =====
            print_step(3, "Contextualize Query")
            refined_query = question
            if llm.enabled and len(history) > 0:
                t0 = time.time()
                refined_query = llm.contextualize_query(question, history)
                print_debug(f"Input: \"{question}\"")
                print_debug(f"Output: \"{refined_query}\"")
                print_debug(f"Time: {(time.time()-t0)*1000:.0f}ms")
            else:
                print_debug("Skip (no history or LLM disabled)")
            
            # ===== STEP 4: DETECT SECTION INTENT =====
            print_step(4, "Detect Section Intent")
            section_keywords = {
                "grading": ["điểm", "đánh giá", "thi", "trọng số"],
                "lecturer": ["giảng viên", "thầy", "cô", "email", "ai dạy"],
                "materials": ["tài liệu", "giáo trình", "sách"],
                "objectives": ["mục tiêu", "chuẩn đầu ra"],
                "schedule": ["lịch", "tuần", "tiết"]
            }
            q_lower = refined_query.lower()
            section_intent = None
            for intent, keywords in section_keywords.items():
                for kw in keywords:
                    if kw in q_lower:
                        section_intent = intent
                        break
                if section_intent:
                    break
            print_debug(f"Intent: {section_intent or 'None'}")
            
            # ===== STEP 5: HYBRID SEARCH =====
            print_step(5, "Hybrid Search")
            raw_results = []
            
            if not matched_code:
                t0 = time.time()
                raw_results = retriever.retriever.hybrid_search(refined_query, top_k=Config.TOP_K_SEARCH)
            print_debug(f"Query: \"{refined_query}\"")
            print_debug(f"Results: {len(raw_results)} chunks")
            print_debug(f"Time: {(time.time()-t0)*1000:.0f}ms")
            
            if raw_results:
                print_debug("Top 3 results:")
                for i, r in enumerate(raw_results[:3], 1):
                    chunk = r.get('chunk', r)
                    score = r.get('score', 0)
                    course = chunk.get('course_name', 'Unknown')
                    code = chunk.get('course_code', '?')
                    text = chunk.get('text', '')[:40]
                    print_debug(f"  {i}. [{score:.3f}] {course} ({code}): {text}...")
            
            # ===== STEP 6: EXTRACT TOP 5 SUBJECTS (FIXED!) =====
            print_step(6, "Extract Top 5 UNIQUE Subjects")
            
            # From search results only - more reliable than keyword detection
            seen_codes = set()
            seen_names = set()
            top_5_subjects = []
            
            for r in raw_results:
                chunk = r.get('chunk', {})
                code = chunk.get('course_code', '').strip()
                name = chunk.get('course_name', '').strip()
                
                if code and name and code not in seen_codes and name not in seen_names:
                    seen_codes.add(code)
                    seen_names.add(name)
                    top_5_subjects.append({"code": code, "name": name})
                    
                    if len(top_5_subjects) >= 5:
                        break
            
            print_debug(f"Final Top 5: {[f'{s['name']} ({s['code']})' for s in top_5_subjects]}")
            # ===== STEP 7: QUICK STRING MATCH =====
            print_step(7, "Quick String Match (no LLM)")
            if matched_code:
                print_debug("Skipped (Already matched by Context/Follow-up)")
            else:
                matches = []
                for s in top_5_subjects:
                    name_lower = s['name'].lower()
                    if name_lower in q_lower:
                        matches.append(s)
                        print_debug(f"✓ Match: '{name_lower}' in query")
                
                if len(matches) == 1:
                    print_debug(f"✅ Single match: {matches[0]['name']} ({matches[0]['code']})")
                    matched_code = matches[0]['code']
                elif len(matches) > 1:
                    # Multiple matches with same name = pick first
                    unique_names = set(m['name'] for m in matches)
                    if len(unique_names) == 1:
                        print_debug(f"✅ Same subject: {matches[0]['name']}")
                        matched_code = matches[0]['code']
                    else:
                        print_debug(f"⚠️ Multiple different matches: {list(unique_names)}")
                        matched_code = None
                else:
                    print_debug(f"❌ No string match")
                    matched_code = None
            
            # ===== STEP 8: LLM VERIFICATION (if needed) =====
            if matched_code is None and top_5_subjects:
                print_step(8, "LLM Subject Verification")
                
                # Only send top 5 unique subjects to LLM
                subject_list = "\n".join([f"- {s['name']} ({s['code']})" for s in top_5_subjects])
                prompt = f"""You are a subject matcher. Output JSON only.

Query: "{refined_query}"
Subjects:
{subject_list}

If query mentions exact subject name from list → return its code.
Otherwise → return null.

Output: {{"match": "CODE"}} or {{"match": null}}"""
                
                print_debug("Prompt (short):")
                print_debug(f"  Query: \"{refined_query}\"")
                print_debug(f"  Subjects: {len(top_5_subjects)} items")
                
                t0 = time.time()
                response = llm._call_with_retry([{"role": "user", "content": prompt}], temperature=0.1)
                print_debug(f"Time: {(time.time()-t0)*1000:.0f}ms")
                print_debug(f"Response: {response[:100] if response else 'None'}...")
                
                # Parse
                if response:
                    if "</think>" in response:
                        response = response.split("</think>", 1)[1].strip()
                    if "{" in response:
                        start = response.find("{")
                        end = response.rfind("}") + 1
                        json_str = response[start:end]
                        try:
                            result = json.loads(json_str)
                            matched_code = result.get("match")
                            print_debug(f"Parsed: {result}")
                        except:
                            print_debug(f"JSON parse failed")
            
            # ===== STEP 8b: METADATA FALLBACK (LLM Batched) =====
            course_name_hint = None
            if matched_code is None:
                print_step("8b", "Metadata Lookup Fallback (LLM Batch)")
                if hasattr(retriever, 'course_loader') and hasattr(llm, 'match_course_from_list'):
                    all_courses = retriever.course_loader.get_course_list_for_matching()
                    batch_size = 30
                    
                    found_match = None
                    for i in range(0, len(all_courses), batch_size):
                        batch = all_courses[i:i+batch_size]
                        print_debug(f"Scanning batch {i//batch_size + 1} ({len(batch)} items)...")
                        
                        match_result = llm.match_course_from_list(refined_query, batch)
                        if match_result:
                            found_match = match_result
                            break
                    
                    if found_match:
                        print_debug(f"✅ FOUND in Metadata: {found_match['name']} ({found_match['code']})")
                        matched_code = found_match['code']
                        course_name_hint = found_match['name']
                    else:
                        print_debug("❌ Not found in any batch")

            # ===== STEP 9: GENERATE ANSWER =====
            print_step(9, "Generate Answer")
            
            if matched_code:
                print_debug(f"Matched: {matched_code}")
                
                 # --- NEW LOGIC START: Full Context ---
                full_course_data = None
                
                # Find name hint for fallback if code is invalid
                if not course_name_hint:
                    course_name_hint = next((s['name'] for s in top_5_subjects if s['code'] == matched_code), None)
                
                if hasattr(retriever, 'course_loader'):
                     full_course_data = retriever.course_loader.load_full_course_json(matched_code, course_name=course_name_hint)
                
                if full_course_data:
                    print_debug(f"✅ Using FULL JSON Context")
                    print_debug(f"   File: {full_course_data['_metadata']['file_path']}")
                    full_text = retriever.course_loader.format_course_as_context(full_course_data)
                    # Wrap single chunk
                    full_chunks = [{
                        "text": full_text,
                        "course_name": full_course_data['_metadata']['course_name'],
                        "score": 1.0
                    }]
                else:
                    print_debug(f"⚠️ Full JSON not found, falling back to all chunks")
                    full_chunks = subject_manager.get_all_chunks_by_code(matched_code)
                    print_debug(f"Chunks: {len(full_chunks)}")
                
                t0 = time.time()
                # Pass single chunk (full context) or multiple chunks
                answer = llm.generate_answer(refined_query, full_chunks[:10] if not full_course_data else full_chunks)
                print_debug(f"Time: {(time.time()-t0)*1000:.0f}ms")
                
                memory.add_message_pair(question, answer)
                
                # Find display name
                for s in top_5_subjects:
                    if s['code'] == matched_code:
                        memory.set_subject(matched_code, s['name'])
                        break
            else:
                print_debug("No match → AMBIGUOUS")
                answer = "Tôi tìm thấy các môn học sau. Bạn muốn hỏi về môn nào?"
                memory.add_message_pair(question, answer)
            
            total_time = (time.time() - total_start) * 1000
            
            # ===== DISPLAY =====
            print("\n" + "=" * 70)
            print(f"🤖 AI ({total_time:.0f}ms):")
            print("-" * 70)
            print(answer)
            print("-" * 70)
            
            if not matched_code and top_5_subjects:
                print("⚠️ Chọn môn:")
                for i, s in enumerate(top_5_subjects, 1):
                    print(f"   {i}. {s['name']} ({s['code']})")
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
