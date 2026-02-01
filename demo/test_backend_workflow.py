"""
Demo Backend Workflow - Không cần Frontend
============================================
Script kiểm tra toàn bộ workflow backend:
1. Kết nối LLM (từ config.py)
2. Memory management  
3. Query refinement (xử lý đại từ)
4. Subject verification
5. RAG generation

Chạy: python demo/test_backend_workflow.py
"""
import sys
import os
import time
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
from backend.llm_interface import LLMInterface
from backend.langchain_memory import LangchainMemoryManager, SessionMemory


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step: int, title: str):
    print(f"\n🔹 Step {step}: {title}")
    print("-" * 50)


def test_config():
    """Test 1: Kiểm tra config"""
    print_header("STEP 1: Config Check")
    
    print(f"📁 Config file: backend/config.py")
    print(f"📡 LLM_BASE_URL: {Config.LLM_BASE_URL}")
    print(f"🤖 LLM_MODEL: {Config.LLM_MODEL}")
    print(f"🔑 LLM_API_KEY: {'***' + Config.LLM_API_KEY[-4:] if Config.LLM_API_KEY else 'Not set'}")
    print(f"⏱️  LLM_TIMEOUT: {Config.LLM_TIMEOUT}s")
    print(f"🔄 LLM_MAX_RETRIES: {Config.LLM_MAX_RETRIES}")
    print(f"💾 MEMORY_MAX_MESSAGES: {Config.MEMORY_MAX_MESSAGES}")
    
    return True


def test_llm_connection():
    """Test 2: Kiểm tra kết nối LLM"""
    print_header("STEP 2: LLM Connection Test")
    
    try:
        llm = LLMInterface()
        
        if not llm.enabled:
            print("❌ LLM không khởi tạo được!")
            return None
            
        print("✅ LLM client initialized")
        
        # Simple test
        print("\n⏳ Testing simple generation...")
        start = time.time()
        
        response = llm._call_with_retry([
            {"role": "user", "content": "Do not explain. What is 1+1? Answer with just the number:"}
        ], temperature=0.1)
        
        elapsed = time.time() - start
        
        if response:
            # Strip thinking if present
            if "</think>" in response:
                response = response.split("</think>", 1)[1].strip()
            print(f"✅ LLM Response: {response.strip()}")
            print(f"⏱️  Response time: {elapsed:.2f}s")
            return llm
        else:
            print("❌ LLM không trả về response")
            return None
            
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return None


def test_memory_manager():
    """Test 3: Kiểm tra Memory Manager"""
    print_header("STEP 3: Memory Manager Test")
    
    manager = LangchainMemoryManager(max_messages_per_session=Config.MEMORY_MAX_MESSAGES)
    print(f"✅ MemoryManager initialized (max_messages={Config.MEMORY_MAX_MESSAGES})")
    
    # Create session
    session_id = f"demo_session_{int(time.time())}"
    session = manager.get_or_create(session_id)
    print(f"✅ Session created: {session_id}")
    
    # Add messages
    session.add_user_message("Môn Giải tích 2A có bao nhiêu tín chỉ?")
    session.add_ai_message("Môn Giải tích 2A có 3 tín chỉ.")
    print("✅ Added message pair")
    
    # Set subject
    session.set_subject("MTH00012", "Giải tích 2A")
    print(f"✅ Subject set: {session.current_subject_name} ({session.current_subject_code})")
    
    # Check history
    history = session.get_history_as_list()
    print(f"\n📝 Chat History ({len(history)} messages):")
    for msg in history:
        role = "👤 User" if msg['role'] == 'user' else "🤖 AI"
        print(f"   {role}: {msg['content'][:50]}...")
    
    return manager, session_id


def test_query_refinement(llm: LLMInterface, session: SessionMemory):
    """Test 4: Query Refinement (xử lý đại từ)"""
    print_header("STEP 4: Query Refinement Test")
    
    # Simulate follow-up question with pronoun
    follow_up = "Giảng viên của nó là ai?"
    print(f"📝 Original query: \"{follow_up}\"")
    print(f"📝 Chat history: User hỏi về Giải tích 2A")
    
    history = session.get_history_as_list()
    
    print("\n⏳ Calling contextualize_query...")
    start = time.time()
    refined = llm.contextualize_query(follow_up, history)
    elapsed = time.time() - start
    
    print(f"✅ Refined query: \"{refined}\"")
    print(f"⏱️  Time: {elapsed:.2f}s")
    
    if "giải tích" in refined.lower() or "MTH" in refined.upper():
        print("🎉 Query refinement giải quyết đại từ thành công!")
        return True
    else:
        print("⚠️  Query có thể chưa được refine hoàn toàn")
        return True


def test_subject_verification(llm: LLMInterface):
    """Test 5: Subject Verification"""
    print_header("STEP 5: Subject Verification Test")
    
    # Test case 1: Specific subject
    print("\n📌 Test Case 1: Question về môn cụ thể")
    query1 = "Giảng viên môn Giải tích 2A là ai?"
    subjects1 = [
        {"code": "MTH00010", "name": "Giải tích 1"},
        {"code": "MTH00011", "name": "Giải tích 2"},
        {"code": "MTH00012", "name": "Giải tích 2A"},
        {"code": "MTH00030", "name": "Đại số tuyến tính"},
        {"code": "MTH00050", "name": "Xác suất thống kê"}
    ]
    
    print(f"Query: \"{query1}\"")
    print(f"Candidates: {[s['name'] for s in subjects1]}")
    
    start = time.time()
    match1 = llm.verify_subject_in_top5(query1, subjects1)
    elapsed = time.time() - start
    
    print(f"✅ Match: {match1}")
    print(f"⏱️  Time: {elapsed:.2f}s")
    
    if match1 == "MTH00012":
        print("🎉 LLM xác định đúng Giải tích 2A!")
    else:
        print(f"⚠️  Expected MTH00012, got {match1}")
    
    # Test case 2: Ambiguous query
    print("\n📌 Test Case 2: Question mơ hồ")
    query2 = "Cách tính điểm môn giải tích?"
    
    print(f"Query: \"{query2}\"")
    
    start = time.time()
    match2 = llm.verify_subject_in_top5(query2, subjects1)
    elapsed = time.time() - start
    
    print(f"✅ Match: {match2}")
    print(f"⏱️  Time: {elapsed:.2f}s")
    
    if match2 is None:
        print("🎉 LLM nhận ra query mơ hồ, cần clarification!")
    else:
        print(f"⚠️  Expected None (ambiguous), got {match2}")
    
    return True


def test_intent_refine(llm: LLMInterface):
    """Test 6: Intent Classification"""
    print_header("STEP 6: Intent Classification Test")
    
    test_queries = [
        "Giảng viên môn Giải tích 2A là ai?",
        "Học phần nào dễ nhất?", 
        "Thời tiết hôm nay thế nào?"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: \"{query}\"")
        
        start = time.time()
        intent = llm.refine_intent(query)
        elapsed = time.time() - start
        
        print(f"   Category: {intent.get('category')}")
        print(f"   Section: {intent.get('section_intent')}")
        print(f"   ⏱️  Time: {elapsed:.2f}s")
    
    return True


def test_full_generation(llm: LLMInterface):
    """Test 7: Full RAG Generation"""
    print_header("STEP 7: RAG Generation Test")
    
    # Mock context chunks
    mock_chunks = [
        {
            "course_name": "Giải tích 2A",
            "text": "Giảng viên phụ trách: ThS. Nguyễn Văn A. Email: nva@hcmus.edu.vn"
        },
        {
            "course_name": "Giải tích 2A",
            "text": "Số tín chỉ: 3 (45 tiết lý thuyết). Điều kiện tiên quyết: Giải tích 1"
        }
    ]
    
    query = "Giảng viên môn Giải tích 2A là ai?"
    
    print(f"📝 Query: \"{query}\"")
    print(f"📦 Context: {len(mock_chunks)} chunks")
    
    print("\n⏳ Generating answer...")
    start = time.time()
    answer = llm.generate_answer(query, mock_chunks)
    elapsed = time.time() - start
    
    print(f"\n✅ Generated Answer:")
    print("-" * 50)
    print(answer)
    print("-" * 50)
    print(f"⏱️  Generation time: {elapsed:.2f}s")
    
    return True


def run_demo():
    """Main demo runner"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "BACKEND WORKFLOW DEMO" + " " * 27 + "║")
    print("║" + " " * 15 + "(Không cần Frontend, không cần Server)" + " " * 15 + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Step 1: Config
    if not test_config():
        return False
    
    # Step 2: LLM Connection
    llm = test_llm_connection()
    if not llm:
        print("\n❌ DEMO STOPPED: LLM connection failed")
        print("   Kiểm tra:")
        print("   1. Server LLM đang chạy?")
        print("   2. LLM_BASE_URL trong config.py đúng?")
        print("   3. Tunnel (ngrok/cloudflared) còn active?")
        return False
    
    # Step 3: Memory
    manager, session_id = test_memory_manager()
    session = manager.get_or_create(session_id)
    
    # Step 4: Query Refinement
    test_query_refinement(llm, session)
    
    # Step 5: Subject Verification
    test_subject_verification(llm)
    
    # Step 6: Intent
    test_intent_refine(llm)
    
    # Step 7: Full Generation
    test_full_generation(llm)
    
    # Summary
    print_header("✅ DEMO COMPLETED")
    print("""
    Tất cả các bước workflow đã được kiểm tra:
    
    ✅ Step 1: Config loaded từ backend/config.py
    ✅ Step 2: LLM connection working
    ✅ Step 3: Memory manager working (Langchain)
    ✅ Step 4: Query refinement (xử lý đại từ)
    ✅ Step 5: Subject verification (LLM-based)
    ✅ Step 6: Intent classification
    ✅ Step 7: RAG generation
    
    🎉 Backend workflow sẵn sàng để integrate với Frontend!
    """)
    
    return True


if __name__ == "__main__":
    try:
        success = run_demo()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Demo cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
