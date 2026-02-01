
import logging
from typing import Dict, List, Optional
from backend.llm_interface import LLMInterface

logger = logging.getLogger("IntentRouter")

class IntentRouter:
    """
    Classifies user query intent relative to the current conversation context.
    Intents:
    - NEW_TOPIC: User is asking about a different subject or starting a new search.
    - FOLLOW_UP: User is asking for more details about the CURRENT subject.
    - CHITCHAT: Greetings, thanks, or irrelevant simple chatter.
    """
    
    def __init__(self, llm: LLMInterface):
        self.llm = llm

    def classify(self, query: str, current_subject_code: Optional[str] = None, current_subject_name: Optional[str] = None) -> str:
        """
        Determine intent of the query given the current subject context.
        """
        # If no context, it's likely NEW_TOPIC or CHITCHAT. 
        # But we still check to be safe (unless it's pure chitchat).
        
        context_str = "None"
        if current_subject_name:
            context_str = f"{current_subject_name} (Code: {current_subject_code})"

        prompt = f"""You are an Intent Classifier for a Course Q&A System.

Current Conversation Context: **{context_str}**
User Query: "{query}"

Task: Classify into one of 3 categories:
1. **NEW_TOPIC**: User asks about a specific DIFFERENT subject, or a general question unrelated to the current one.
   - E.g. Context="Math", Query="Who teaches Art?" -> NEW_TOPIC
   - E.g. Context="Math", Query="Tell me about Calculus" -> NEW_TOPIC
   - E.g. Context="None", Query="Info about Math" -> NEW_TOPIC

2. **FOLLOW_UP**: User asks for more details about the CURRENT subject (Context).
   - E.g. Context="Math", Query="How many credits?" (Implies Math) -> FOLLOW_UP
   - E.g. Context="Math", Query="Who is the lecturer?" -> FOLLOW_UP
   - E.g. Context="Math", Query="Is it hard?" -> FOLLOW_UP
   *IF Context is None, this cannot be FOLLOW_UP.*

3. **CHITCHAT**: Social interaction, greetings, thanks, or nonsense.
   - E.g. "Hello", "Thanks", "Good bot" -> CHITCHAT

Output JSON ONLY:
{{
  "intent": "NEW_TOPIC" | "FOLLOW_UP" | "CHITCHAT",
  "reasoning": "Brief explanation"
}}
"""
        response = self.llm._call_with_retry([{"role": "user", "content": prompt}], temperature=0.0)
        
        default_intent = "NEW_TOPIC"
        
        if response:
            try:
                # Clean response
                clean_resp = response
                if "</think>" in clean_resp:
                     clean_resp = clean_resp.split("</think>", 1)[1].strip()
                
                if "```json" in clean_resp:
                    clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_resp:
                    clean_resp = clean_resp.split("```")[1].split("```")[0].strip()
                
                # Try to extract JSON
                import json
                if "{" in clean_resp:
                    start = clean_resp.find("{")
                    end = clean_resp.rfind("}") + 1
                    clean_resp = clean_resp[start:end]
                    
                data = json.loads(clean_resp)
                intent = data.get("intent", default_intent).upper()
                
                # Safety check: Cannot be FOLLOW_UP if no context
                if intent == "FOLLOW_UP" and not current_subject_name:
                    logger.warning("Classified as FOLLOW_UP but no context exists. Forcing NEW_TOPIC.")
                    return "NEW_TOPIC"
                    
                return intent
                
            except Exception as e:
                logger.error(f"Error parsing intent: {e}")
                return default_intent
        
        return default_intent
