from src.config.loader import SETTINGS
# Import everything from our new package
from src.extractors import *

class ExtractorFactory:
    @staticmethod
    def get_extractor(file_extension):
        """
        Returns an instance of the appropriate extractor class based on extension.
        """
        mapping = SETTINGS.get('supported_extensions', {})
        extractor_class_name = mapping.get(file_extension)
        
        if not extractor_class_name:
            return None
        
        # Look up the class in the global namespace of this module
        # (Since we imported * from src.extractors, they are available here)
        extractor_class = globals().get(extractor_class_name)
        
        if extractor_class:
            return extractor_class()
        
        return None