import sys
import os
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.config import Config
from backend.course_loader import CourseLoader

def test_collision_handling():
    print("Testing Course Collision Handling...", flush=True)
    
    loader = CourseLoader(Config.INDEX_DIR)
    
    # Test Case 1: Collision -> "Toán rời rạc 2A"
    print("\n--- Test Case 1: 'Toán rời rạc 2A' (MTHxxxxx) ---", flush=True)
    res1 = loader.load_full_course_json(course_code="MTHxxxxx", course_name="Toán rời rạc 2A")
    if res1:
        name1 = res1['_metadata']['course_name']
        print(f"✅ Loaded: {name1}", flush=True)
        if "Toán rời rạc" in name1:
             print("SUCCESS: Correctly prioritized Name over Collision Code.", flush=True)
        else:
             print(f"FAILURE: Loaded {name1} instead of Discrete Math.", flush=True)
    else:
        print("FAILURE: Course not found.", flush=True)

    # Test Case 2: Collision -> "Cơ học tính toán"
    print("\n--- Test Case 2: 'Cơ học tính toán' (MTHxxxxx) ---", flush=True)
    res2 = loader.load_full_course_json(course_code="MTHxxxxx", course_name="Cơ học tính toán")
    if res2:
        name2 = res2['_metadata']['course_name']
        print(f"✅ Loaded: {name2}", flush=True)
        if "Cơ học tính toán" in name2:
             print("SUCCESS: Correctly loaded Computational Mechanics.", flush=True)
        else:
             print(f"FAILURE: Loaded {name2}", flush=True)
    
    # Test Case 3: Code Only (Ambiguity)
    print("\n--- Test Case 3: Code Only (MTHxxxxx) ---", flush=True)
    res3 = loader.load_full_course_json(course_code="MTHxxxxx", course_name=None)
    if res3:
        name3 = res3['_metadata']['course_name']
        print(f"ℹ️ Loaded default for MTHxxxxx: {name3}", flush=True)

if __name__ == "__main__":
    test_collision_handling()
