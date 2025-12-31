import json
import logging
import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

# Imports for modularity
from src.utils.config_loader import load_category_config
from src.common.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

# --- 1. Output Schema ---
class ExtractedMetadata(BaseModel):
    category_id: str = Field(..., description="The ID of the matching category.")
    confidence_score: float = Field(..., description="Confidence score between 0.0 and 1.0.")
    issue_date: Optional[str] = Field(None, description="ISO 8601 format (YYYY-MM-DD).")
    expiry_date: Optional[str] = Field(None, description="ISO 8601 format (YYYY-MM-DD).")
    country: Optional[str] = Field(None, description="Country associated with the document.")
    person_name: Optional[str] = Field(None, description="Primary person named.")
    summary: str = Field(..., description="Brief 1-sentence summary.")

# --- 2. The Classification Agent ---
class DocumentClassifier:
    def __init__(self):
        """
        Initializes the agent using settings.yaml. No hardcoded models allowed.
        """
        # 1. Get Client and Model from Factory
        self.client, self.model_name = LLMFactory.get_client()
        
        # 2. Get Agent-specific settings
        self.settings = LLMFactory.get_classifier_settings()
        self.max_tokens = self.settings.get("max_input_tokens", 3000)
        
        # 3. Load Categories
        self.category_prompt_str, self.valid_ids = load_category_config()

    def classify(self, text: str) -> Dict[str, Any]:
        
        # We explicitly give it an example JSON so it knows exactly what to do.
        system_prompt = f"""
        You are an intelligent document archivist.
        TODAY'S DATE: {datetime.date.today()} 

        --- ALLOWED CATEGORIES ---
        {self.category_prompt_str}
        
        --- INSTRUCTIONS ---
        1. Analyze the document text provided by the user.
        2. Select the BEST matching Category ID from the list above.
        3. Extract dates strictly in YYYY-MM-DD format.
        4. Return ONLY the JSON object.

        --- EXAMPLE OUTPUT FORMAT ---
        {{
            "category_id": "visa_document",
            "confidence_score": 0.95,
            "issue_date": "2023-01-15",
            "expiry_date": "2033-01-12",
            "country": "USA",
            "person_name": "John Doe",
            "summary": "A US B1/B2 Visa issued to John Doe valid until 2033."
        }}
        """

        truncated_text = text[:self.max_tokens]

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here is the document text:\n\n{truncated_text}"}
                ],
                response_format={"type": "json_object"}, 
                temperature=0
            )

            result_json = response.choices[0].message.content
            
            # Debugging: Uncomment the line below if you want to see exactly what Llama returns
            # print(f"DEBUG RAW RESPONSE: {result_json}")

            data = json.loads(result_json)
            
            # Validation Logic
            if data.get("category_id") not in self.valid_ids:
                # Fallback: Try to "fuzzy match" or just warn
                logger.warning(f"Invalid ID '{data.get('category_id')}'. Defaulting to uncategorized.")
                data["category_id"] = "uncategorized"

            return data

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return {
                "category_id": "uncategorized",
                "confidence_score": 0.0,
                "summary": "Error during classification.",
                "error": str(e)
            }