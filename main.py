import os
import io
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

app = FastAPI(title="Tanglish SRT Studio")

ALLOWED_EXTENSIONS = {
    ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav",
    ".webm", ".ogg", ".flac", ".mov", ".mkv"
}
MAX_BYTES = 25 * 1024 * 1024

def timestamp(seconds: float) -> str:
    ms_total = max(0, round(float(seconds) * 1000))
    hours, rem = divmod(ms_total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def get_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY missing. Hosting dashboard > Environment-la secret API key add pannunga."
        )
    return OpenAI(api_key=key)

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "Tanglish SRT Studio",
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY", "").strip())
    }

@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    client = get_client()
    filename = Path(file.filename or "upload.mp3").name
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Unsupported file type. Use MP3, WAV, M4A, MP4, WebM, MOV, MKV, OGG or FLAC.")
    content = await file.read()
    if not content:
        raise HTTPException(400, "Uploaded file is empty.")
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "File exceeds 25 MB. Compress or split it into smaller parts.")

    try:
        transcription = client.audio.transcriptions.create(
            model=os.getenv("TRANSCRIPTION_MODEL", "whisper-1"),
            file=(filename, io.BytesIO(content)),
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )
    except Exception as exc:
        # Keep error actionable without exposing secrets.
        msg = str(exc)
        if "401" in msg or "authentication" in msg.lower() or "api key" in msg.lower():
            raise HTTPException(502, "OpenAI API key invalid. Hosting Environment-la OPENAI_API_KEY check pannunga.")
        if "429" in msg or "quota" in msg.lower() or "billing" in msg.lower():
            raise HTTPException(502, "OpenAI API quota/billing issue. API account usage and billing check pannunga.")
        raise HTTPException(502, f"Transcription API failed: {msg[:220]}")

    segments = getattr(transcription, "segments", None) or []
    if not segments:
        raise HTTPException(502, "Transcription returned no timed segments. Try a clearer or shorter file.")

    output = []
    for seg in segments:
        text = (getattr(seg, "text", "") or "").strip()
        if not text:
            continue
        try:
            converted = client.chat.completions.create(
                model=os.getenv("ROMANIZATION_MODEL", "gpt-4.1-mini"),
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Convert this Tamil speech transcript to natural Tamil written in Latin "
                            "letters (Tanglish) for Tamil Nadu subtitles. Preserve the meaning, names, "
                            "numbers and English words already spoken. Do not translate Tamil to English. "
                            "Return only the converted subtitle text, no explanation."
                        )
                    },
                    {"role": "user", "content": text}
                ]
            ).choices[0].message.content or text
        except Exception as exc:
            msg = str(exc)
            if "401" in msg or "authentication" in msg.lower():
                raise HTTPException(502, "Romanization API authentication failed. Check OPENAI_API_KEY.")
            if "429" in msg or "quota" in msg.lower() or "billing" in msg.lower():
                raise HTTPException(502, "API quota/billing issue. Check OpenAI API account.")
            raise HTTPException(502, f"Tanglish conversion failed: {msg[:220]}")

        output.append({
            "start": float(getattr(seg, "start", 0)),
            "end": float(getattr(seg, "end", 0)),
            "text": converted.strip()
        })

    srt_parts = []
    for i, seg in enumerate(output, 1):
        srt_parts.append(
            f"{i}\n{timestamp(seg['start'])} --> {timestamp(seg['end'])}\n{seg['text']}\n"
        )
    return {
        "filename": Path(filename).stem + "_tanglish.srt",
        "srt": "\n".join(srt_parts),
        "segments": output
    }

# Serve frontend and API from the same domain. Mount must stay last.
app.mount("/", StaticFiles(directory="public", html=True), name="public")
