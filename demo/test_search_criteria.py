import json
import sys
import os
from embedding_indexing_script import HybridRetriever

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def run_test_case(retriever, query, expected_course_keyword, expected_context_keyword):
    print(f"\nTesting Query: '{query}'")
    print(f"  - Mong đợi môn học chứa: '{expected_course_keyword}'")
    print(f"  - Mong đợi ngữ cảnh chứa: '{expected_context_keyword}'")
    
    results = retriever.hybrid_search(query, top_k=5, alpha=0.5)
    
    found_match = False
    
    for i, result in enumerate(results, 1):
        chunk = result['chunk']
        score = result['score']
        
        metadata = chunk.get('metadata', {})
        course_name = chunk.get('course_name') or metadata.get('course_name', 'N/A')
        section_name = chunk.get('section_name') or metadata.get('section_name', 'N/A')
        text = chunk.get('text', '')
        
        is_course_match = expected_course_keyword.lower() in course_name.lower()
        is_context_match = expected_context_keyword.lower() in section_name.lower() or expected_context_keyword.lower() in text.lower()
        
        match_status = "❌"
        if is_course_match and is_context_match:
            match_status = "✅"
            found_match = True
        elif is_course_match:
            match_status = "⚠️ (Đúng môn, sai context)"
        elif is_context_match:
            match_status = "⚠️ (Sai môn, đúng context)"
            
        print(f"  [{i}] {match_status} Score: {score:.4f}")
        print(f"      Học phần: {course_name}")
        print(f"      Section: {section_name}")
        print(f"      Text start: {text[:50]}...")
        
        if found_match:
            print(f"\n  => TÌM THẤY KẾT QUẢ PHÙ HỢP TẠI VỊ TRÍ #{i}")
            return True
            
    print("\n  => KHÔNG TÌM THẤY KẾT QUẢ PHÙ HỢP TRONG TOP 5")
    return False

def main():
    print("=" * 60)
    print("KIỂM TRA TIÊU CHÍ: ĐÚNG MÔN HỌC & ĐÚNG CONTEXT")
    print("=" * 60)
    
    # Load index
    retriever = HybridRetriever()
    retriever.load_index("index/")
    
    # Test cases
    test_cases = [
        {
            "query": "giảng viên môn cơ học lý thuyết",
            "course": "Cơ học lý thuyết",
            "context": "giảng viên"
        },
        {
            "query": "tài liệu tham khảo đại số đại cương",
            "course": "Đại số đại cương",
            "context": "tài liệu"
        },
        {
            "query": "mục tiêu học phần giải tích số",
            "course": "Giải tích số",
            "context": "mục tiêu"
        }
    ]
    
    passed = 0
    for case in test_cases:
        if run_test_case(retriever, case["query"], case["course"], case["context"]):
            passed += 1
            
    print("\n" + "=" * 60)
    print(f"KẾT QUẢ: {passed}/{len(test_cases)} TEST CASES PASSED")
    print("=" * 60)

if __name__ == "__main__":
    main()
