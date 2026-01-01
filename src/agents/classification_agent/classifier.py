import os
import json
import datetime
import logging
from typing import Dict, Any, List
from openai import OpenAI
from src.config.loader import SETTINGS

logger = logging.getLogger(__name__)

class DocumentClassifier:
    def __init__(self):
        self.config = SETTINGS.get('classifier', {})
        self.llm_config = SETTINGS.get('llm', {})
        self.max_tokens = self.config.get('max_input_tokens', 3000)
        
        # Load Category Definitions
        self.categories = self._load_categories()
        self.valid_ids = [c['id'] for c in self.categories]
        self.category_prompt_str = json.dumps(self.categories, indent=2)
        
        # Initialize LLM Client
        self._init_client()

    def _load_categories(self) -> List[Dict]:
        """
        Loads allowed categories. 
        In a real app, these might come from a DB or YAML.
        """
        return [
            {"id": "invoice", "description": "Bill for goods or services"},
            {"id": "receipt", "description": "Proof of payment"},
            {"id": "bank_statement", "description": "Periodic bank account summary"},
            {"id": "tax_return", "description": "Government tax filing (1040, W2, etc.)"},
            {"id": "contract", "description": "Legal agreement between parties"},
            {"id": "id_card", "description": "Passport, Driver License, National ID"},
            {"id": "medical_record", "description": "Doctor notes, prescriptions, lab results"},
            {"id": "visa_document", "description": "Immigration documents, H1B, Visas"},
            {"id": "resume", "description": "CV or Resume"},
            {"id": "educational_certificate", "description": "Degree, Transcript, or Diploma"},
            {"id": "utility_bill", "description": "Electricity, Water, Internet bill"},
            {"id": "insurance_policy", "description": "Health, Car, or Home insurance policy"}
        ]

    def _init_client(self):
        """Sets up the OpenAI-compatible client (Ollama/OpenAI)"""
        provider = self.llm_config.get('provider', 'local_ollama')
        
        if provider == 'local_ollama':
            conf = self.llm_config.get('local_ollama', {})
            self.client = OpenAI(
                base_url=conf.get('base_url', 'http://localhost:11434/v1'),
                api_key=conf.get('api_key', 'ollama')
            )
            self.model_name = conf.get('model', 'llama3')
        elif provider == 'openai':
            conf = self.llm_config.get('openai', {})
            self.client = OpenAI(api_key=os.getenv(conf.get('api_key_env_var')))
            self.model_name = conf.get('model', 'gpt-4-turbo')

    def classify(self, text: str, filename: str = "Unknown") -> Dict[str, Any]:
        """
        Classifies the document using the LLM.
        Now accepts 'filename' for better logging traceability.
        """
        system_prompt = f"""
        You are an intelligent document archivist.
        TODAY'S DATE: {datetime.date.today()} 

        --- ALLOWED CATEGORIES ---
        {self.category_prompt_str}
        
        --- INSTRUCTIONS ---
        1. Analyze the document text provided.
        2. Select the BEST matching Category ID.
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
            "summary": "A US B1/B2 Visa issued to John Doe."
        }}
        """

        # Truncate text to fit context window
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
            data = json.loads(result_json)
            
            # Validation Logic
            if data.get("category_id") not in self.valid_ids:
                logger.warning(f"⚠️  [{filename}] Invalid ID '{data.get('category_id')}'. Defaulting to 'uncategorized'.")
                data["category_id"] = "uncategorized"

            return data

        except Exception as e:
            # Only print/log real errors, not just confusion
            logger.error(f"❌ [{filename}] Classification failed: {e}")
            return {
                "category_id": "uncategorized",
                "confidence_score": 0.0,
                "summary": "Error during classification.",
                "error": str(e)
            }