import os
import tempfile
import uuid
from typing import Optional

import requests
from faster_whisper import WhisperModel

from .config import get_settings


settings = get_settings()
_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
	global _model
	if _model is None:
		_model = WhisperModel(
			settings.whisper_model,
			device="auto",
			compute_type=settings.whisper_compute_type,
		)
	return _model


def download_file(url: str) -> str:
	resp = requests.get(url, stream=True, timeout=30)
	resp.raise_for_status()
	fd, path = tempfile.mkstemp(prefix=f"twilio_{uuid.uuid4().hex}_", suffix=".mp3")
	with os.fdopen(fd, "wb") as f:
		for chunk in resp.iter_content(chunk_size=8192):
			if chunk:
				f.write(chunk)
	return path


def transcribe_from_url(recording_url: str, language: Optional[str] = "hi") -> str:
	local_path = download_file(recording_url)
	try:
		model = _get_model()
		segments, info = model.transcribe(local_path, language=language, beam_size=1)
		text_parts = [seg.text for seg in segments]
		return " ".join([t.strip() for t in text_parts if t]).strip()
	finally:
		try:
			os.remove(local_path)
		except Exception:
			pass


