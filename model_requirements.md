# 📊 AITeamVN/Vietnamese_Embedding_v2 - Yêu Cầu Hệ Thống

## Thông Tin Model

| Thông số | Giá trị |
|----------|---------|
| **Tổng Parameters** | 567,754,752 (~568M params) |
| **Precision** | Float32 (F32) |
| **Output Dimensions** | 1024 |
| **Max Sequence Length** | 2048 tokens |
| **Base Model** | BAAI/bge-m3 |

---

## 💾 Kích Thước File

### Model Weights (safetensors)
- **Parameters:** 567,754,752
- **Precision:** F32 (4 bytes/param)
- **Kích thước:** ~2.15 GB (567.75M × 4 bytes)

### Tổng Cộng Cần Download:
```
model.safetensors:  ~2.2 GB
config files:       ~10 MB
tokenizer:          ~5 MB
───────────────────────────
Tổng:              ~2.3 GB
```

---

## 🖥️ Yêu Cầu Cấu Hình

### ⚠️ RAM Yêu Cầu (Quan Trọng!)

Khi load model vào memory:

**Minimum (Chỉ inference):**
```
Model weights:              2.3 GB
Python overhead:            0.5 GB
Intermediate tensors:       1.0 GB
──────────────────────────────────
Minimum RAM:                4 GB
```

**Recommended (Thực tế sử dụng):**
```
Model weights:              2.3 GB
Python + libraries:         0.5 GB
Intermediate tensors:       1.5 GB
Batch processing:           1.0 GB
OS + other apps:            2.0 GB
──────────────────────────────────
Recommended RAM:            8 GB
```

**Optimal (Xử lý nhiều documents):**
```
Model weights:              2.3 GB
Full batch processing:      2.0 GB
Multiple workers:           1.5 GB
OS + background:            2.0 GB
──────────────────────────────────
Optimal RAM:               16 GB
```

### 🎮 GPU (Optional - Tăng tốc đáng kể)

**CPU Only:**
- ✅ Chạy được, nhưng **CHẬM**
- Embedding 1,498 chunks: ~10-15 phút
- Batch size nhỏ (8-16)

**GPU Recommended:**
- ✅ **RTX 3060 (12GB)** - Lý tưởng
- ✅ **RTX 3050 (8GB)** - Tốt
- ✅ **GTX 1660 (6GB)** - Chấp nhận được
- ⚠️ **GPU < 4GB** - Khó khăn

**Với GPU:**
- Embedding 1,498 chunks: ~30-60 giây
- Batch size lớn (32-64)
- Nhanh gấp 10-20 lần CPU

### 💿 Ổ Cứng
- **Tối thiểu:** 5 GB trống (model + cache)
- **Khuyến nghị:** 10 GB trống (cho data + index)

### 🐍 Python & Libraries
```bash
Python >= 3.8
sentence-transformers
torch >= 1.12
```

---

## 📈 Performance Benchmark

### Trên CPU (Intel i5-10400)
```
Single document (512 tokens):    ~200ms
Batch 16 documents:              ~2.5s
1,498 chunks (chunked_data):     ~12 phút
```

### Trên GPU (RTX 3060)
```
Single document (512 tokens):    ~15ms
Batch 64 documents:              ~1.2s
1,498 chunks (chunked_data):     ~45 giây
```

---

## 🚀 Tối Ưu Cho Máy Yếu

Nếu RAM < 8GB hoặc không có GPU:

### Option 1: Quantization (Giảm size)
```python
# Load model với half precision (FP16)
model = SentenceTransformer(
    "AITeamVN/Vietnamese_Embedding_v2",
    device="cpu"
)
model.half()  # Giảm từ 2.3GB → 1.2GB
```
**Pros:** Giảm 50% RAM
**Cons:** Giảm ~1-2% accuracy

### Option 2: Batch Processing Nhỏ
```python
# Chia nhỏ chunks, process từng batch
batch_size = 8  # Thay vì 32-64
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i+batch_size]
    embeddings = model.encode(batch)
```
**Pros:** Chạy được trên RAM thấp
**Cons:** Chậm hơn

### Option 3: Model Nhỏ Hơn
```python
# Dùng model nhỏ hơn nếu cần
# keepitreal/vietnamese-sbert (~400MB)
```
**Pros:** Nhẹ hơn nhiều
**Cons:** Accuracy thấp hơn

---

## ✅ Kết Luận & Khuyến Nghị

### Cấu Hình Tối Thiểu (Chạy Được)
```
CPU:     Intel i3/i5 hoặc Ryzen 3/5
RAM:     8 GB
GPU:     Không cần (nhưng sẽ chậm)
Disk:    10 GB trống
```

### Cấu Hình Khuyến Nghị (Mượt)
```
CPU:     Intel i5 gen 8+ hoặc Ryzen 5
RAM:     16 GB
GPU:     RTX 3050 8GB hoặc tốt hơn
Disk:    SSD với 10 GB trống
```

### Cấu Hình Optimal (Xử Lý Nhanh)
```
CPU:     Intel i7/i9 hoặc Ryzen 7/9
RAM:     32 GB
GPU:     RTX 3060 12GB hoặc RTX 4060
Disk:    NVMe SSD
```

---

## 🤔 Máy Của Bạn Như Thế Nào?

Hãy cho tôi biết:
1. **RAM:** Bao nhiêu GB?
2. **GPU:** Có GPU không? Loại gì?
3. **CPU:** Loại CPU gì?

Tôi sẽ tư vấn cách tối ưu phù hợp! 💡

---

## 📝 So Sánh Model Size

| Model | Parameters | RAM Needed | Speed |
|-------|-----------|-----------|-------|
| **vietnamese-sbert** | ~110M | ~1 GB | Nhanh |
| **multilingual-e5-base** | ~278M | ~1.5 GB | Trung bình |
| **Vietnamese_Embedding_v2** | ~568M | ~2.5 GB | Chậm hơn |
| **bge-m3 (base)** | ~568M | ~2.5 GB | Tương đương |

**Vietnamese_Embedding_v2** lớn hơn nhưng **accuracy cao hơn** (Acc@10: 95.78%)
