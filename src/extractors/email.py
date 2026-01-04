import email
from email import policy
from pathlib import Path
from src.common.utils import get_logger

logger = get_logger(__name__)

class EmailExtractor:
    def __init__(self):
        self.name = "Enterprise Email Extractor"

    def extract(self, file_path):
        path = Path(file_path)
        content = ""
        metadata = {"subject": "", "from": "", "date": ""}

        try:
            with open(path, 'rb') as f:
                # policy.default enables the modern EmailMessage API
                msg = email.message_from_binary_file(f, policy=policy.default)

            metadata["subject"] = str(msg.get('subject', 'No Subject'))
            metadata["from"] = str(msg.get('from', 'Unknown Sender'))
            metadata["date"] = str(msg.get('date', ''))

            # --- ROBUST BODY EXTRACTION ---
            if msg.is_multipart():
                parts = []
                for part in msg.walk():
                    content_type = part.get_content_type()
                    # FIX: Correct method name is get_content_disposition()
                    disposition = str(part.get_content_disposition())

                    if content_type == 'text/plain' and 'attachment' not in disposition:
                        payload = part.get_content() # Modern API uses get_content()
                        parts.append(str(payload))
                    elif content_type == 'text/html' and not parts:
                        payload = part.get_content()
                        # Optional: Add BeautifulSoup here if you want to strip HTML tags
                        parts.append(str(payload))
                
                content = "\n".join(parts)
            else:
                content = str(msg.get_content())

            content = content.strip()
            
            # Fallback if body is still empty
            if not content:
                content = f"Subject: {metadata['subject']}\nFrom: {metadata['from']}"

            return content, metadata

        except Exception as e:
            logger.error(f"❌ Email Extraction Failed for {path.name}: {e}")
            # Return a non-empty string to prevent 'index out of range' in OCR engine
            return f"Error extracting {path.name}", metadata