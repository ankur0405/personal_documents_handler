import os
import sys

# Ensure Python can find your 'src' folder
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.agents.classification_agent.classifier import DocumentClassifier

def test_local_classification():
    print("--- Starting Local Classifier Test ---")
    
    # 1. Initialize the Agent (It will auto-read settings.yaml)
    try:
        classifier = DocumentClassifier()
        print(f"✅ Agent Initialized using model: {classifier.model_name}")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return

    # 2. Define a Dummy Document (simulating an OCR'd PDF)
    fake_document_text = """
    THE UNITED STATES OF AMERICA
    VISA
    Control Number: 202412345678
    Issuing Post Name: NEW DELHI
    Surname: SHARMA
    Given Name: ROHIT
    Passport Number: Z123456
    Entries: M
    Type: R B1/B2
    Issue Date: 15 JAN 2024
    Expiration Date: 12 JAN 2034
    Annotation: ESTA NOT REQUIRED
    """
    
    print(f"\n--- Input Text (First 200 chars) ---\n{fake_document_text[:200]}...")

    # 3. Run Classification
    print("\n--- Sending to Local AI (this may take a few seconds) ---")
    result = classifier.classify(fake_document_text)

    # 4. Show Results
    print("\n--- 🤖 AI Output ---")
    import json
    print(json.dumps(result, indent=2))
    
    # 5. Logical Checks
    if result.get("category_id") == "visa_document":
        print("\n✅ SUCCESS: Correctly identified as 'visa_document'")
    else:
        print(f"\n⚠️ WARNING: Identified as '{result.get('category_id')}' instead of 'visa_document'")

    if result.get("expiry_date") == "2034-01-12":
        print("✅ SUCCESS: Correctly extracted expiry date '2034-01-12'")
    else:
        print(f"⚠️ WARNING: Date extraction might be off: {result.get('expiry_date')}")

if __name__ == "__main__":
    test_local_classification()