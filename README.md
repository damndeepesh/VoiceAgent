# Riverwood AI Voice Agent (Twilio + Whisper + Gemini + edge-tts) on Railway

This is a callable AI voice agent for Riverwood Projects. It receives phone calls via Twilio, performs on-box speech-to-text with open-source Whisper (faster-whisper), generates responses using Gemini (or Grok), synthesizes speech with edge-tts or ElevenLabs, stores memory in Upstash Redis, and serves audio to Twilio.

## Architecture

User calls → Twilio → FastAPI (Railway) → faster-whisper (STT) → Gemini/Grok (LLM) → edge-tts/ElevenLabs (TTS) → Redis memory (Upstash) → back to user

## Key Endpoints

- `POST /voice`: Twilio webhook for incoming/continued calls. Returns TwiML asking the caller to speak.
- `POST /process-recording`: Receives Twilio recording, runs STT, LLM, TTS, plays result, then loops.
- `GET /media/{filename}`: Serves synthesized audio files for Twilio `<Play>`.
- `GET /health`: Healthcheck for Railway.

## Environment Variables

Set these in Railway Variables:

- PUBLIC_URL: e.g. https://your-service.up.railway.app
- TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_NUMBER
- LLM_PROVIDER: gemini | grok
- GEMINI_API_KEY, GEMINI_MODEL (gemini-1.5-flash)
- GROK_API_KEY, GROK_MODEL (optional alternative)
- WHISPER_MODEL: tiny | base | small | medium | large-v3 (recommend `small` on Railway)
- WHISPER_COMPUTE_TYPE: auto
- TTS_PROVIDER: edge | elevenlabs
- EDGE_VOICE: e.g. en-IN-NeerjaNeural
- ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID (if using elevenlabs)
- UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
- REDIS_TTL_SECONDS (default 86400), MAX_HISTORY_MESSAGES (default 20)
- MEDIA_DIR: media

## Local Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PORT=8000
uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload
```

## Deploy on Railway

1. Create new Railway project and connect this repo.
2. Add variables listed above in the Railway dashboard.
3. Deploy. Healthcheck is `/health`. Service starts with uvicorn.

Note: Nixpacks installs `ffmpeg` via `nixpacks.toml` for faster-whisper.

## Twilio Setup

1. Buy a Twilio number.
2. Set Voice webhook (HTTP POST) for the number to: `https://YOUR_PUBLIC_URL/voice`
3. Ensure `PUBLIC_URL` matches the deployed Railway URL so TwiML `<Play>` URLs resolve.

## Costs and Choices

- STT: Open-source faster-whisper (no OpenAI). Choose `small` for latency/accuracy balance.
- LLM: Default Gemini (`gemini-1.5-flash`) for speed/cost; can switch to Grok via env.
- TTS: Default `edge-tts` (free). Set `TTS_PROVIDER=elevenlabs` to use ElevenLabs premium.

## Security

Do not commit secrets. Use Railway variables. Regenerate any leaked keys before production.


