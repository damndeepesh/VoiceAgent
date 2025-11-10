import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from twilio.twiml.voice_response import VoiceResponse, Say, Record, Play, Redirect
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant

from .config import get_settings
from .stt import transcribe_from_url
from .llm import generate_response
from .memory import load_history, append_message
from .tts import synthesize
from .twilio_utils import validate_twilio_signature


settings = get_settings()

app = FastAPI(title="Riverwood AI Voice Agent", version="0.1.0")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

os.makedirs(settings.media_dir, exist_ok=True)

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
	app.mount("/static", StaticFiles(directory=static_dir), name="static")
CLIENT_PAGE = static_dir / "client.html"


@app.get("/health")
def health() -> dict:
	return {"status": "ok"}


def _public_url(path: str, request: Request | None = None) -> str:
	base = settings.api_base_url or ""
	if base:
		return f"{base}{path}"
	# Derive from incoming request for PR/preview environments
	if request is not None:
		try:
			return str(request.url_for("media", filename=path.split("/")[-1]))
		except Exception:
			pass
	return path


@app.post("/voice", response_class=PlainTextResponse, include_in_schema=False)
async def voice(request: Request) -> str:
	form = await request.form()
	from_number: str = str(form.get("From", ""))
	call_sid: str = str(form.get("CallSid", uuid.uuid4().hex))

	# Validate Twilio signature
	sig = request.headers.get("X-Twilio-Signature")
	if not validate_twilio_signature(str(request.url), form, sig):
		return str(VoiceResponse())  # empty TwiML

	vr = VoiceResponse()
	vr.say("Namaste! Riverwood Projects se baat ho rahi hai.", voice="alice", language="en-IN")
	# Optional: Twilio Media Streams for lower latency
	if settings.twilio_use_streaming:
		stream_url = (settings.api_base_url or str(request.base_url).rstrip("/")) + "/media-stream"
		vr.start().stream(url=stream_url, track="inbound")
		# Keep the call open to stream audio; adjust as needed
		vr.pause(length=60)
	else:
		vr.say("Beep ke baad boliye.", voice="alice", language="en-IN")
		vr.record(
			action="/process-recording",
			method="POST",
			max_length=30,
			timeout=1,
			play_beep=False,
		)
	return str(vr)


@app.post("/process-recording", response_class=PlainTextResponse, include_in_schema=False)
async def process_recording(request: Request) -> str:
	form = await request.form()
	call_sid: str = str(form.get("CallSid", uuid.uuid4().hex))
	recording_url: Optional[str] = form.get("RecordingUrl")
	caller: str = str(form.get("From", ""))

	# Validate Twilio signature
	sig = request.headers.get("X-Twilio-Signature")
	if not validate_twilio_signature(str(request.url), form, sig):
		return str(VoiceResponse())

	vr = VoiceResponse()
	if not recording_url:
		vr.say("Kshama kijiye, awaz record nahi ho payi. Dobara koshish karein.", voice="alice", language="en-IN")
		vr.redirect("/voice")
		return str(vr)

	# STT
	try:
		user_text = transcribe_from_url(recording_url, language="hi")
	except Exception:
		user_text = ""

	if not user_text:
		vr.say("Mujhe theek se sunai nahin diya. Kripya dobara kahe.", voice="alice", language="en-IN")
		vr.redirect("/voice")
		return str(vr)

	# Memory + LLM
	history = load_history(call_sid)
	append_message(call_sid, "user", user_text)
	reply_text = ""
	try:
		reply_text = generate_response(history + [{"role": "user", "content": user_text}])
	except Exception:
		reply_text = "Namaste! Aapki baat samajh aayi. Thodi der baad phir se koshish karte hain."

	append_message(call_sid, "assistant", reply_text)

	# TTS -> file
	try:
		audio_path = await synthesize(reply_text)
	except Exception:
		# Fallback to Twilio TTS if synthesis fails
		vr.say(reply_text, voice="alice", language="en-IN")
		vr.redirect("/voice")
		return str(vr)

	filename = os.path.basename(audio_path)
	play_url = _public_url(f"/media/{filename}", request=request)
	vr.play(play_url)
	vr.redirect("/voice")
	return str(vr)


@app.get("/media/{filename}")
async def media(filename: str):
	path = os.path.join(settings.media_dir, filename)
	return FileResponse(path, media_type="audio/mpeg")


@app.post("/client-voice", response_class=PlainTextResponse, include_in_schema=False)
async def client_voice(request: Request) -> str:
	form = await request.form()
	sig = request.headers.get("X-Twilio-Signature")
	if not validate_twilio_signature(str(request.url), form, sig):
		return str(VoiceResponse())

	to_number = str(form.get("To") or "").strip()
	vr = VoiceResponse()
	if not to_number:
		vr.say("Destination number missing.")
		return str(vr)

	dial_kwargs = {}
	if settings.twilio_number:
		dial_kwargs["callerId"] = settings.twilio_number
	dial = vr.dial(**dial_kwargs)
	dial.number(to_number)
	return str(vr)


@app.websocket("/media-stream")
async def media_stream(ws: WebSocket):
	# Accept Twilio Media Streams WebSocket
	await ws.accept()
	# Minimal buffering; full streaming STT can be added if needed
	try:
		while True:
			msg = await ws.receive_json()
			# Twilio sends event types: start, media, stop, mark, etc.
			event = msg.get("event", "")
			if event == "start":
				# Acknowledge start
				pass
			elif event == "media":
				# media payload has base64 audio in msg["media"]["payload"]
				# Here we could buffer and periodically run STT for near-real-time responses.
				pass
			elif event == "stop":
				break
	except WebSocketDisconnect:
		pass
	finally:
		try:
			await ws.close()
		except Exception:
			pass


@app.get("/client", response_class=HTMLResponse, include_in_schema=False)
async def client_page():
	if CLIENT_PAGE.exists():
		return HTMLResponse(CLIENT_PAGE.read_text(encoding="utf-8"))
	return HTMLResponse("<h1>Client page not found</h1>", status_code=404)


@app.get("/client-token")
async def client_token(identity: Optional[str] = None):
	if not all([settings.twilio_account_sid, settings.twilio_api_key_sid, settings.twilio_api_key_secret]):
		return JSONResponse({"error": "Twilio account SID, API key SID, or API key secret missing."}, status_code=400)
	if not settings.twilio_twiml_app_sid:
		return JSONResponse({"error": "Twilio TwiML App SID missing."}, status_code=400)

	identity_to_use = identity or settings.twilio_client_identity
	token = AccessToken(
		settings.twilio_account_sid,
		settings.twilio_api_key_sid,
		settings.twilio_api_key_secret,
		identity=identity_to_use,
	)
	voice_grant = VoiceGrant(
		outgoing_application_sid=settings.twilio_twiml_app_sid,
		incoming_allow=True,
	)
	token.add_grant(voice_grant)
	jwt = token.to_jwt()
	jwt_str = jwt.decode("utf-8") if isinstance(jwt, bytes) else jwt
	return {"token": jwt_str, "identity": identity_to_use}


