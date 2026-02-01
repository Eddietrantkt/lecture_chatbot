import sys
import os
import json

# Fix utf-8 issue
sys.stdout.reconfigure(encoding='utf-8')

# Add core to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.adaptive_retriever import AdaptiveRetriever

def verify_system():
    print("Initializing Adaptive RAG System...")
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CHUNKS_FILE = os.path.join(BASE_DIR, "chunked_data.json")
    INDEX_DIR = os.path.join(BASE_DIR, "index")

    try:
        retriever = AdaptiveRetriever(index_dir=INDEX_DIR, chunks_file=CHUNKS_FILE)
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return

    # Test Cases
    test_queries = [
        {
            "query": "Chào bạn, bạn có khỏe không?",
            "expected_intent": "IRRELEVANT",
            "desc": "Testing IRRELEVANT (Local Router - Greetings)"
        },
        {
            "query": "Quy chế thi kết thúc học phần như thế nào?",
            "expected_intent": "GENERAL_ACADEMIC",
            "desc": "Testing GENERAL_ACADEMIC (Local Router - No Subject)"
        },
        {
            "query": "Giảng viên môn Giải tích 1 là ai?",
            "expected_intent": "SPECIFIC_COURSE",
            "desc": "Testing SPECIFIC_COURSE (Subject Detected)"
        },
        {
             "query": "thông tin giảng viên môn cơ học lý thuyết",
             "expected_intent": "SPECIFIC_COURSE",
             "desc": "Testing Long Subject Name + Section Intent (Local Map)"
        },
        {
             "query": "giảng viên môn giải tích là ai",
             "expected_intent": "SPECIFIC_COURSE",
             "desc": "Testing Ambiguity: Expected Subject List (Multiple Matches)"
        }
    ]

    print("\n" + "="*50)
    print("STARTING VERIFICATION (PHASE 5: AMBIGUITY HANDLING)")
    print("="*50)

    for case in test_queries:
        print(f"\n>> TEST: {case['desc']}")
        print(f"Query: {case['query']}")
        
        try:
            result = retriever.search_and_answer(case['query'])
            
            detected_intent = result.get('intent', 'UNKNOWN')
            answer = result.get('answer', '')
            sources = result.get('sources', [])
            subjects = result.get('subjects', [])
            
            print(f"Detected Intent: {detected_intent}")
            print(f"Sources Found: {len(sources)}")
            print(f"Subjects Found: {len(subjects)}")
            print(f"Answer Start: {answer[:100]}...")
            
            # Validation
            if detected_intent == case['expected_intent']:
                print("✅ Intent Check: PASSED")
            else:
                 print(f"❌ Intent Check: FAILED (Expected {case['expected_intent']}, got {detected_intent})")

            # Check Ambiguity Handling
            if "Ambiguity" in case['desc']:
                if len(subjects) > 1 and len(sources) == 0 and "Bạn muốn hỏi về môn cụ thể nào" in answer:
                     print("✅ Ambiguity Handler Check: PASSED (Subject List Returned)")
                else:
                     print(f"❌ Ambiguity Handler Check: FAILED (Subjects: {len(subjects)}, Sources: {len(sources)})")

        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*50)
    print("VERIFICATION COMPLETE")
    print("="*50)

if __name__ == "__main__":
    verify_system()
