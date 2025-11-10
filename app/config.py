import os
from functools import lru_cache


class Settings:
	api_base_url: str = os.getenv("PUBLIC_URL", "").rstrip("/")
	port: int = int(os.getenv("PORT", "8000"))

	# Twilio
	twilio_account_sid: str | None = os.getenv("TWILIO_ACCOUNT_SID")
	twilio_auth_token: str | None = os.getenv("TWILIO_AUTH_TOKEN")
	twilio_number: str | None = os.getenv("TWILIO_NUMBER")
	twilio_validate_signatures: bool = os.getenv("TWILIO_VALIDATE", "true").lower() == "true"
	twilio_use_streaming: bool = os.getenv("TWILIO_USE_STREAMING", "false").lower() == "true"
	twilio_api_key_sid: str | None = os.getenv("TWILIO_API_KEY_SID")
	twilio_api_key_secret: str | None = os.getenv("TWILIO_API_KEY_SECRET")
	twilio_twiml_app_sid: str | None = os.getenv("TWILIO_TWIML_APP_SID")
	twilio_client_identity: str = os.getenv("TWILIO_CLIENT_IDENTITY", "riverwood-agent")

	# STT
	whisper_model: str = os.getenv("WHISPER_MODEL", "small")
	whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "auto")

	# LLM
	llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")  # gemini | grok
	gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
	gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
	grok_api_key: str | None = os.getenv("GROK_API_KEY")
	grok_model: str = os.getenv("GROK_MODEL", "grok-beta")

	# TTS
	tts_provider: str = os.getenv("TTS_PROVIDER", "edge")  # edge | elevenlabs
	edge_voice: str = os.getenv("EDGE_VOICE", "en-IN-NeerjaNeural")
	elevenlabs_api_key: str | None = os.getenv("ELEVENLABS_API_KEY")
	elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

	# Redis (Upstash)
	upstash_redis_url: str | None = os.getenv("UPSTASH_REDIS_REST_URL")
	upstash_redis_token: str | None = os.getenv("UPSTASH_REDIS_REST_TOKEN")
	redis_ttl_seconds: int = int(os.getenv("REDIS_TTL_SECONDS", "86400"))
	max_history_messages: int = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))

	# Files
	media_dir: str = os.getenv("MEDIA_DIR", "media")


@lru_cache
def get_settings() -> Settings:
	return Settings()


