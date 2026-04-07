"""
Script để chunking các file JSON học phần với việc giữ lại tên học phần
cho mỗi chunk để đảm bảo ngữ nghĩa khi retrieval.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
import re
import sys

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


class CourseChunker:
    def __init__(self, max_chunk_size: int = 512):
        """
        Khởi tạo CourseChunker
        
        Args:
            max_chunk_size: Kích thước tối đa của mỗi chunk (số ký tự)
        """
        self.max_chunk_size = max_chunk_size
        self.chunks = []

    @staticmethod
    def get_section(sections: Dict[str, Any], target_name: str) -> List[str]:
        """Get a section while tolerating minor heading punctuation variants."""
        target = target_name.strip().rstrip(":").strip().lower()
        for section_name, content in sections.items():
            normalized = section_name.strip().rstrip(":").strip().lower()
            if normalized == target:
                return content
        return []
    
    def extract_course_info(self, filepath: str, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Trích xuất thông tin cơ bản về học phần từ JSON
        
        Args:
            filepath: Đường dẫn file
            data: Dữ liệu JSON
            
        Returns:
            Dictionary chứa thông tin học phần
        """
        course_info = {
            "file_name": Path(filepath).stem,
            "course_code": "",
            "course_name": "",
            "course_name_en": "",
            "department": ""
        }
        
        # Trích xuất từ file name
        filename_parts = Path(filepath).stem.split("_")
        if filename_parts:
            course_info["course_code"] = filename_parts[0]
        
        # Trích xuất từ sections
        sections = data.get("sections", {})
        general_info = self.get_section(sections, "Thông tin chung về học phần")
        
        for item in general_info:
            if "Mã học phần:" in item:
                code = item.split("Mã học phần:")[-1].strip().rstrip(".")
                if code and code != "Chưa có":
                    course_info["course_code"] = code
            elif "Tên học phần:" in item and "bằng tiếng Anh" not in item:
                course_info["course_name"] = item.split("Tên học phần:")[-1].strip()
            elif "Tên học phần bằng tiếng Anh:" in item:
                course_info["course_name_en"] = item.split("Tên học phần bằng tiếng Anh:")[-1].strip()
            elif "Bộ môn phụ trách học phần:" in item:
                course_info["department"] = item.split("Bộ môn phụ trách học phần:")[-1].strip()
        
        return course_info
    
    def create_chunk_metadata(self, course_info: Dict[str, str], section_name: str) -> str:
        """
        Tạo metadata prefix cho mỗi chunk
        Format: Môn học: {Name} ({Code}) - {Section}
        """
        metadata_parts = []
        
        # Đưa Tên môn học lên đầu để tăng trọng số Semantic Search
        if course_info["course_name"]:
            metadata_parts.append(f"{course_info['course_name']}")
        elif course_info["course_code"]:
            # Fallback nếu không có tên
            metadata_parts.append(f"{course_info['course_code']}")
            
        if section_name:
            metadata_parts.append(f"- {section_name}:")
        
        return " ".join(metadata_parts) + "\n"
    
    def split_text_smart(self, text: str, max_size: int) -> List[str]:
        """
        Chia text thành các chunks nhỏ hơn một cách thông minh
        
        Args:
            text: Text cần chia
            max_size: Kích thước tối đa
            
        Returns:
            List các text chunks
        """
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        # Ưu tiên chia theo dấu xuống dòng
        paragraphs = text.split('\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 1 <= max_size:
                current_chunk += para + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Nếu paragraph quá dài, chia nhỏ hơn
                if len(para) > max_size:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    temp_chunk = ""
                    for sent in sentences:
                        if len(temp_chunk) + len(sent) + 1 <= max_size:
                            temp_chunk += sent + " "
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                            temp_chunk = sent + " "
                    current_chunk = temp_chunk
                else:
                    current_chunk = para + "\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def chunk_section(self, course_info: Dict[str, str], section_name: str, 
                     section_content: List[str]) -> List[Dict[str, Any]]:
        """
        Chunk một section của học phần
        
        Args:
            course_info: Thông tin học phần
            section_name: Tên section
            section_content: Nội dung section
            
        Returns:
            List các chunks với metadata
        """
        chunks = []
        metadata_prefix = self.create_chunk_metadata(course_info, section_name)
        
        # Gộp tất cả content lại
        full_content = "\n".join(section_content)
        
        # Tính toán kích thước còn lại cho content
        remaining_size = self.max_chunk_size - len(metadata_prefix)
        
        # Chia content thành các chunks
        content_chunks = self.split_text_smart(full_content, remaining_size)
        
        # Tạo chunk với metadata
        for i, content_chunk in enumerate(content_chunks):
            # Tạo embedding_text = section_name + course_name (CHỈ embed 2 thứ này)
            embedding_text = f"{section_name} - {course_info['course_name']}"
            
            chunk_data = {
                "course_code": course_info["course_code"],
                "course_name": course_info["course_name"],
                "course_name_en": course_info["course_name_en"],
                "department": course_info["department"],
                "section_name": section_name,
                "chunk_index": i,
                "total_chunks": len(content_chunks),
                "text": metadata_prefix + content_chunk,
                "content_only": content_chunk,
                "embedding_text": embedding_text  # Field dùng để embedding
            }
            chunks.append(chunk_data)
        
        return chunks
    
    def process_file(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Xử lý một file JSON
        
        Args:
            filepath: Đường dẫn đến file JSON
            
        Returns:
            List các chunks
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Trích xuất thông tin học phần
            course_info = self.extract_course_info(filepath, data)
            
            # Chunk từng section
            file_chunks = []
            sections = data.get("sections", {})
            
            for section_name, section_content in sections.items():
                if section_content:  # Chỉ xử lý nếu có content
                    section_chunks = self.chunk_section(
                        course_info, 
                        section_name, 
                        section_content
                    )
                    file_chunks.extend(section_chunks)
            
            return file_chunks
        
        except Exception as e:
            print(f"Lỗi khi xử lý file {filepath}: {str(e)}")
            return []
    
    def process_directory(self, directory: str) -> List[Dict[str, Any]]:
        """
        Xử lý tất cả các file JSON trong thư mục và thư mục con
        
        Args:
            directory: Đường dẫn thư mục gốc
            
        Returns:
            List tất cả chunks từ tất cả các file
        """
        all_chunks = []
        json_files = []
        # Chỉ quét các folder bắt đầu bằng BM_
        for root, dirs, files in os.walk(directory):
            # Kiểm tra nếu thư mục hiện tại hoặc thư mục cha có chứa "BM_"
            path_parts = Path(root).parts
            if any("BM_" in part for part in path_parts):
                for file in files:
                    if file.endswith(".json"):
                        json_files.append(Path(root) / file)
        
        # Filter (giữ lại logic cũ để loại bỏ file rác nếu có)
        json_files = [
            f for f in json_files 
            if f.name != "chunked_data.json" 
            and not f.name.startswith("CTDT_")
            and "index" not in f.parts
            and ".git" not in f.parts
        ]
        
        print(f"Tìm thấy {len(json_files)} file JSON")
        
        for i, filepath in enumerate(json_files, 1):
            print(f"Đang xử lý [{i}/{len(json_files)}]: {filepath.name}")
            chunks = self.process_file(str(filepath))
            all_chunks.extend(chunks)
            print(f"  → Tạo được {len(chunks)} chunks")
        
        print(f"\nTổng cộng: {len(all_chunks)} chunks từ {len(json_files)} file")
        return all_chunks
    
    def save_chunks(self, chunks: List[Dict[str, Any]], output_file: str):
        """
        Lưu chunks vào file JSON
        
        Args:
            chunks: List các chunks
            output_file: Đường dẫn file output
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        
        print(f"Đã lưu {len(chunks)} chunks vào {output_file}")


def main():
    """
    Hàm main để chạy script
    """
    # Cấu hình
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    
    # OUTPUT_FILE sẽ nằm ở PROJECT_ROOT
    OUTPUT_FILE = os.path.join(PROJECT_ROOT, "chunked_data.json")
    CHUNK_SIZE = 512  # Kích thước mỗi chunk
    
    # Khởi tạo chunker
    chunker = CourseChunker(max_chunk_size=CHUNK_SIZE)
    
    # Xử lý tất cả các file trong PROJECT_ROOT (đệ quy)
    print("=" * 60)
    print("BẮT ĐẦU CHUNKING DỮ LIỆU HỌC PHẦN")
    print(f"Scanning directory: {PROJECT_ROOT}")
    print("=" * 60)
    
    all_chunks = chunker.process_directory(PROJECT_ROOT)
    
    # Lưu kết quả
    chunker.save_chunks(all_chunks, OUTPUT_FILE)
    
    # Thống kê
    print("\n" + "=" * 60)
    print("THỐNG KÊ")
    print("=" * 60)
    print(f"Tổng số chunks: {len(all_chunks)}")
    
    if all_chunks:
        avg_length = sum(len(c['text']) for c in all_chunks) / len(all_chunks)
        print(f"Độ dài trung bình: {avg_length:.0f} ký tự")
        print(f"Chunk ngắn nhất: {min(len(c['text']) for c in all_chunks)} ký tự")
        print(f"Chunk dài nhất: {max(len(c['text']) for c in all_chunks)} ký tự")
        
        # Thống kê theo bộ môn
        departments = {}
        for chunk in all_chunks:
            dept = chunk.get('department', 'Unknown')
            departments[dept] = departments.get(dept, 0) + 1
        
        print("\nPhân bố theo bộ môn:")
        for dept, count in sorted(departments.items(), key=lambda x: x[1], reverse=True):
            print(f"  {dept}: {count} chunks")
    
    print("\n✓ Hoàn thành!")


if __name__ == "__main__":
    main()
