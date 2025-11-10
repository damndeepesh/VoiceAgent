from typing import List, Dict, Any
from upstash_redis import Redis
from .config import get_settings


settings = get_settings()

redis_client: Redis | None = None
if settings.upstash_redis_url and settings.upstash_redis_token:
	redis_client = Redis(url=settings.upstash_redis_url, token=settings.upstash_redis_token)


def _key(call_sid: str) -> str:
	return f"call:{call_sid}:history"


def load_history(call_sid: str) -> List[Dict[str, str]]:
	if not redis_client:
		return []
	items = redis_client.lrange(_key(call_sid), 0, settings.max_history_messages - 1)
	history: List[Dict[str, str]] = []
	for raw in items or []:
		try:
			role, content = raw.split("::", 1)
			history.append({"role": role, "content": content})
		except Exception:
			continue
	return history


def append_message(call_sid: str, role: str, content: str) -> None:
	if not redis_client:
		return
	redis_client.lpush(_key(call_sid), f"{role}::{content}")
	redis_client.ltrim(_key(call_sid), 0, settings.max_history_messages - 1)
	redis_client.expire(_key(call_sid), settings.redis_ttl_seconds)


