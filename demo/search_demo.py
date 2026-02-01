"""
Script demo sử dụng hệ thống retrieval đã build
Ví dụ về cách query và lấy thông tin từ index
"""

import json
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from script.embedding_indexing_script import HybridRetriever


def pretty_print_result(result: dict, rank: int):
    """In kết quả một cách đẹp mắt"""
    chunk = result['chunk']
    score = result['score']
    
    print(f"\n{'='*70}")
    print(f"KẾT QUẢ #{rank} - Score: {score:.4f}")
    print(f"{'='*70}")
    print(f"📚 Học phần: {chunk.get('course_name', 'N/A')} ({chunk.get('course_code', 'N/A')})")
    print(f"🏫 Bộ môn: {chunk.get('department', 'N/A')}")
    print(f"📑 Section: {chunk.get('section_name', 'N/A')}")
    print(f"\n📝 Nội dung:")
    print(f"{'-'*70}")
    print(chunk.get('content_only', chunk.get('text', 'N/A'))[:500])
    if len(chunk.get('content_only', chunk.get('text', ''))) > 500:
        print("...")
    print(f"{'-'*70}")


def interactive_search(retriever: HybridRetriever):
    """Chế độ search interactive"""
    print("\n" + "="*70)
    print("HỆ THỐNG TÌM KIẾM THÔNG TIN HỌC PHẦN")
    print("="*70)
    print("Nhập 'quit' hoặc 'exit' để thoát")
    print("Nhập 'config' để thay đổi cấu hình")
    print("="*70 + "\n")
    
    # Cấu hình mặc định
    config = {
        'top_k': 5,
        'alpha': 0.5  # 0.5 = cân bằng giữa FAISS và BM25
    }
    
    while True:
        query = input("\n🔍 Nhập câu hỏi: ").strip()
        
        if query.lower() in ['quit', 'exit']:
            print("\n👋 Tạm biệt!")
            break
        
        if query.lower() == 'config':
            print("\nCấu hình hiện tại:")
            print(f"  - Số kết quả (top_k): {config['top_k']}")
            print(f"  - Alpha (FAISS weight): {config['alpha']}")
            
            try:
                new_top_k = input(f"Nhập top_k mới (enter để giữ nguyên {config['top_k']}): ").strip()
                if new_top_k:
                    config['top_k'] = int(new_top_k)
                
                new_alpha = input(f"Nhập alpha mới (0-1, enter để giữ nguyên {config['alpha']}): ").strip()
                if new_alpha:
                    config['alpha'] = float(new_alpha)
                
                print("✓ Đã cập nhật cấu hình!")
            except ValueError:
                print("⚠ Giá trị không hợp lệ, giữ nguyên cấu hình cũ")
            continue
        
        if not query:
            continue
        
        # Thực hiện search
        print(f"\n⏳ Đang tìm kiếm...")
        results = retriever.hybrid_search(
            query, 
            top_k=config['top_k'],
            alpha=config['alpha']
        )
        
        if not results:
            print("❌ Không tìm thấy kết quả nào!")
            continue
        
        print(f"\n✓ Tìm thấy {len(results)} kết quả:")
        
        for i, result in enumerate(results, 1):
            pretty_print_result(result, i)


def batch_search_example(retriever: HybridRetriever):
    """Ví dụ về batch search với nhiều câu hỏi"""
    
    queries = {
        "Thông tin giảng viên": [
            "thông tin giảng viên",
            "email liên hệ giảng viên",
            "giờ làm việc của giảng viên"
        ],
        "Học phần tiên quyết": [
            "học phần tiên quyết",
            "yêu cầu trước khi học",
            "điều kiện để đăng ký môn học"
        ],
        "Đánh giá": [
            "hình thức đánh giá",
            "tỷ lệ điểm",
            "thi cuối kỳ chiếm bao nhiêu phần trăm"
        ],
        "Tài liệu": [
            "giáo trình",
            "tài liệu tham khảo",
            "sách học"
        ]
    }
    
    print("\n" + "="*70)
    print("BATCH SEARCH - VÍ DỤ CÁC LOẠI CÂU HỎI")
    print("="*70)
    
    for category, query_list in queries.items():
        print(f"\n\n{'#'*70}")
        print(f"DANH MỤC: {category}")
        print(f"{'#'*70}")
        
        for query in query_list:
            print(f"\n{'='*70}")
            print(f"🔍 Query: '{query}'")
            print(f"{'='*70}")
            
            results = retriever.hybrid_search(query, top_k=3, alpha=0.5)
            
            for i, result in enumerate(results, 1):
                chunk = result['chunk']
                print(f"\n  [{i}] {chunk.get('course_name', 'N/A')} - "
                      f"{chunk.get('section_name', 'N/A')} (Score: {result['score']:.3f})")
                print(f"      {chunk.get('text', '')[:150]}...")


def export_results_to_json(results: list, output_file: str):
    """Export kết quả search ra file JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✓ Đã export kết quả ra {output_file}")


def main():
    """Hàm main"""
    # Adjusted to look one level up from 'demo' folder
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INDEX_DIR = os.path.join(BASE_DIR, "index")
    
    # Kiểm tra xem index đã được tạo chưa
    index_path = Path(INDEX_DIR)
    if not index_path.exists() or not (index_path / "faiss.index").exists():
        print("❌ Index chưa được tạo!")
        print("Vui lòng chạy embedding_indexing_script.py trước")
        return
    
    print("Đang load index...")
    retriever = HybridRetriever()
    retriever.load_index(INDEX_DIR)
    
    print("\n" + "="*70)
    print("HỆ THỐNG ĐÃ SẴN SÀNG!")
    print("="*70)
    
    # Chọn chế độ
    print("\nChọn chế độ:")
    print("  1. Interactive search (tìm kiếm tương tác)")
    print("  2. Batch search example (ví dụ batch search)")
    print("  3. Custom query")
    
    choice = input("\nNhập lựa chọn (1-3): ").strip()
    
    if choice == "1":
        interactive_search(retriever)
    elif choice == "2":
        batch_search_example(retriever)
    elif choice == "3":
        query = input("\nNhập câu hỏi: ").strip()
        if query:
            results = retriever.hybrid_search(query, top_k=5, alpha=0.5)
            for i, result in enumerate(results, 1):
                pretty_print_result(result, i)
            
            # Hỏi có muốn export không
            export = input("\nBạn có muốn export kết quả ra JSON? (y/n): ").strip().lower()
            if export == 'y':
                output_file = BASE_DIR + r"\search_results.json"
                export_results_to_json(results, output_file)
    else:
        print("Lựa chọn không hợp lệ!")


if __name__ == "__main__":
    main()
