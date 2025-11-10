from typing import List, Dict
import google.generativeai as genai
import requests

from .config import get_settings


settings = get_settings()


RIVERWOOD_SYSTEM_PROMPT = """You are a friendly AI voice agent for Riverwood Projects in Haryana.
PERSONALITY:
- Warm, conversational Hinglish
- Use: "Namaste", "chai pee li?", "kaise hain?"
- Build relationships, remember conversations
KNOWLEDGE:
- Riverwood Estate: 25 acres, Sector 7 Kharkhauda
- Near Maruti Suzuki plant
- Plots: 90-150 sq meters
- Under DDJAY scheme
STYLE:
- Keep responses short (2-3 sentences for calls)
- Natural and caring tone
- Reference previous conversations
- Invite for weekend visits
CONSTRUCTION UPDATES:
- Positive and specific
- Mention: foundation, walls, roofing progress
- Give realistic timelines
Respond concisely in Hinglish with warmth.
"""


def _gemini_chat(messages: List[Dict[str, str]]) -> str:
	if not settings.gemini_api_key:
		raise RuntimeError("GEMINI_API_KEY not configured")
	genai.configure(api_key=settings.gemini_api_key)
	model = genai.GenerativeModel(settings.gemini_model)
	# Convert to Gemini format
	history = []
	for m in messages:
		role = "user" if m["role"] == "user" else "model"
		history.append({"role": role, "parts": [m["content"]]})
	resp = model.generate_content(
		[RIVERWOOD_SYSTEM_PROMPT] + [h["parts"][0] for h in history],
		generation_config={"temperature": 0.6, "max_output_tokens": 200},
	)
	return (resp.text or "").strip()


def _grok_chat(messages: List[Dict[str, str]]) -> str:
	if not settings.grok_api_key:
		raise RuntimeError("GROK_API_KEY not configured")
	# xAI Grok API (OpenAI-compatible-ish schema may vary; using chat/completions style)
	url = "https://api.x.ai/v1/chat/completions"
	headers = {"Authorization": f"Bearer {settings.grok_api_key}"}
	payload = {
		"model": settings.grok_model,
		"messages": [{"role": "system", "content": RIVERWOOD_SYSTEM_PROMPT}] + messages,
		"temperature": 0.6,
		"max_tokens": 220,
	}
	resp = requests.post(url, json=payload, headers=headers, timeout=60)
	resp.raise_for_status()
	data = resp.json()
	return data["choices"][0]["message"]["content"].strip()


def generate_response(history: List[Dict[str, str]]) -> str:
	if settings.llm_provider == "grok":
		return _grok_chat(history)
	return _gemini_chat(history)


