from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/karwan",
        description="PostgreSQL async connection URL with PostGIS"
    )

    # JWT / Auth
    SECRET_KEY: str = Field(
        default="",
        description="JWT signing key - must be set in environment"
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRATION_MINUTES: int = Field(default=30)

    # Request #1 - Intent LLM (project owner's credentials)
    REQUEST1_GEMINI_API_KEY: str = Field(default="", description="Primary Intent LLM API key")
    REQUEST1_GEMINI_MODEL: str = Field(default="gemini-1.5-flash", description="Gemini model for Request #1")
    REQUEST1_GEMINI_BASE_URL: str = Field(default="https://generativelanguage.googleapis.com/v1beta", description="Gemini API base URL")
    REQUEST1_GROQ_API_KEY: str = Field(default="", description="Fallback Intent LLM API key")
    REQUEST1_GROQ_MODEL: str = Field(default="llama-3.1-70b-versatile", description="Groq model for Request #1")
    REQUEST1_GROQ_BASE_URL: str = Field(default="https://api.groq.com/openai/v1", description="Groq API base URL")

    # Request #2 - Response LLM (second contributor's credentials)
    REQUEST2_GEMINI_API_KEY: str = Field(default="", description="Primary Response LLM API key")
    REQUEST2_GEMINI_MODEL: str = Field(default="gemini-1.5-flash", description="Gemini model for Request #2")
    REQUEST2_GEMINI_BASE_URL: str = Field(default="https://generativelanguage.googleapis.com/v1beta", description="Gemini API base URL")
    REQUEST2_GROQ_API_KEY: str = Field(default="", description="Fallback Response LLM API key")
    REQUEST2_GROQ_MODEL: str = Field(default="llama-3.1-70b-versatile", description="Groq model for Request #2")
    REQUEST2_GROQ_BASE_URL: str = Field(default="https://api.groq.com/openai/v1", description="Groq API base URL")

    # Speech-to-text (voice input only)
    GROQ_WHISPER_API_KEY: str = Field(default="", description="Groq Whisper ASR API key")
    GROQ_WHISPER_MODEL: str = Field(default="whisper-large-v3", description="Groq Whisper model")
    GROQ_WHISPER_BASE_URL: str = Field(default="https://api.groq.com/openai/v1", description="Groq Whisper API base URL")

    # Predictive ETA
    ETA_PROVIDER: str = Field(default="local")

    # Routing
    ROUTING_PROVIDER: str = Field(default="osrm")
    OSRM_BASE_URL: str = Field(default="http://router.project-osrm.org")

    # Nominatim
    NOMINATIM_BASE_URL: str = Field(default="https://nominatim.openstreetmap.org")
    NOMINATIM_USER_AGENT: str = Field(default="karwan-e-khizr/1.0")

    # Rate limiting
    RATE_LIMIT_LOGIN: int = Field(default=5, description="Login attempts per minute")
    RATE_LIMIT_VALIDATE: int = Field(default=30, description="Ticket validations per minute")
    RATE_LIMIT_CONVERSE: int = Field(default=10, description="AI converse requests per minute")

    # QR signing
    QR_SIGNING_KEY: str = Field(default="", description="Server-side secret for QR payload signing")

    # CORS
    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://localhost:5173")

    # App
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")


settings = Settings()


def validate_required_settings() -> None:
    missing = []
    if not settings.SECRET_KEY:
        missing.append("SECRET_KEY")
    if not settings.REQUEST1_GEMINI_API_KEY and not settings.REQUEST1_GROQ_API_KEY:
        missing.append("REQUEST1_GEMINI_API_KEY or REQUEST1_GROQ_API_KEY")
    if not settings.REQUEST2_GEMINI_API_KEY and not settings.REQUEST2_GROQ_API_KEY:
        missing.append("REQUEST2_GEMINI_API_KEY or REQUEST2_GROQ_API_KEY")
    if not settings.GROQ_WHISPER_API_KEY:
        missing.append("GROQ_WHISPER_API_KEY")
    if not settings.QR_SIGNING_KEY:
        missing.append("QR_SIGNING_KEY")

    if missing and settings.APP_ENV == "production":
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")