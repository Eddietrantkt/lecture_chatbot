import os
import sys
import io

# Robust fix for Vietnamese display in Windows terminal
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # Set both input and output console code pages to UTF-8
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        os.system('chcp 65001 > nul')
    
    # Force UTF-8 encoding for stdout, stderr, and stdin
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')
        
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    else:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='backslashreplace')

    if hasattr(sys.stdin, 'reconfigure'):
        sys.stdin.reconfigure(encoding='utf-8', errors='backslashreplace')
    else:
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='backslashreplace')

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.adaptive_retriever import AdaptiveRetriever

def print_result(result):
    chunk = result['chunk']
    print(f"\n  Môn học: {chunk.get('course_name', 'N/A')} ({chunk.get('course_code')})")
    print(f"  Section: {chunk.get('section_name', 'N/A')}")
    print(f"  Nội dung preview: {chunk['text'][:150]}...")
    print("-" * 40)

def main():
    # Cấu hình đường dẫn (Điều chỉnh nếu cần)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CHUNKS_FILE = os.path.join(BASE_DIR, "index", "chunks.json")
    INDEX_DIR = os.path.join(BASE_DIR, "index")
    
    print("=" * 60)
    print("DEMO ADAPTIVE RAG (SUBJECT-AWARE ROUTER)")
    print("=" * 60)
    
    # Auto-indexing check
    try:
        retriever = AdaptiveRetriever(INDEX_DIR, CHUNKS_FILE)
    except FileNotFoundError:
        print("\n[!] CHƯA CÓ INDEX: Hệ thống sẽ tự động khởi tạo dữ liệu lần đầu (mất vài phút)...")
        import subprocess
        
        indexing_script = os.path.join(BASE_DIR, "script", "embedding_indexing_script.py")
        try:
            subprocess.run([sys.executable, indexing_script], check=True)
            print("\n[V] Đã tạo index xong! Đang khởi động lại hệ thống...")
            retriever = AdaptiveRetriever(INDEX_DIR, CHUNKS_FILE)
        except Exception as e:
            print(f"\n[X] Lỗi nghiêm trọng khi tạo index: {e}")
            return
    except Exception as e:
        print(f"Lỗi khởi tạo: {e}")
        return

    print("\nHệ thống đã sẵn sàng! Có thể xử lý:")
    print("1. Hỏi cụ thể: 'giảng viên môn Cơ học lý thuyết'")
    print("2. Hỏi nhập nhằng: 'tài liệu môn Cơ học' (Tìm cả Cơ học lý thuyết, Cơ học chất lỏng...)")
    print("3. Hỏi chung: 'môn nào học về đạo hàm'")
    print("\n(Gõ 'exit' để thoát)\n")
    
    while True:
        try:
            # Use raw_input/input and sanitize immediately
            raw_query = input("Nhập câu hỏi của bạn: ")
            # Remove surrogate characters that crash the terminal
            query = raw_query.encode('utf-8', 'ignore').decode('utf-8').strip()
        except EOFError:
            break
            
        if query.lower() in ['exit', 'quit', 'q']:
            break
        
        if not query:
            continue
            
        try:
            print(f"\nĐang xử lý câu hỏi: '{query}'...")
        except UnicodeEncodeError:
            print(f"\nĐang xử lý câu hỏi...")
        
        response = retriever.search_and_answer(query, top_k=5)
        
        intent = response.get('intent', 'UNKNOWN')
        subjects = response.get('subjects', [])
        results = response.get('sources', [])
        llm_answer = response.get('answer', 'No answer generated.')
        
        print("\n" + "=" * 20 + " KẾT QUẢ PHÂN TÍCH " + "=" * 20)
        print(f"Intent Strategy: {intent}")
        if subjects:
            print(f"Detected Subjects ({len(subjects)}):")
            for subj in subjects:
                print(f"  - {subj}")
        else:
            print("Detected Subjects: None (Searching Global)")
            
        print("\n" + "=" * 20 + " Chatbot trả lời " + "=" * 20)
        print(llm_answer)
        
        print("\n" + "=" * 20 + " Kết quả tìm kiếm chi tiết " + "=" * 20)
        
        if not results:
            print("Không tìm thấy kết quả nào.")
        else:
            # Group results by course for better readability if Multi-subject
            if len(subjects) > 1:
                # Nếu tìm thấy nhiều môn, group lại cho dễ nhìn
                results_by_course = {}
                for r in results:
                    c_name = r['chunk'].get('course_name', 'Other')
                    if c_name not in results_by_course:
                        results_by_course[c_name] = []
                    results_by_course[c_name].append(r)
                
                for course, items in results_by_course.items():
                    print(f"\n>>> TỪ MÔN: {course}")
                    for item in items:
                        print_result(item)
            else:
                # In bình thường
                for item in results:
                    print_result(item)
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
