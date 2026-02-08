"""
Course Loader - Load full JSON file as context
Khi đã xác định được môn học, load toàn bộ file JSON gốc thay vì dùng chunks.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import unicodedata
import re

# Add Config import
from backend.config import Config

logger = logging.getLogger("CourseLoader")


def remove_accents(input_str):
    s1 = unicodedata.normalize('NFD', input_str)
    s2 = ''.join(c for c in s1 if unicodedata.category(c) != 'Mn')
    return s2.replace('đ', 'd').replace('Đ', 'D')



class CourseLoader:
    """Load và quản lý dữ liệu môn học từ metadata và file JSON gốc"""
    
    def __init__(self, index_dir: str):
        """
        Args:
            index_dir: Thư mục chứa course_metadata.json
        """
        self.index_dir = Path(index_dir)
        self.metadata_file = self.index_dir / "course_metadata.json"
        self.metadata: List[Dict] = []
        self._load_metadata()
    
    def _load_metadata(self):
        """Load course metadata từ file"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle new structure (Dict) vs old structure (List)
            if isinstance(data, list):
                self.metadata = data
                self.majors = []
            elif isinstance(data, dict):
                self.metadata = data.get("courses", [])
                self.majors = data.get("majors", [])
            
            logger.info(f"Loaded metadata for {len(self.metadata)} courses and {len(self.majors)} majors")
        else:
            logger.warning(f"Metadata file not found: {self.metadata_file}")
            self.metadata = []
            self.majors = []

    def get_all_courses_summary(self) -> str:
        """
        Tạo summary text của tất cả môn học để LLM có thể tìm kiếm.
        Format: course_name (course_code) - Giảng viên: ...
        """
        lines = []
        # Add Majors
        for m in self.majors:
             lines.append(f"- NGÀNH: {m['major_name']} ({m['major_code']})")

        # Add Courses
        for m in self.metadata:
            lecturers = ", ".join(m.get('lecturers', [])) or "Chưa có"
            line = f"- {m['course_name']} ({m['course_code']}) - GV: {lecturers}"
            lines.append(line)
        return "\n".join(lines)
    
    def find_course_by_code(self, course_code: str) -> Optional[Dict]:
        """Tìm metadata của môn học theo mã"""
        for m in self.metadata:
            if m['course_code'].lower() == course_code.lower():
                return m
        return None
    
    def find_course_by_name(self, course_name: str) -> Optional[Dict]:
        """Tìm metadata của môn học theo tên (exact hoặc partial match, accent-insensitive)"""
        course_name_clean = remove_accents(course_name.lower())
        
        # 1. Exact match (ignore accents)
        for m in self.metadata:
            db_name_clean = remove_accents(m['course_name'].lower())
            if course_name_clean == db_name_clean:
                return m
        
        # 2. Contains match (ignore accents)
        for m in self.metadata:
            db_name_clean = remove_accents(m['course_name'].lower())
            if course_name_clean in db_name_clean:
                return m
        
        return None
    
    def load_full_course_json(self, course_code: str = None, course_name: str = None) -> Optional[Dict]:
        """
        Load toàn bộ file JSON gốc của môn học.
        
        Args:
            course_code: Mã môn học
            course_name: Tên môn học
            
        Returns:
            Dict chứa toàn bộ dữ liệu JSON hoặc None
        """
        # Tìm metadata
        meta = None
        
        # 1. Prioritize finding by Name (Exact or Partial Match in Metadata)
        # This resolves collisions where multiple courses have "MTHxxxxx" but different names.
        if course_name:
            meta = self.find_course_by_name(course_name)
        
        # 2. If valid Code provided and Name check failed (or no name), try finding by Code
        # We only do this if we haven't found metadata yet, OR if the found metadata likely matches the code.
        if not meta and course_code:
             meta = self.find_course_by_code(course_code)

        # 2. If not found by code (or collision detected), try finding by Name
        if not meta and course_name:
            meta = self.find_course_by_name(course_name)
        
        if not meta:
            logger.warning(f"Course not found: code={course_code}, name={course_name}")
            return None
        
        # Load file JSON gốc
        file_path = meta.get('file_path')

        # FIXED: Use consistent path resolution with Config.BASE_DIR
        if file_path and not os.path.isabs(file_path):
            # Relative path -> Join with BASE_DIR
            file_path = os.path.join(Config.BASE_DIR, file_path)

        if not file_path or not os.path.exists(file_path):
            logger.error(f"Course file not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Thêm metadata vào data
            data['_metadata'] = {
                'course_code': meta['course_code'],
                'course_name': meta['course_name'],
                'course_name_en': meta.get('course_name_en', ''),
                'department': meta.get('department', ''),
                'lecturers': meta.get('lecturers', []),
                'file_path': file_path
            }
            
            logger.info(f"Loaded full JSON for: {meta['course_name']}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return None
    
    def format_course_as_context(self, course_data: Dict) -> str:
        """
        Format toàn bộ dữ liệu môn học thành text context cho LLM.
        
        Args:
            course_data: Dữ liệu JSON đầy đủ của môn học
            
        Returns:
            String context
        """
        if not course_data:
            return ""
        
        meta = course_data.get('_metadata', {})
        sections = course_data.get('sections', {})
        
        lines = []
        lines.append(f"# {meta.get('course_name', 'Unknown')} ({meta.get('course_code', '')})")
        lines.append(f"**Tên tiếng Anh:** {meta.get('course_name_en', 'N/A')}")
        lines.append(f"**Bộ môn:** {meta.get('department', 'N/A')}")
        lines.append(f"**Giảng viên:** {', '.join(meta.get('lecturers', [])) or 'N/A'}")
        lines.append("")
        
        for section_name, content in sections.items():
            lines.append(f"## {section_name}")
            if isinstance(content, list):
                for item in content:
                    lines.append(f"- {item}")
            else:
                lines.append(str(content))
            lines.append("")
        
        return "\n".join(lines)
    
    def search_by_lecturer(self, lecturer_name: str) -> List[Dict]:
        """Tìm tất cả môn học của một giảng viên"""
        results = []
        lecturer_lower = lecturer_name.lower()
        
        for m in self.metadata:
            for lec in m.get('lecturers', []):
                if lecturer_lower in lec.lower():
                    results.append(m)
                    break
        
        return results

    
    def get_course_list_for_matching(self) -> List[Dict[str, str]]:
        """
        Returns a simplified list of all courses AND majors for LLM matching.
        FIXED: Now includes majors, not just courses
        """
        results = []

        # Add courses
        for m in self.metadata:
            results.append({
                "code": m["course_code"],
                "name": m["course_name"],
                "is_major": False
            })

        # Add majors (FIXED: was missing)
        for major in self.majors:
            results.append({
                "code": major.get("major_code", ""),
                "name": major.get("major_name", ""),
                "is_major": True
            })

        return results

    def get_all_majors_list(self) -> List[Dict[str, str]]:
        """Get summary list of all majors."""
        # Ensure we return a list of dicts with code and name
        results = []
        for m in self.majors:
            results.append({
                "code": m.get("major_code", ""),
                "name": m.get("major_name", ""),
                "is_major": True
            })
        return results

    def get_major_by_code(self, code: str) -> Optional[Dict]:
        """Get major metadata by code."""
        for major in self.majors:
            if major.get("major_code") == code:
                return major
        return None

    def get_major_by_name(self, name: str) -> Optional[Dict]:
        """Get major metadata by name (fuzzy match)."""
        name_lower = name.lower()
        for major in self.majors:
            if major.get("major_name", "").lower() in name_lower:
                return major
        return None

    def get_major_full_details(self, code: str) -> Optional[Dict]:
        """
        Get full major details, loading from file if necessary.
        Returns dict with keys: major_code, major_name, courses_list, etc.
        """
        # 1. Get metadata
        meta = self.get_major_by_code(code)
        if not meta:
            return None
        
        # 2. Check if courses_list is already in metadata
        if "courses_list" in meta and meta["courses_list"]:
            return meta
            
        # 3. Load from file_path if valid
        file_path = meta.get("file_path")
        if file_path:
            # FIXED: Use Config.BASE_DIR for consistent path resolution
            if not os.path.isabs(file_path):
                full_path = os.path.join(Config.BASE_DIR, file_path)
            else:
                full_path = file_path
            
            if os.path.exists(full_path):
                try:
                    import json
                    import re
                    with open(full_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Logically extract courses (Recursive logic)
                    courses_list = []
                    sections = data.get("sections", {})
                    
                    def extract_from_section(content):
                        if isinstance(content, list):
                            for line in content:
                                if isinstance(line, dict):
                                     code = line.get("Ma_HP")
                                     name = line.get("Ten_HP")
                                     if code and name:
                                         courses_list.append({
                                             "code": code,
                                             "name": name,
                                             "type": "Tự chọn"
                                         })
                                elif isinstance(line, str):
                                    match = re.match(r'^\d+,\s*([A-Z0-9]+)\s*,\s*([^,]+),', line)
                                    if match:
                                        c_code = match.group(1).strip()
                                        c_name = match.group(2).strip()

                                        courses_list.append({
                                            "code": c_code,
                                            "name": c_name,
                                            "type": "Bắt buộc" if "BB" in line else "Tự chọn"
                                        })

                        elif isinstance(content, dict):
                            for k, v in content.items():
                                extract_from_section(v)

                    extract_from_section(sections)

                                    
                    # Return combined info
                    result = meta.copy()
                    result["courses_list"] = courses_list
                    return result
                    
                except Exception as e:
                    logger.error(f"Error loading full major JSON from {full_path}: {e}")
                    return meta
            else:
                logger.warning(f"Major file path not found: {full_path}")
                
        return meta
