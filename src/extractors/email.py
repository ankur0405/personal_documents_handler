import extract_msg
from .base import BaseExtractor

class EmailExtractor(BaseExtractor):
    def extract(self, file_path):
        try:
            msg = extract_msg.Message(file_path)
            content = f"Subject: {msg.subject}\nFrom: {msg.sender}\nTo: {msg.to}\n\n{msg.body}"
            msg.close()
            if content.strip(): yield 1, content
        except Exception:
            pass