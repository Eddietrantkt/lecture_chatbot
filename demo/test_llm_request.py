"""
Test script kiểm tra kết nối LLM server.
Đọc config từ backend/config.py - chỉ cần sửa config 1 chỗ duy nhất.

Chạy: python demo/test_llm_request.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from backend.config import Config


def get_base_url():
    """Lấy base URL từ config (bỏ /v1 ở cuối nếu có)"""
    url = Config.LLM_BASE_URL
    if url.endswith("/v1"):
        return url[:-3]
    return url


def test_models_endpoint():
    """Test 1: Kiểm tra server có respond không (/v1/models)"""
    base_url = get_base_url()
    
    print("=" * 60)
    print("🔍 Kiểm tra kết nối LLM Server")
    print("=" * 60)
    print(f"Config File: backend/config.py")
    print(f"Base URL: {base_url}")
    print(f"Model: {Config.LLM_MODEL}")
    print(f"API Key: {'Có (đã ẩn)' if Config.LLM_API_KEY else 'Không'}")
    print("-" * 60)
    
    headers = {}
    if Config.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {Config.LLM_API_KEY}"
    
    try:
        print("⏳ Đang gọi /v1/models ...")
        resp = requests.get(f"{base_url}/v1/models", headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            models = data.get('data', [])
            print(f"✅ Server OK! Status: {resp.status_code}")
            print(f"✅ Tìm thấy {len(models)} model:")
            for m in models:
                print(f"   - {m.get('id', 'unknown')}")
            return True
            
        elif resp.status_code == 401:
            print(f"❌ Lỗi 401: Sai API Key!")
            print(f"   Kiểm tra lại LLM_API_KEY trong backend/config.py")
            return False
            
        elif resp.status_code == 404:
            print(f"❌ Lỗi 404: Endpoint không tồn tại")
            print(f"   Có thể server chưa start hoặc URL sai")
            return False
            
        else:
            print(f"❌ Lỗi HTTP {resp.status_code}")
            print(f"Chi tiết: {resp.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Không kết nối được đến {base_url}")
        print(f"   - Kiểm tra xem server LLM còn chạy không")
        print(f"   - Kiểm tra xem tunnel (ngrok/cloudflared) còn chạy không")
        return False
        
    except requests.exceptions.Timeout:
        print(f"❌ Timeout: Server không phản hồi sau 15 giây")
        return False
        
    except Exception as e:
        print(f"❌ Lỗi không xác định: {e}")
        return False


def test_chat_completion():
    """Test 2: Thử gửi 1 đoạn chat đơn giản"""
    base_url = get_base_url()
    
    print("\n" + "-" * 60)
    print("💬 Test chat completion...")
    print("-" * 60)
    
    headers = {
        "Content-Type": "application/json"
    }
    if Config.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {Config.LLM_API_KEY}"
    
    payload = {
        "model": Config.LLM_MODEL,
        "messages": [
            {"role": "user", "content": "Xin chào! Hãy trả lời 'OK' nếu bạn nhận được tin nhắn này."}
        ],
        "max_tokens": 50,
        "temperature": 0.1
    }
    
    try:
        print("⏳ Đang gửi request...")
        resp = requests.post(
            f"{base_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=Config.LLM_TIMEOUT
        )
        
        if resp.status_code == 200:
            result = resp.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ Chat API hoạt động!")
            print(f"📝 Phản hồi: {content[:100]}...")
            return True
        else:
            print(f"❌ Chat API lỗi: {resp.status_code}")
            print(f"Chi tiết: {resp.text[:300]}")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi khi chat: {e}")
        return False


if __name__ == "__main__":
    if test_models_endpoint():
        if test_chat_completion():
            print("\n" + "=" * 60)
            print("🎉 THÀNH CÔNG!")
            print("LLM Server hoạt động bình thường.")
            print(f"Config: backend/config.py")
            print("=" * 60)
        else:
            print("\n⚠️ Server online nhưng chat bị lỗi")
            sys.exit(1)
    else:
        print("\n" + "=" * 60)
        print("💥 KẾT NỐI THẤT BẠI")
        print("Kiểm tra lại:")
        print("1. Server LLM còn chạy không?")
        print("2. Tunnel (ngrok/cloudflared) còn chạy không?")
        print("3. LLM_BASE_URL trong backend/config.py có đúng không?")
        print("=" * 60)
        sys.exit(1)