import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "DialoGPTChatAPI"
    DEBUG: bool = True
    MODEL_NAME: str = "microsoft/DialoGPT-small"
    MAX_HISTORY: int = 20
    SPACE_FOR_GENERATION: int = 10
    # Generation parameters
    MAX_LENGTH: int = 50  # Maximum length of the generated response
    MIN_LENGTH: int = 10  # Minimum length of the generated response
    TEMPERATURE: float = 0.7  # Controls randomness (0.0-1.0)
    TOP_P: float = 0.9  # Nucleus sampling parameter
    NO_REPEAT_NGRAM_SIZE: int = 3  # Prevents repetition of n-grams
    LOG_LEVEL: str = "DEBUG"
    # Session management settings
    SESSION_TIMEOUT_MINUTES: int = 30  # How long until a session expires
    SESSION_CLEANUP_INTERVAL: int = 10  # Clean up after every N new sessions
    BEAMS: int = 1 # TODO support multiple beams

    class Config:
        env_file = ".env"

