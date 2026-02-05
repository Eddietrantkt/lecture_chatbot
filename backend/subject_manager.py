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
        Returns entries sorted by relevance to the query.
        """
        query_norm = normalize_text(query)
        query_no_accent = normalize_text(query, remove_accents=True)
        query_tokens = set(query_norm.split())
        query_tokens_no_accent = set(query_no_accent.split())
        
        detected_codes = set()
        
        # 1. Exact Code Match
        words = query_norm.split()
        for w in words:
            w_code = w.upper().rstrip('.')
            if w_code in self.subjects:
                detected_codes.add(w_code)
        
        # 2. Full Name Scanning (Accented & No Accent)
        # We can iterate all, but for efficiency we might rely on N-gram to find candidates first.
        # However, to be safe, let's keep the scan but we will score them later.
        # Actually, let's allow the N-gram index to do the heavy lifting for retrieval, 
        # BUT we must always check "Is this name actually in the query?" for high confidence.
        
        # Optimization: Let's trust N-gram + Code match to find candidates, then score them.
        # If N-gram misses "Full Name", it's because the name is unique and not in N-gram? 
        # No, N-gram indexes all valid grams.
        
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

        # Retrieve SubjectInfo objects
        candidates = [self.subjects[c] for c in detected_codes if c in self.subjects]
        
        # 4. Score and Sort
        def calculate_score(subj: SubjectInfo):
            score = 0
            s_name_norm = normalize_text(subj.name)
            s_name_no_accent = normalize_text(subj.name, remove_accents=True)
            
            # Criterion 1: Substring match (High Value)
            if s_name_norm in query_norm:
                score += 50
                # Extra points for length of name (longer specific name is better)
                score += len(s_name_norm)
            elif s_name_no_accent in query_no_accent:
                score += 40
                score += len(s_name_no_accent)
            
            # Criterion 2: Token Overlap (Medium Value)
            s_tokens = set(s_name_norm.split())
            overlap = len(s_tokens & query_tokens)
            score += overlap * 5
            
            return score

        # Sort by score desc
        sorted_candidates = sorted(candidates, key=calculate_score, reverse=True)
        
        return sorted_candidates

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
