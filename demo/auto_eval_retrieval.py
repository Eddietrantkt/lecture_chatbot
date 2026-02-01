import json
import random
import os
import sys
import time
import logging
from tqdm import tqdm
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AutoEval")

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.llm_interface import LLMInterface
from backend.adaptive_retriever import AdaptiveRetriever

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS_FILE = os.path.join(BASE_DIR, "chunked_data.json")
INDEX_DIR = os.path.join(BASE_DIR, "index")
TEST_SET_FILE = os.path.join(BASE_DIR, "demo", "synthetic_test_set.json")
NUM_SAMPLES = 100  # Number of questions to generate

def generate_test_set():
    """
    Generates synthetic QA pairs from random chunks using LLM.
    Handles Rate Limit (429) with retry logic.
    """
    logger.info(f"Loading chunks from {CHUNKS_FILE}...")
    try:
        with open(CHUNKS_FILE, 'r', encoding='utf-8') as f:
            all_chunks = json.load(f)
    except FileNotFoundError:
        logger.error("Chunk file not found!")
        return

    # Filter out chunks that are too short
    valid_chunks = [c for c in all_chunks if len(c.get('text', '')) > 50]
    
    if len(valid_chunks) < NUM_SAMPLES:
        selected_chunks = valid_chunks
    else:
        selected_chunks = random.sample(valid_chunks, NUM_SAMPLES)

    logger.info(f"Generating {len(selected_chunks)} synthetic questions using LLM...")
    
    llm = LLMInterface()
    if not llm.enabled:
        logger.error("LLM is not enabled.")
        return

    # Load existing dataset if exists (Checkpointing)
    dataset = []
    if os.path.exists(TEST_SET_FILE):
        try:
            with open(TEST_SET_FILE, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            logger.info(f"Resuming from existing checkpoint: {len(dataset)} items done.")
        except:
            pass
    
    # Calculate how many left to do
    remaining_count = len(selected_chunks) - len(dataset)
    if remaining_count <= 0:
        logger.info("Dataset already complete!")
        return
        
    # Only process the remaining chunks
    chunks_to_process = selected_chunks[len(dataset):]
    
    for i, chunk in enumerate(tqdm(chunks_to_process, desc="Generating Queries")):
        context = chunk.get('text', '')
        course_name = chunk.get('course_name', 'Môn học')
        
        prompt = f"""
Bạn là một sinh viên đại học đang tìm hiểu về môn học "{course_name}".
Dựa vào đoạn văn bản dưới đây, hãy đặt 1 câu hỏi ngắn gọn, tự nhiên mà sinh viên thường hỏi để tìm kiếm thông tin này.
Câu hỏi phải liên quan trực tiếp đến nội dung văn bản.
Không trả lời câu hỏi, chỉ đưa ra câu hỏi. Không thêm dấu ngoặc kép.

Văn bản:
{context[:1000]}

Câu hỏi:
"""
        max_retries = 5
        retry_delay = 60 # seconds
        success = False
        
        for attempt in range(max_retries):
            try:
                # Rate limit manual delay
                time.sleep(5) 
                
                response = llm.client.chat.completions.create(
                    model=llm.model,
                    messages=[{"role": "user", "content": prompt}]
                )
                question = response.choices[0].message.content.strip().replace('"', '')
                
                new_item = {
                    "id": len(dataset),
                    "question": question,
                    "ground_truth_text": context,
                    "course_code": chunk.get('course_code'),
                    "section": chunk.get('section_name')
                }
                dataset.append(new_item)
                
                # Save Checkpoint immediately
                with open(TEST_SET_FILE, 'w', encoding='utf-8') as f:
                    json.dump(dataset, f, ensure_ascii=False, indent=2)
                
                success = True
                break
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    logger.warning(f"Rate Limit Hit (429). Waiting {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Error generating question: {e}")
                    break # Break on non-retryable error
        
        if not success:
            logger.error(f"Failed to generate question for chunk index {i} after retries.")
    
    logger.info(f"Completed! Total QA pairs: {len(dataset)}")

def evaluate_retrieval():
    """
    Runs retrieval on the test set and calculates accuracy.
    """
    if not os.path.exists(TEST_SET_FILE):
        logger.error("Test set not found. Please run generation first.")
        return

    logger.info("Loading test set...")
    with open(TEST_SET_FILE, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    logger.info("Initializing Retriever...")
    retriever = AdaptiveRetriever(INDEX_DIR, CHUNKS_FILE)

    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    
    # New metrics: Subject Match Accuracy
    subject_hits_at_1 = 0
    subject_hits_at_3 = 0
    subject_hits_at_5 = 0
    
    total = len(dataset)
    
    logger.info(f"Evaluating {total} queries...")

    for item in tqdm(dataset, desc="Evaluating"):
        query = item['question']
        ground_truth_text = item['ground_truth_text']
        ground_truth_code = item.get('course_code') # Get ground truth code
        
        # Run retrieval
        results = retriever.retriever.hybrid_search(query, top_k=5)
        
        # Check Content Matches (Exact chunk retrieval)
        found_rank = -1
        for rank, res in enumerate(results):
            if res['chunk']['text'] == ground_truth_text:
                found_rank = rank
                break
        
        if found_rank == 0:
            hits_at_1 += 1
        if found_rank != -1 and found_rank < 3:
            hits_at_3 += 1
        if found_rank != -1 and found_rank < 5:
            hits_at_5 += 1

        # Check Subject Matches (Correct Course Code)
        # We check if the CORRECT course code appears in the top K results
        found_subject_rank = -1
        if ground_truth_code:
            for rank, res in enumerate(results):
                retrieved_code = res['chunk'].get('course_code')
                if retrieved_code == ground_truth_code:
                    found_subject_rank = rank
                    break # Found the first occurrence of the correct subject
            
            if found_subject_rank == 0:
                subject_hits_at_1 += 1
            if found_subject_rank != -1 and found_subject_rank < 3:
                subject_hits_at_3 += 1
            if found_subject_rank != -1 and found_subject_rank < 5:
                subject_hits_at_5 += 1

    print("\n" + "="*50)
    print("📊 RETRIEVAL EVALUATION REPORT")
    print("="*50)
    print(f"Total Questions: {total}")
    print("-" * 30)
    print("1. EXACT CHUNK MATCH (Tìm lại đúng đoạn văn gốc)")
    print(f"  • Top 1 Accuracy: {hits_at_1}/{total} ({hits_at_1/total*100:.2f}%)")
    print(f"  • Top 3 Accuracy: {hits_at_3}/{total} ({hits_at_3/total*100:.2f}%)")
    print(f"  • Top 5 Accuracy: {hits_at_5}/{total} ({hits_at_5/total*100:.2f}%)")
    print("-" * 30)
    print("2. SUBJECT MATCH (Tìm ra đúng môn học)")
    print(f"  • Top 1 Accuracy: {subject_hits_at_1}/{total} ({subject_hits_at_1/total*100:.2f}%)")
    print(f"  • Top 3 Accuracy: {subject_hits_at_3}/{total} ({subject_hits_at_3/total*100:.2f}%)")
    print(f"  • Top 5 Accuracy: {subject_hits_at_5}/{total} ({subject_hits_at_5/total*100:.2f}%)")
    print("="*50 + "\n")

def main():
    print("1. Generate new test set (using LLM)")
    print("2. Evaluate existing test set")
    print("3. Run both")
    
    choice = input("Select option (1/2/3): ").strip()
    
    if choice in ['1', '3']:
        generate_test_set()
    
    if choice in ['2', '3']:
        evaluate_retrieval()

if __name__ == "__main__":
    main()
