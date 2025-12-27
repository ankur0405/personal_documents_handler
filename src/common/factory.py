import importlib
from src.config.loader import SETTINGS
from src.common import extractors
from src.common.interfaces import BaseExtractor

class ExtractorFactory:
    _registry = {}

    @classmethod
    def register_all(cls):
        """
        Dynamically registers classes based on YAML config.
        """
        # Map string names to actual classes in 'extractors.py'
        # e.g. "PDFExtractor" -> extractors.PDFExtractor
        mapping = SETTINGS['supported_extensions']
        
        for ext, class_name in mapping.items():
            if hasattr(extractors, class_name):
                cls._registry[ext] = getattr(extractors, class_name)

    @classmethod
    def get_extractor(cls, file_ext: str) -> BaseExtractor:
        if not cls._registry:
            cls.register_all()
            
        extractor_class = cls._registry.get(file_ext.lower())
        if extractor_class:
            return extractor_class() # Instantiate
        return None