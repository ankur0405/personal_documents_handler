import os
import yaml
from openai import OpenAI

# Path to settings.yaml
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_PATH = os.path.join(BASE_DIR, "config", "settings.yaml")

class LLMFactory:
    _config = None

    @classmethod
    def load_config(cls):
        if cls._config is None:
            if not os.path.exists(SETTINGS_PATH):
                raise FileNotFoundError(f"Settings file not found at: {SETTINGS_PATH}")
            with open(SETTINGS_PATH, "r") as f:
                cls._config = yaml.safe_load(f)
        return cls._config

    @classmethod
    def get_client(cls):
        """
        Returns a configured OpenAI Client (which works for Local Ollama too).
        """
        config = cls.load_config()
        provider = config["llm"]["provider"]

        if provider == "local_ollama":
            settings = config["llm"]["local_ollama"]
            return OpenAI(
                base_url=settings["base_url"],
                api_key=settings["api_key"]
            ), settings["model"]
            
        elif provider == "openai":
            settings = config["llm"]["openai"]
            api_key = os.environ.get(settings["api_key_env_var"])
            if not api_key:
                raise ValueError("OpenAI API Key environment variable is missing.")
            return OpenAI(api_key=api_key), settings["model"]
        
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    @classmethod
    def get_classifier_settings(cls):
        """Returns specific settings for the classifier agent."""
        config = cls.load_config()
        return config.get("classifier", {})