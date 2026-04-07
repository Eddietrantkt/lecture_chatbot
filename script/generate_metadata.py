"""
Script tạo metadata cho tất cả môn học
Output: index/course_metadata.json

Chứa:
- course_name, course_code, course_name_en
- file_path (đường dẫn đầy đủ đến file JSON gốc)
- lecturers (danh sách giảng viên)
- department
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def extract_lecturer_name(lecturer_info: List[str]) -> List[str]:
    """Trích xuất tên giảng viên từ section 'Thông tin về giảng viên'"""
    lecturers = []
    for item in lecturer_info:
        if "Họ và tên:" in item:
            name = item.split("Họ và tên:")[-1].strip()
            if name and name != "…" and name != "...":
                lecturers.append(name)
    return lecturers


def get_section(sections: Dict[str, Any], target_name: str) -> List[str]:
    """Get a section while tolerating minor heading punctuation variants."""
    target = target_name.strip().rstrip(":").strip().lower()
    for section_name, content in sections.items():
        normalized = section_name.strip().rstrip(":").strip().lower()
        if normalized == target:
            return content
    return []


def extract_course_info(filepath: str, data: Dict[str, Any], project_root: str) -> Dict[str, Any]:
    """Trích xuất thông tin từ một file JSON môn học"""
    sections = data.get("sections", {})
    
    # Calculate relative path
    try:
        rel_path = os.path.relpath(filepath, project_root)
    except ValueError:
        rel_path = str(filepath)

    # Default values
    info = {
        "course_code": "",
        "course_name": "",
        "course_name_en": "",
        "department": "",
        "lecturers": [],
        "file_path": rel_path,
        "file_name": Path(filepath).name
    }
    
    # Extract từ Thông tin chung về học phần
    general_info = get_section(sections, "Thông tin chung về học phần")
    for item in general_info:
        if "Mã học phần:" in item:
            code = item.split("Mã học phần:")[-1].strip().rstrip(".")
            if code and code not in ["Chưa có", "…", "..."]:
                info["course_code"] = code
        elif "Tên học phần:" in item and "bằng tiếng Anh" not in item:
            info["course_name"] = item.split("Tên học phần:")[-1].strip()
        elif "Tên học phần bằng tiếng Anh:" in item:
            info["course_name_en"] = item.split("Tên học phần bằng tiếng Anh:")[-1].strip()
        elif "Bộ môn phụ trách học phần:" in item:
            info["department"] = item.split("Bộ môn phụ trách học phần:")[-1].strip()
    
    # Extract giảng viên
    lecturer_info = get_section(sections, "Thông tin về giảng viên")
    info["lecturers"] = extract_lecturer_name(lecturer_info)
    
    # Fallback: lấy course_code từ filename nếu chưa có
    if not info["course_code"]:
        filename_parts = Path(filepath).stem.split("_")
        if filename_parts:
            info["course_code"] = filename_parts[0]
    
    return info


def find_all_course_files(root_dir: str) -> List[str]:
    """Tìm tất cả file JSON trong thư mục BM_*"""
    json_files = []
    for root, dirs, files in os.walk(root_dir):
        path_parts = Path(root).parts
        if any("BM_" in part for part in path_parts):
            for file in files:
                if file.endswith(".json") and not file.startswith("CTDT_"):
                    json_files.append(str(Path(root) / file))
    return json_files


def main():
    # Cấu hình
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    OUTPUT_FILE = os.path.join(PROJECT_ROOT, "index", "course_metadata.json")
    
    print("=" * 60)
    print("TẠO COURSE METADATA")
    print("=" * 60)
    
    # Tìm tất cả file JSON
    json_files = find_all_course_files(PROJECT_ROOT)
    print(f"Tìm thấy {len(json_files)} file JSON")
    
    # Extract metadata
    metadata = []
    for filepath in json_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            info = extract_course_info(filepath, data, PROJECT_ROOT)
            metadata.append(info)
            print(f"  ✓ {info['course_name']} ({info['course_code']})")
        except Exception as e:
            print(f"  ✗ Lỗi {filepath}: {e}")
    
    # Lưu metadata
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Đã lưu metadata vào {OUTPUT_FILE}")
    print(f"  Tổng: {len(metadata)} môn học")
    
    # Thống kê giảng viên
    all_lecturers = set()
    for m in metadata:
        all_lecturers.update(m['lecturers'])
    print(f"  Giảng viên: {len(all_lecturers)} người")


if __name__ == "__main__":
    main()
