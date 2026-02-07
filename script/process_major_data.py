import json
import os
import re
from pathlib import Path

# Paths
BASE_DIR = Path("C:/Users/Admin/Downloads/POC1")
INDEX_DIR = BASE_DIR / "index"
METADATA_FILE = INDEX_DIR / "course_metadata.json"
CHUNKS_FILE = INDEX_DIR / "chunks.json"
MAJOR_FILE = BASE_DIR / "BM_Co_hoc/CTDT_K2024_Toan_hoc.json"

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_major_info(major_data):
    """
    Extract major metadata and course list from the specific CTDT format.
    """
    sections = major_data.get("sections", {})
    
    # 1. Basic Info
    # Try to find header or general info
    # Based on file inspection: "1. Thông tin chung về chương trình đào tạo"
    general_info = sections.get("1. Thông tin chung về chương trình đào tạo", [])
    
    major_name = "Toán học" # Fallback
    major_code = "7460101" # Fallback
    
    for line in general_info:
        if "Tên tiếng Việt:" in line:
            major_name = line.split(":", 1)[1].strip()
        if "Mã ngành đào tạo:" in line:
            major_code = line.split(":", 1)[1].strip().rstrip('.')

    # 2. Extract Courses List
    # From "7. Nội dung chương trình", "7.1...", "7.2..."
    # We look for lines like "1, MTH00010, Giải tích 1A, ..."
    course_list = []
    
    course_list = []
    
    def extract_from_section(content):
        if isinstance(content, list):
            for line in content:
                # Check for object format (in Appendix)
                if isinstance(line, dict):
                     # Handle dict object in list (Appendix format)
                     # item has "Ma_HP", "Ten_HP"
                     code = line.get("Ma_HP")
                     name = line.get("Ten_HP")
                     if code and name:
                         course_list.append({
                             "code": code,
                             "name": name,
                             "type": "Tự chọn" # Defaults in Appendix are often electives
                         })
                elif isinstance(line, str):
                    # Handle string line (CSV format)
                    # Regex to match CSV-like course lines: Number, Code, Name, Credits...
                    # Example: "1, MTH00010, Giải tích 1A, 3, ..."
                    match = re.match(r'^\d+,\s*([A-Z0-9]+)\s*,\s*([^,]+),', line)
                    if match:
                        code = match.group(1).strip()
                        name = match.group(2).strip()
                        if code and name and code != "Mã học phần":
                            course_list.append({
                                "code": code,
                                "name": name,
                                "type": "Bắt buộc" if "BB" in line else "Tự chọn"
                            })
        elif isinstance(content, dict):
            for k, v in content.items():
                extract_from_section(v)

    # Allow recursion on sections
    extract_from_section(sections)

    return {
        "major_code": major_code,
        "major_name": major_name,
        "major_name_en": "Mathematics", 
        "file_path": str(MAJOR_FILE.relative_to(BASE_DIR)).replace("\\", "/"),
        "file_name": MAJOR_FILE.name,
        "type": "MAJOR",
        "courses_list": course_list
    }

def create_major_chunks(major_data, major_meta):
    """
    Create searchable chunks from the Major JSON.
    """
    chunks = []
    sections = major_data.get("sections", {})
    
    for sec_name, content in sections.items():
        text_content = ""
        if isinstance(content, list):
            text_content = "\n".join(content)
        elif isinstance(content, str):
            text_content = content
        else:
            continue
            
        if not text_content.strip():
            continue
            
        # Create chunk
        chunk = {
            "text": f"{sec_name}\n{text_content}",
            "section_name": sec_name,
            "course_code": major_meta["major_code"], 
            "course_name": major_meta["major_name"],
            "type": "MAJOR", 
            "embedding_text": f"Ngành {major_meta['major_name']} - {sec_name}"
        }
        chunks.append(chunk)

    return chunks

def main():
    print("Processing Major Data...")
    
    # 1. Load Data
    if not MAJOR_FILE.exists():
        print(f"Error: Major file not found at {MAJOR_FILE}")
        return

    major_json = load_json(MAJOR_FILE)
    current_metadata = load_json(METADATA_FILE)
    current_chunks = load_json(CHUNKS_FILE)
    
    # 2. Extract Info
    major_info = extract_major_info(major_json)
    print(f"Extracted Major: {major_info['major_name']} ({major_info['major_code']})")

    
    # Filter out valid
    valid_courses = [c for c in major_info['courses_list'] if "không tồn tại" not in c['name'].lower()]
    major_info['courses_list'] = valid_courses
    
    print(f"Found {len(major_info['courses_list'])} courses in curriculum.")
    bb_count = sum(1 for c in valid_courses if c['type'] == 'Bắt buộc')
    tc_count = sum(1 for c in valid_courses if c['type'] == 'Tự chọn')
    print(f"Type breakdown: Bắt buộc={bb_count}, Tự chọn={tc_count}")

    
    # 3. Create Chunks for Major
    major_chunks = create_major_chunks(major_json, major_info)
    print(f"Created {len(major_chunks)} chunks for Major.")
    
    # 4. Update Metadata Structure
    if isinstance(current_metadata, list):
        new_metadata = {
            "courses": current_metadata,
            "majors": []
        }
    else:
        new_metadata = current_metadata
    
    # Add/Update Major in Metadata
    # Remove existing major with same code
    new_metadata["majors"] = [m for m in new_metadata.get("majors", []) if m["major_code"] != major_info["major_code"]]
    
    # Prepare major info for storage (remove courses_list)
    major_meta_storage = major_info.copy()
    if "courses_list" in major_meta_storage:
        del major_meta_storage["courses_list"]
        
    new_metadata["majors"].append(major_meta_storage)
    
    # 5. Add Chunks
    # Remove old chunks for this major to avoid duplicates
    # We identify chunks by 'course_code' == major_code AND 'type' == 'MAJOR' (if we added type before)
    # Or just by code if it doesn't overlap with course codes. 7460101 is distinct from MTH...
    
    # Filter out old major chunks
    final_chunks = [c for c in current_chunks if c.get("course_code") != major_info["major_code"]]
    final_chunks.extend(major_chunks)
    
    # 6. Save
    save_json(METADATA_FILE, new_metadata)
    save_json(CHUNKS_FILE, final_chunks)
    
    print("Optimization Complete.")
    print(f"Updated {METADATA_FILE}")
    print(f"Updated {CHUNKS_FILE}")

if __name__ == "__main__":
    main()
