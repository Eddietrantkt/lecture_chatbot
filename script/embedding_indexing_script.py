"""
Script để embedding và indexing với FAISS + BM25
Hybrid retrieval system kết hợp semantic search (FAISS) và lexical search (BM25)
"""

import json
import pickle
import numpy as np
from pathlib import Path
import os
import sys
from typing import List, Dict, Any, Tuple
import warnings
warnings.filterwarnings('ignore')

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    from backend.config import Config
except ImportError:
    class Config:
        EMBEDDING_MODEL_NAME = "microsoft/harrier-oss-v1-270m"
        EMBEDDING_QUERY_PROMPT_NAME = "web_search_query"
        EMBEDDING_MAX_SEQ_LENGTH = 1024


class HybridRetriever:
    """
    Hybrid retriever kết hợp FAISS (dense vectors) và BM25 (sparse vectors)
    """
    
    def __init__(
        self,
        embedding_model_name: str = None,
        query_prompt_name: str = None,
        max_seq_length: int = None
    ):
        """
        Khởi tạo Hybrid Retriever
        
        Args:
            embedding_model_name: Tên model embedding (hỗ trợ tiếng Việt)
        """
        self.embedding_model_name = embedding_model_name or Config.EMBEDDING_MODEL_NAME
        self.query_prompt_name = query_prompt_name or Config.EMBEDDING_QUERY_PROMPT_NAME
        self.max_seq_length = max_seq_length or Config.EMBEDDING_MAX_SEQ_LENGTH
        self.chunks = []
        self.embeddings = None
        self.faiss_index = None
        self.bm25 = None
        self.embedding_model = None
        
    def load_embedding_model(self):
        """Load model embedding"""
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {self.embedding_model_name}")
            model_kwargs = {}
            if self.embedding_model_name.startswith("microsoft/harrier-oss-v1"):
                model_kwargs["dtype"] = "auto"

            self.embedding_model = SentenceTransformer(
                self.embedding_model_name,
                device='cpu',
                model_kwargs=model_kwargs
            )
            self.embedding_model.max_seq_length = self.max_seq_length
            print(f"Model loaded successfully with max_seq_length={self.embedding_model.max_seq_length}")
        except ImportError:
            raise ImportError("Cần cài đặt: pip install sentence-transformers")
    
    def load_chunks(self, chunks_file: str):
        """
        Load chunks từ file JSON
        
        Args:
            chunks_file: Đường dẫn đến file chunks
        """
        print(f"Loading chunks from {chunks_file}")
        with open(chunks_file, 'r', encoding='utf-8') as f:
            self.chunks = json.load(f)
        print(f"Loaded {len(self.chunks)} chunks")
    
    def create_embeddings(self, batch_size: int = 32):
        """
        Tạo embeddings cho tất cả chunks
        
        Args:
            batch_size: Kích thước batch khi embedding
        """
        if self.embedding_model is None:
            self.load_embedding_model()
        
        print(f"Creating embeddings for {len(self.chunks)} chunks...")
        
        # Lấy embedding_text từ chunks (chỉ embed section_name + course_name)
        # Fallback về text nếu không có embedding_text
        texts = [chunk.get('embedding_text', chunk['text']) for chunk in self.chunks]
        print("Embedding based on field: embedding_text (section_name + course_name)")
        
        # Tạo embeddings theo batch
        self.embeddings = self.embedding_model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        print(f"Embeddings created with shape: {self.embeddings.shape}")
    
    def build_faiss_index(self, use_gpu: bool = False):
        """
        Xây dựng FAISS index từ embeddings
        
        Args:
            use_gpu: Có sử dụng GPU không (cần cài faiss-gpu)
        """
        try:
            import faiss
        except ImportError:
            raise ImportError("Cần cài đặt: pip install faiss-cpu (hoặc faiss-gpu)")
        
        print("Building FAISS index...")
        
        dimension = self.embeddings.shape[1]
        
        # Sử dụng IndexFlatIP cho cosine similarity
        # Normalize vectors trước
        faiss.normalize_L2(self.embeddings)
        
        if use_gpu:
            try:
                # Sử dụng GPU nếu có
                res = faiss.StandardGpuResources()
                index_flat = faiss.IndexFlatIP(dimension)
                self.faiss_index = faiss.index_cpu_to_gpu(res, 0, index_flat)
            except:
                print("⚠ Không thể sử dụng GPU, chuyển sang CPU")
                self.faiss_index = faiss.IndexFlatIP(dimension)
        else:
            self.faiss_index = faiss.IndexFlatIP(dimension)
        
        # Thêm vectors vào index
        self.faiss_index.add(self.embeddings)
        
        print(f"FAISS index built with {self.faiss_index.ntotal} vectors")
    
    def build_bm25_index(self):
        """
        Xây dựng BM25 index từ chunks
        """
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            raise ImportError("Cần cài đặt: pip install rank-bm25")
        
        print("Building BM25 index...")
        
        # Tokenize texts (đơn giản: split by space)
        # Có thể cải thiện bằng underthesea hoặc pyvi cho tiếng Việt
        tokenized_corpus = [chunk['text'].lower().split() for chunk in self.chunks]
        
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        print(f"BM25 index built with {len(tokenized_corpus)} documents")
    
    def save_index(self, output_dir: str):
        """
        Lưu index và embeddings
        
        Args:
            output_dir: Thư mục lưu index
        """
        import faiss
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Saving index to {output_dir}...")
        
        # Lưu FAISS index
        faiss_path = output_path / "faiss.index"
        faiss.write_index(faiss.index_gpu_to_cpu(self.faiss_index) if hasattr(self.faiss_index, 'getDevice') 
                         else self.faiss_index, str(faiss_path))
        
        # Lưu BM25
        bm25_path = output_path / "bm25.pkl"
        with open(bm25_path, 'wb') as f:
            pickle.dump(self.bm25, f)
        
        # Lưu chunks
        chunks_path = output_path / "chunks.json"
        with open(chunks_path, 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)
        
        # Lưu embeddings
        embeddings_path = output_path / "embeddings.npy"
        np.save(embeddings_path, self.embeddings)
        
        # Lưu metadata
        metadata = {
            "num_chunks": len(self.chunks),
            "embedding_dim": self.embeddings.shape[1],
            "embedding_model": self.embedding_model_name,
            "query_prompt_name": self.query_prompt_name,
            "max_seq_length": self.max_seq_length,
            "total_vectors": self.faiss_index.ntotal
        }
        metadata_path = output_path / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print("All indices saved")
        print(f"  - FAISS index: {faiss_path}")
        print(f"  - BM25 index: {bm25_path}")
        print(f"  - Chunks: {chunks_path}")
        print(f"  - Embeddings: {embeddings_path}")
        print(f"  - Metadata: {metadata_path}")
    
    def load_index(self, index_dir: str):
        """
        Load index đã lưu
        
        Args:
            index_dir: Thư mục chứa index
        """
        import faiss
        
        index_path = Path(index_dir)
        
        print(f"Loading index from {index_dir}...")
        
        # Load FAISS
        faiss_path = index_path / "faiss.index"
        self.faiss_index = faiss.read_index(str(faiss_path))
        
        # Load BM25
        bm25_path = index_path / "bm25.pkl"
        with open(bm25_path, 'rb') as f:
            self.bm25 = pickle.load(f)
        
        # Load chunks
        chunks_path = index_path / "chunks.json"
        with open(chunks_path, 'r', encoding='utf-8') as f:
            self.chunks = json.load(f)
        
        # Load embeddings
        embeddings_path = index_path / "embeddings.npy"
        self.embeddings = np.load(embeddings_path)

        metadata_path = index_path / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            self.embedding_model_name = metadata.get("embedding_model", self.embedding_model_name)
            self.query_prompt_name = metadata.get("query_prompt_name", self.query_prompt_name)
            self.max_seq_length = metadata.get("max_seq_length", self.max_seq_length)
        
        # Load model
        self.load_embedding_model()
        
        print("Index loaded successfully")
    
    def search_faiss(self, query: str, top_k: int = 10) -> Tuple[List[int], List[float]]:
        """
        Search sử dụng FAISS (semantic search)
        
        Args:
            query: Query string
            top_k: Số kết quả trả về
            
        Returns:
            Tuple (indices, scores)
        """
        if self.embedding_model is None:
            self.load_embedding_model()
        
        # Encode query
        encode_kwargs = {"convert_to_numpy": True}
        if self.query_prompt_name:
            encode_kwargs["prompt_name"] = self.query_prompt_name
        query_vector = self.embedding_model.encode([query], **encode_kwargs)
        
        # Normalize
        import faiss
        faiss.normalize_L2(query_vector)
        
        # Search
        scores, indices = self.faiss_index.search(query_vector, top_k)
        
        return indices[0].tolist(), scores[0].tolist()
    
    def search_bm25(self, query: str, top_k: int = 10) -> Tuple[List[int], List[float]]:
        """
        Search sử dụng BM25 (lexical search)
        
        Args:
            query: Query string
            top_k: Số kết quả trả về
            
        Returns:
            Tuple (indices, scores)
        """
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        top_scores = scores[top_indices]
        
        return top_indices.tolist(), top_scores.tolist()
    
    def hybrid_search(self, query: str, top_k: int = 10, 
                     alpha: float = 0.5) -> List[Dict[str, Any]]:
        """
        Hybrid search kết hợp FAISS và BM25
        
        Args:
            query: Query string
            top_k: Số kết quả trả về
            alpha: Trọng số cho FAISS (1-alpha cho BM25)
            
        Returns:
            List kết quả với scores
        """
        # Search với cả 2 phương pháp
        faiss_indices, faiss_scores = self.search_faiss(query, top_k * 2)
        bm25_indices, bm25_scores = self.search_bm25(query, top_k * 2)
        
        # Normalize scores về [0, 1]
        faiss_scores = np.array(faiss_scores)
        bm25_scores = np.array(bm25_scores)
        
        if faiss_scores.max() > 0:
            faiss_scores = faiss_scores / faiss_scores.max()
        if bm25_scores.max() > 0:
            bm25_scores = bm25_scores / bm25_scores.max()
        
        # Kết hợp scores
        combined_scores = {}
        
        for idx, score in zip(faiss_indices, faiss_scores):
            combined_scores[idx] = combined_scores.get(idx, 0) + alpha * score
        
        for idx, score in zip(bm25_indices, bm25_scores):
            combined_scores[idx] = combined_scores.get(idx, 0) + (1 - alpha) * score
        
        # Sắp xếp theo score
        sorted_results = sorted(combined_scores.items(), 
                              key=lambda x: x[1], reverse=True)[:top_k]
        
        # Tạo kết quả
        results = []
        for idx, score in sorted_results:
            result = {
                "chunk": self.chunks[idx],
                "score": float(score),
                "index": idx
            }
            results.append(result)
        
        return results


def main():
    """
    Hàm main để build index
    """
    # Cấu hình
    # Cấu hình
    # BASE_DIR: Lấy thư mục hiện tại chứa script này
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    INDEX_DIR = os.path.join(PROJECT_ROOT, "index")
    CHUNKS_FILE = os.path.join(INDEX_DIR, "chunks.json")
    
    print("=" * 60)
    print("BUILDING HYBRID INDEX (FAISS + BM25)")
    print("=" * 60)
    
    # Khởi tạo retriever
    retriever = HybridRetriever()
    
    # Load chunks
    retriever.load_chunks(CHUNKS_FILE)
    
    # Tạo embeddings
    retriever.create_embeddings(batch_size=32)
    
    # Build FAISS index
    retriever.build_faiss_index(use_gpu=False)
    
    # Build BM25 index
    retriever.build_bm25_index()
    
    # Save index
    retriever.save_index(INDEX_DIR)
    
    print("\n" + "=" * 60)
    print("TESTING SEARCH")
    print("=" * 60)
    
    # Test search
    test_queries = [
        "đại số tuyến tính",
        "giải tích",
        "học phần tiên quyết",
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = retriever.hybrid_search(query, top_k=3, alpha=0.5)
        
        for i, result in enumerate(results, 1):
            chunk = result['chunk']
            score = result['score']
            print(f"\n  [{i}] Score: {score:.4f}")
            print(f"      Học phần: {chunk.get('course_name', 'N/A')}")
            print(f"      Section: {chunk.get('section_name', 'N/A')}")
            print(f"      Preview: {chunk['text'][:100]}...")
    
    print("\n" + "=" * 60)
    print("✓ COMPLETED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
