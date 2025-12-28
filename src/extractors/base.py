from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str):
        """
        Yields a tuple of (page_number, text_content)
        """
        pass