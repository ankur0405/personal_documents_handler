# Minimal __init__.py to prevent eager loading of heavy dependencies
from .base import BaseExtractor

__all__ = ["BaseExtractor"]