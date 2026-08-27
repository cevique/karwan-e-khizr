from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipeline import ConversationPipeline, get_conversation_pipeline
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AIProviderError, ProviderError, ValidationError
from app.users.dependencies import get_current_user_or_none
from app.db.models.user import User

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/converse", status_code=status.HTTP_200_OK)
async def converse(
    message: str | None = Form(default=None),
    audio: UploadFile | None = File(default=None),
    session: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_or_none),
) -> dict:
    if message is None and audio is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Exactly one of 'message' or 'audio' must be provided.",
        )

    if message is not None and audio is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either 'message' or 'audio', not both.",
        )

    pipeline = await get_conversation_pipeline()

    try:
        if message is not None:
            if not message.strip():
                raise ValidationError("Message cannot be empty")
            result = await pipeline.process_text(message.strip(), session)
        else:
            if not audio.content_type or not audio.content_type.startswith("audio/"):
                raise ValidationError(
                    "Audio file must have a valid audio content type",
                    details={"received_content_type": audio.content_type},
                )
            audio_bytes = await audio.read()
            if not audio_bytes:
                raise ValidationError("Audio file is empty")
            result = await pipeline.process_audio(audio_bytes, audio.content_type, session)

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"detail": e.message, "code": e.code, **e.details},
        )
    except AIProviderError as e:
        if e.details.get("request_stage") == 1:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "detail": e.message,
                    "code": e.code,
                    "request_stage": e.details.get("request_stage"),
                    "provider": e.details.get("provider"),
                },
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "detail": e.message,
                    "code": e.code,
                    "request_stage": e.details.get("request_stage"),
                    "provider": e.details.get("provider"),
                },
            )
    except ProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "detail": e.message,
                "code": e.code,
                "provider": e.details.get("provider"),
            },
        )

    return result


@router.get("/health", status_code=status.HTTP_200_OK)
async def ai_health() -> dict:
    def check_provider_status(key_name: str) -> str:
        key_value = getattr(settings, key_name, "")
        return "configured" if key_value else "not_configured"

    return {
        "speech_to_text": {
            "provider": "groq_whisper",
            "status": check_provider_status("GROQ_WHISPER_API_KEY"),
        },
        "intent_llm": {
            "primary": "gemini" if settings.REQUEST1_GEMINI_API_KEY else "groq",
            "fallback": "groq" if settings.REQUEST1_GEMINI_API_KEY else "gemini",
            "status": "configured"
            if (settings.REQUEST1_GEMINI_API_KEY or settings.REQUEST1_GROQ_API_KEY)
            else "not_configured",
        },
        "response_llm": {
            "primary": "gemini" if settings.REQUEST2_GEMINI_API_KEY else "groq",
            "fallback": "groq" if settings.REQUEST2_GEMINI_API_KEY else "gemini",
            "status": "configured"
            if (settings.REQUEST2_GEMINI_API_KEY or settings.REQUEST2_GROQ_API_KEY)
            else "not_configured",
        },
    }