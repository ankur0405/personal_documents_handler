from .pdf import PDFExtractor
from .image import ImageExtractor
from .office import DocxExtractor, SlideExtractor, SpreadsheetExtractor, TextExtractor
from .email import EmailExtractor

# Define what happens when someone does "from src.extractors import *"
__all__ = [
    "PDFExtractor",
    "ImageExtractor",
    "DocxExtractor",
    "SlideExtractor",
    "SpreadsheetExtractor",
    "TextExtractor",
    "EmailExtractor"
]