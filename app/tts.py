import asyncio
import os
import uuid
from typing import Literal

import edge_tts
import requests

from .config import get_settings


settings = get_settings()


async def synthesize_edge(text: str, voice: str | None = None) -> str:
	voice_to_use = voice or settings.edge_voice
	filename = f"{uuid.uuid4().hex}.mp3"
	os.makedirs(settings.media_dir, exist_ok=True)
	out_path = os.path.join(settings.media_dir, filename)
	communicate = edge_tts.Communicate(text=text, voice=voice_to_use)
	with open(out_path, "wb") as f:
		async for chunk in communicate.stream():
			if chunk["type"] == "audio":
				f.write(chunk["data"])
	return out_path


async def synthesize_elevenlabs(text: str, voice_id: str | None = None) -> str:
	if not settings.elevenlabs_api_key:
		raise RuntimeError("ELEVENLABS_API_KEY not configured")
	voice = voice_id or settings.elevenlabs_voice_id
	url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
	headers = {
		"xi-api-key": settings.elevenlabs_api_key,
		"accept": "audio/mpeg",
		"content-type": "application/json",
	}
	data = {
		"text": text,
		"model_id": "eleven_monolingual_v1",
		"voice_settings": {"stability": 0.5, "similarity_boost": 0.6},
	}
	# Use async HTTP client to avoid blocking
	import aiohttp
	import logging
	logger = logging.getLogger(__name__)
	try:
		async with aiohttp.ClientSession() as session:
			async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
				if resp.status != 200:
					error_text = await resp.text()
					logger.error(f"ElevenLabs API error {resp.status}: {error_text}")
					raise RuntimeError(f"ElevenLabs API returned {resp.status}: {error_text}")
				audio_data = await resp.read()
	except Exception as e:
		logger.error(f"ElevenLabs synthesis failed: {e}")
		raise
	filename = f"{uuid.uuid4().hex}.mp3"
	os.makedirs(settings.media_dir, exist_ok=True)
	out_path = os.path.join(settings.media_dir, filename)
	with open(out_path, "wb") as f:
		f.write(audio_data)
	logger.info(f"ElevenLabs TTS generated: {filename} ({len(audio_data)} bytes)")
	return out_path


async def synthesize(text: str) -> str:
	if settings.tts_provider == "elevenlabs":
		return await synthesize_elevenlabs(text)
	return await synthesize_edge(text)


