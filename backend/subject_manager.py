import json
import re
from typing import List, Dict, Set, Optional
from collections import defaultdict
import unicodedata

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
    def __init__(self, code: str, name: str, name_en: str = "", department: str = ""):
        self.code = code
        self.name = name
        self.name_en = name_en
        self.department = department
        self.raw_data = {}  # Optional: keep sample raw data

    def __repr__(self):
        return f"[{self.code}] {self.name}"

    def __eq__(self, other):
        return self.code == other.code

    def __hash__(self):
        return hash(self.code)

class SubjectManager:
    def __init__(self, data_path: str = None):
        self.subjects: Dict[str, SubjectInfo] = {} # Map code -> SubjectInfo
        self.keyword_index: Dict[str, Set[str]] = defaultdict(set) # Map keyword/phrase -> Set of course_codes
        self.all_chunks = [] # Store all chunks for direct access
        
        # Stop words common in course names that we shouldn't use for partial matching alone
        self.stop_words = {
            "môn", "học", "phần", "lý", "thuyết", "thực", "hành", "và", "của", "đại", "cương", 
            "nhập", "cơ", "bản", "giới", "thiệu", "các", "những", "về", "trong", "cho", "với",
            "1", "2", "3", "i", "ii", "iii" # Generic numbers often cause noise if matched alone
        }
        
        if data_path:
            self.load_data(data_path)

    def load_data(self, data_path: str):
        """Load data from chunked_data.json"""
        print(f"Loading data from {data_path}...")
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.all_chunks = data # Store raw chunks
            
            # Extract unique subjects
            for item in data:
                code = item.get('course_code', '').strip().rstrip('.')
                name = item.get('course_name', '').strip()
                name_en = item.get('course_name_en', '').strip()
                dept = item.get('department', '').strip()
                
                if not code:
                    continue

                # Add to subjects map if new
                if code not in self.subjects:
                    self.subjects[code] = SubjectInfo(code, name, name_en, dept)
                else:
                    # [FIX]: Handle duplicate codes (collision)
                    # If same code but different name, append suffix to distinguish
                    existing_subj = self.subjects[code]
                    if existing_subj.name != name:
                        # Collision detected!
                        # Find a new unique code
                        suffix = 2
                        new_code = f"{code}_{suffix}"
                        while new_code in self.subjects:
                            suffix += 1
                            new_code = f"{code}_{suffix}"
                        
                        # Create new entry with unique code
                        self.subjects[new_code] = SubjectInfo(new_code, name, name_en, dept)
                        
                        # IMPORTANT: Update the chunk's course_code so subsequent lookups work
                        item['course_code'] = new_code


            print(f"Loaded {len(self.subjects)} unique subjects.")
            self.build_indices()
            
        except Exception as e:
            print(f"Error loading data: {e}")

    def build_indices(self):
        """Build reverse index for fast searching"""
        for code, subject in self.subjects.items():
            # Index by Code (High Priority)
            code_norm = normalize_text(code)
            self.keyword_index[code_norm].add(code)
            
            # Index by Name (Full) - Both accented and no-accents
            norm_name = normalize_text(subject.name)
            self.keyword_index[norm_name].add(code)
            
            no_accent_name = normalize_text(subject.name, remove_accents=True)
            if no_accent_name != norm_name:
                self.keyword_index[no_accent_name].add(code)
            
            # Index by Name EN (Full)
            if subject.name_en:
                self.keyword_index[normalize_text(subject.name_en)].add(code)
            
            # Index by words/phrases in Name
            def index_phrases(text_to_index):
                words = text_to_index.split()
                n_words = len(words)
                
                # Helper to check if a phrase is "valid" (not just digits/stopwords)
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
                            self.keyword_index[gram].add(code)

            index_phrases(norm_name)
            if no_accent_name != norm_name:
                index_phrases(no_accent_name)

    def detect_subjects(self, query: str) -> List[SubjectInfo]:
        """
        Detect subjects in the query using n-gram lookup.
        Supports both accented and no-accent matching.
        """
        query_norm = normalize_text(query)
        query_no_accent = normalize_text(query, remove_accents=True)
        
        detected_codes = set()
        
        # 1. Exact Code Match
        words = query_norm.split()
        for w in words:
            w_code = w.upper().rstrip('.')
            if w_code in self.subjects:
                detected_codes.add(w_code)
        
        # 2. Full Name Scanning (Accented & No Accent)
        sorted_subjects = sorted(self.subjects.values(), key=lambda s: len(s.name), reverse=True)
        for sub in sorted_subjects:
            sub_norm = normalize_text(sub.name)
            sub_no_accent = normalize_text(sub.name, remove_accents=True)
            
            if (sub_norm and sub_norm in query_norm) or (sub_no_accent and sub_no_accent in query_no_accent):
                detected_codes.add(sub.code)

        # 3. N-Gram Matching (Both versions)
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
                    if gram in self.keyword_index:
                        found.update(self.keyword_index[gram])
            return found

        detected_codes.update(find_grams(query_norm))
        detected_codes.update(find_grams(query_no_accent))

        results = [self.subjects[c] for c in detected_codes if c in self.subjects]
        return results

    def get_subject_by_code(self, code: str) -> Optional[SubjectInfo]:
        return self.subjects.get(code)
    
    def get_all_chunks_by_code(self, code: str) -> List[Dict]:
        """
        Return all text chunks belonging to a specific course code.
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
