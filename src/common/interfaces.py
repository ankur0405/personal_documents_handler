from abc import ABC, abstractmethod
from typing import Generator, Tuple

class BaseExtractor(ABC):
    """
    The Interface. All plugins must obey this.
    """
    @abstractmethod
    def extract(self, file_path: str) -> Generator[Tuple[int, str], None, None]:
        """
        Yields (page_number, text_content) tuples.
        Must handle its own file opening/closing.
        """
        pass