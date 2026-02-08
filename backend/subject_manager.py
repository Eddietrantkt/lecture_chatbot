import json
import re
import logging
from typing import List, Dict, Set, Optional
from collections import defaultdict
import unicodedata

logger = logging.getLogger("SubjectManager")

def normalize_text(text: str, remove_accents: bool = False) -> str:
    """
    Normalize text: lower case, remove accents if requested, remove special chars
    """
    if not text:
        return ""

    # Lowercase
    text = text.lower()

    if remove_accents:
        # Standard approach to remove Vietnamese accents
        s1 = u'ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẶặẸẹẺẻẼẽẾếỀềỂểỄễỆệỈỉỊịỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỴỵỶỷỸỹ'
        s0 = u'AAAAEEEIIOOOOUUYaaaaeeeiiiiiioooouuyAaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYy'
        s = ''
        for c in text:
            if c in s1:
                s += s0[s1.index(c)]
            else:
                s += c
        text = s

    # Remove extra spaces and punctuation
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

class SubjectInfo:
    def __init__(self, code: str, name: str, name_en: str = "", department: str = "", is_major: bool = False):
        self.code = code
        self.name = name
        self.name_en = name_en
        self.department = department
        self.is_major = is_major

    def __repr__(self):
        return f"[{'MAJOR' if self.is_major else 'COURSE'}] {self.code} - {self.name}"

    def __eq__(self, other):
        return self.code == other.code

    def __hash__(self):
        return hash(self.code)

class SubjectManager:
    def __init__(self, data_path: str = None):
        # Separated Registries
        self.courses: Dict[str, SubjectInfo] = {} # Map code -> SubjectInfo (Courses)
        self.majors: Dict[str, SubjectInfo] = {}  # Map code -> SubjectInfo (Majors)

        # Separated Indices
        self.course_index: Dict[str, Set[str]] = defaultdict(set)
        self.major_index: Dict[str, Set[str]] = defaultdict(set)

        self.all_chunks = [] # Store all chunks for direct access

        self.stop_words = {
            "học", "phần", "lý", "thuyết", "thực", "hành", "và", "của", "đại", "cương",
            "nhập", "cơ", "bản", "giới", "thiệu", "các", "những", "về", "trong", "cho", "với",
            "1", "2", "3", "i", "ii", "iii"
        }

        if data_path:
            self.load_data(data_path)

    def load_data(self, data_path: str):
        """Load data from chunked_data.json"""
        logger.info(f"Loading data from {data_path}...")
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.all_chunks = data # Store raw chunks

            # Extract unique subjects/majors
            for item in data:
                code = item.get('course_code', '').strip().rstrip('.')
                name = item.get('course_name', '').strip()
                name_en = item.get('course_name_en', '').strip()
                dept = item.get('department', '').strip()
                is_major = item.get('type') == 'MAJOR'

                if not code:
                    continue

                target_dict = self.majors if is_major else self.courses

                # Add to appropriate map if new
                if code not in target_dict:
                    target_dict[code] = SubjectInfo(code, name, name_en, dept, bool(is_major))
                else:
                    # Handle collision
                    existing_subj = target_dict[code]
                    if existing_subj.name != name:
                        # Simple collision resolution
                        new_code = f"{code}_v2"
                        # In production we might want a better strategy, but this persists existing logic
                        if new_code not in target_dict:
                            target_dict[new_code] = SubjectInfo(new_code, name, name_en, dept, bool(is_major))

            logger.info(f"Loaded {len(self.courses)} unique courses and {len(self.majors)} majors.")
            self.build_indices()

        except Exception as e:
            logger.error(f"Error loading data: {e}")

    def build_indices(self):
        """Build reverse indices for fast searching"""
        self._build_index_for_registry(self.courses, self.course_index)
        self._build_index_for_registry(self.majors, self.major_index)

    def _build_index_for_registry(self, registry: Dict[str, SubjectInfo], index: Dict[str, Set[str]]):
        for code, subject in registry.items():
            # Index by Code
            code_norm = normalize_text(code)
            index[code_norm].add(code)

            # Index by Name
            norm_name = normalize_text(subject.name)
            index[norm_name].add(code)

            no_accent_name = normalize_text(subject.name, remove_accents=True)
            if no_accent_name != norm_name:
                index[no_accent_name].add(code)

            # Index by Name EN
            if subject.name_en:
                index[normalize_text(subject.name_en)].add(code)

            # Index phrases
            self._index_phrases(norm_name, index, code)
            if no_accent_name != norm_name:
                self._index_phrases(no_accent_name, index, code)

    def _index_phrases(self, text: str, index: Dict[str, Set[str]], code: str):
        words = text.split()
        n_words = len(words)

        def is_valid_keyword(kw):
            parts = kw.split()
            if len(parts) > 2:
                return not all(p.isdigit() for p in parts)
            if len(parts) == 1:
                return len(kw) > 2 and kw not in self.stop_words
            if all(p in self.stop_words or p.isdigit() for p in parts):
                return False
            return True

        MAX_GRAM = 6
        for size in range(1, MAX_GRAM + 1):
            if size > n_words:
                break
            for i in range(n_words - size + 1):
                gram = " ".join(words[i : i+size])
                if is_valid_keyword(gram):
                    index[gram].add(code)

    def detect_courses(self, query: str) -> List[SubjectInfo]:
        """Detect COURSES in the query."""
        return self._detect_entities(query, self.courses, self.course_index)

    def detect_majors(self, query: str) -> List[SubjectInfo]:
        """Detect MAJORS in the query."""
        return self._detect_entities(query, self.majors, self.major_index)

    def _detect_entities(self, query: str, registry: Dict[str, SubjectInfo], index: Dict[str, Set[str]]) -> List[SubjectInfo]:
        query_norm = normalize_text(query)
        query_no_accent = normalize_text(query, remove_accents=True)
        query_tokens = set(query_norm.split())

        detected_codes = set()

        # 1. Exact Code Match in Query Words
        words = query_norm.split()
        for w in words:
            w_code = w.upper().rstrip('.')
            if w_code in registry:
                detected_codes.add(w_code)

        # 2. N-Gram Matching
        def find_grams(q_text):
            n_words = len(q_text.split())
            q_words = q_text.split()
            found = set()
            MAX_GRAM = 6
            for size in range(MAX_GRAM, 0, -1):
                if size > n_words:
                    continue
                for i in range(n_words - size + 1):
                    gram = " ".join(q_words[i : i+size])
                    if gram in index:
                        found.update(index[gram])
            return found

        detected_codes.update(find_grams(query_norm))
        detected_codes.update(find_grams(query_no_accent))

        # Retrieve objects
        candidates = [registry[c] for c in detected_codes if c in registry]

        # 3. Score and Sort
        def calculate_score(subj: SubjectInfo):
            score = 0
            s_name_norm = normalize_text(subj.name)
            s_name_no_accent = normalize_text(subj.name, remove_accents=True)

            # Substring match
            if s_name_norm in query_norm:
                score += 50
                score += len(s_name_norm)
            elif s_name_no_accent in query_no_accent:
                score += 40
                score += len(s_name_no_accent)

            # Token overlap
            s_tokens = set(s_name_norm.split())
            overlap = len(s_tokens & query_tokens)
            score += overlap * 5

            return score

        sorted_candidates = sorted(candidates, key=calculate_score, reverse=True)
        return sorted_candidates

    def get_subject_by_code(self, code: str) -> Optional[SubjectInfo]:
        """Generic lookup for both courses and majors"""
        if code in self.courses:
            return self.courses[code]
        if code in self.majors:
            return self.majors[code]
        return None

    def get_all_chunks_by_code(self, code: str) -> List[Dict]:
        """
        Return all text chunks belonging to a specific course/major code.
        """
        if not self.all_chunks:
            return []

        code_norm = normalize_text(code)
        results = []
        for chunk in self.all_chunks:
            c_code = chunk.get('course_code', '').strip().rstrip('.')
            if normalize_text(c_code) == code_norm:
                results.append(chunk)
        return results
