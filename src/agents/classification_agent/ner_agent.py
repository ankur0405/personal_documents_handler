import spacy

class EntityDiscovery:
    """
    Uses NLP to find 'Who' a document belongs to without a reference list.
    """
    def __init__(self):
        # Load lightweight NLP model (en_core_web_sm)
        self.nlp = spacy.load("en_core_web_sm")

    def get_owner(self, text):
        """Extracts the most prominent 'Person' entity from the text."""
        doc = self.nlp(text[:1500]) # Scan first 1500 chars for identification

        # Filter for entities labeled as 'PERSON' by the NLP model
        people = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]

        # Return the most frequent name or 'Unassigned'
        return people[0] if people else "System_Unassigned"