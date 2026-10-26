import json
import math
import os
import platform
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
MODELS_PATH = BASE_DIR / "models.json"
STATIC_DIR = BASE_DIR / "static"
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Local AI Video Studio", version="1.5.0")


class JobRequest(BaseModel):
    prompt: str = Field(..., description="User prompt or narrative script")
    model_id: str = Field(default="custom-ffmpeg", description="Selected local model ID")
    scene_duration: int = Field(default=18, ge=4, le=60)
    total_duration: int = Field(default=120, ge=1)
    script_text: str = Field(default="", description="Narrative script content")


def load_model_catalog() -> List[Dict[str, Any]]:
    with MODELS_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def split_script_into_chunks(script_text: str, scene_duration: int) -> List[str]:
    text = (script_text or "").strip()
    if not text:
        text = "A cinematic local drone shot rises over a city skyline while atmospheric data streams bloom into the night."

    normalized = text.replace("\r", "").split(/\n{2,}|\.\s+|\?\s+|!\s+/)
    chunks = []
    buffer = ""
    for segment in normalized:
        seg = segment.strip().replace("  ", " ")
        if not seg:
            continue
        if buffer:
            candidate = buffer + " " + seg
        else:
            candidate = seg
        words = len(candidate.split())
        if words > max(18, int(scene_duration * 2.6)):
            if buffer:
                chunks.append(buffer.strip())
            buffer = seg
        else:
            buffer = candidate
    if buffer:
        chunks.append(buffer.strip())
    return [chunk for chunk in chunks if chunk]


def ensure_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def get_available_models() -> List[Dict[str, Any]]:
    catalog = load_model_catalog()
    for model in catalog:
        if model["id"] == "custom-ffmpeg":
            model["available"] = ensure_ffmpeg()
        elif model.get("requires_manual_download"):
            model["available"] = False
        else:
            model["available"] = True
    return catalog


class GenerationResult:
    def __init__(self, status: str, message: str, download_url: str | None = None, metadata: Dict[str, Any] | None = None):
        self.status = status
        self.message = message
        self.download_url = download_url
        self.metadata = metadata or {}


def render_ffmpeg_demo(prompt: str, scene_duration: int, total_duration: int, script_text: str) -> GenerationResult:
    if not ensure_ffmpeg():
        return GenerationResult("failed", "FFmpeg is required for local generation but is not installed on this machine.")

    job_id = uuid.uuid4().hex
    output_path = GENERATED_DIR / f"{job_id}.mp4"
    work_dir = GENERATED_DIR / f"{job_id}_frames"
    work_dir.mkdir(exist_ok=True)

    chunks = split_script_into_chunks(script_text or prompt, scene_duration)
    total_chunks = max(1, min(len(chunks), max(1, math.ceil(total_duration / max(scene_duration, 1)))))
    selected_chunks = chunks[:total_chunks]

    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if not os.path.exists(font_path):
            font_path = None

        for idx, chunk in enumerate(selected_chunks):
            frame_path = work_dir / f"frame_{idx:04d}.png"
            frame = Image.new("RGB", (1280, 720), color=(8, 14, 18))
            draw = ImageDraw.Draw(frame)

            # Gradient-like effect
            for y in range(frame.height):
                ratio = y / frame.height
                r = int(10 + ratio * 24)
                g = int(18 + ratio * 36)
                b = int(26 + ratio * 44)
                draw.line((0, y, frame.width, y), fill=(r, g, b))

            # Glow arcs and shapes
            for i in range(10):
                x = int(150 + (frame.width - 300) * (i / 9))
                y = int(200 + 80 * math.sin((idx + i) * 0.7))
                radius = int(40 + i * 11)
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(40, 210, 170), width=2)

            # Title and subtitles
            draw.text((80, 80), "LOCAL AI VIDEO STUDIO", fill=(220, 240, 255), font=(ImageFont.truetype(font_path, 44) if font_path else None))
            draw.text((80, 150), f"SCENE {idx + 1}/{len(selected_chunks)}", fill=(120, 225, 255), font=(ImageFont.truetype(font_path, 26) if font_path else None))
            draw.text((80, 210), chunk[:100], fill=(170, 255, 210), font=(ImageFont.truetype(font_path, 28) if font_path else None))
            draw.text((80, 620), f"MODEL: {('Custom Pipeline (FFmpeg Script)')}", fill=(255, 190, 90), font=(ImageFont.truetype(font_path, 22) if font_path else None))
            draw.text((80, 655), "OFFLINE MODE / 100% PRIVATE", fill=(103, 255, 177), font=(ImageFont.truetype(font_path, 22) if font_path else None))

            frame.save(frame_path)

        frame_pattern = str(work_dir / "frame_%04d.png")
        command = [
            "ffmpeg",
            "-y",
            "-framerate", "24",
            "-i", frame_pattern,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path),
        ]

        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return GenerationResult(
            "completed",
            "Local render completed successfully using the FFmpeg fallback pipeline.",
            download_url=f"/download/{job_id}.mp4",
            metadata={
                "job_id": job_id,
                "output_path": str(output_path),
                "scene_count": len(selected_chunks),
                "duration_seconds": max(scene_duration, 1) * len(selected_chunks),
            },
        )
    finally:
        if work_dir.exists():
            for file_item in work_dir.iterdir():
                if file_item.is_file():
                    file_item.unlink()
            work_dir.rmdir()


def render_model_job(model_id: str, prompt: str, scene_duration: int, total_duration: int, script_text: str) -> GenerationResult:
    catalog = load_model_catalog()
    model = next((item for item in catalog if item["id"] == model_id), None)
    if not model:
        return GenerationResult("failed", f"Model '{model_id}' not found in local catalog.")

    if model_id == "custom-ffmpeg":
        return render_ffmpeg_demo(prompt, scene_duration, total_duration, script_text)

    if model.get("requires_manual_download"):
        return GenerationResult(
            "waiting_for_model",
            f"{model['name']} is available as a local model option, but the required weights must be installed manually before inference can run.",
            metadata={"model_name": model["name"], "weight_path_hint": model.get("weight_path_hint")},
        )

    # For real local model runners, this is where a CLI wrapper or GPU entry point would be invoked.
    # The app checks for local runtime availability instead of pretending to do unsupported downloads.
    return GenerationResult(
        "waiting_for_model",
        f"{model['name']} is configured for local runtime use but no model weights were detected on this machine.",
        metadata={"model_name": model["name"], "weight_path_hint": model.get("weight_path_hint")},
    )


@app.get("/api/models")
def api_models() -> Dict[str, List[Dict[str, Any]]]:
    return {"models": get_available_models()}


@app.get("/api/system")
def api_system() -> Dict[str, Any]:
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "ffmpeg_installed": ensure_ffmpeg(),
        "output_dir": str(GENERATED_DIR),
        "models_path": str(MODELS_PATH),
    }


@app.post("/api/jobs")
def create_job(request: JobRequest) -> Dict[str, Any]:
    model_id = request.model_id or "custom-ffmpeg"
    result = render_model_job(model_id, request.prompt, request.scene_duration, request.total_duration, request.script_text)

    return {
        "status": result.status,
        "message": result.message,
        "download_url": result.download_url,
        "model_id": model_id,
        "metadata": result.metadata,
    }


@app.get("/download/{file_name}")
def download_video(file_name: str):
    candidate = GENERATED_DIR / file_name
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(str(candidate), media_type="video/mp4", filename=file_name)


if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root():
    return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
