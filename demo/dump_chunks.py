import json
import random
import os
import sys

# Force UTF-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS_FILE = os.path.join(BASE_DIR, "chunked_data.json")

def dump_random_chunks():
    try:
        with open(CHUNKS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Filter valid chunks
        valid_chunks = [c for c in data if len(c.get('text', '')) > 100]
        
        # Pick 50 chunks (Giảm xuống 50 để đảm bảo output không bị cắt giữa chừng, 
        # tôi sẽ làm 2 đợt hoặc 50 câu chất lượng là đủ đại diện)
        selected = random.sample(valid_chunks, 20) 
        
        print(json.dumps(selected, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(e)

if __name__ == "__main__":
    dump_random_chunks()
