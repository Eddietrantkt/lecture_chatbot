import time
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

# Add parent directory to path to import backend modules if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env from parent dir
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

def test_llm_speed():
    api_key = os.environ.get("OPENROUTER_API_KEY") or "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"
    model = "z-ai/glm-4.5-air:free"
    
    print(f"--- TESTING LLM SPEED ---")
    print(f"Model: {model}")
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    
    query = "Giải thích ngắn gọn về thuyết tương đối hẹp trong 3 câu."
    print(f"\nQuery: '{query}'")
    print("-" * 40)
    
    start_time = time.time()
    first_token_time = None
    full_content = ""
    
    try:
        # Use streaming to measure TTFT (Time To First Token)
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": query}],
            stream=True
        )
        
        print("Response: ", end="", flush=True)
        
        for chunk in stream:
            if first_token_time is None:
                first_token_time = time.time()
            
            content = chunk.choices[0].delta.content or ""
            full_content += content
            print(content, end="", flush=True)
            
        end_time = time.time()
        
        print("\n" + "-" * 40)
        
        total_time = end_time - start_time
        ttft = (first_token_time - start_time) if first_token_time else 0
        char_count = len(full_content)
        # Rough estimation: 1 token ~ 4 chars (English) or 1.5 chars (Vietnamese)
        # Let's use a safe estimate for speed calculation
        
        print(f"\n📊 STATISTICS:")
        print(f"  • Time to First Token (Latency): {ttft:.4f}s")
        print(f"  • Total Generation Time:         {total_time:.4f}s")
        print(f"  • Total Content Length:          {char_count} chars")
        print(f"  • Average Speed (approx):        {char_count / total_time:.1f} chars/sec")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_llm_speed()
