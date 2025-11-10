from typing import Mapping
from twilio.request_validator import RequestValidator
from .config import get_settings


settings = get_settings()


def validate_twilio_signature(url: str, params: Mapping[str, str], signature: str | None) -> bool:
	if not settings.twilio_validate_signatures:
		return True
	if not settings.twilio_auth_token or not signature:
		return False
	validator = RequestValidator(settings.twilio_auth_token)
	return bool(validator.validate(url, dict(params), signature))


