# Local AI Video Studio

This project is a local, self-hosted AI video studio backend built for local inference and offline rendering. It includes:

- a FastAPI backend
- a browser-based control panel for script ingestion and generation
- a model catalog with local install metadata
- a real local video rendering pipeline using FFmpeg + PIL fallback
- optional support for locally installed model runtimes such as AnimateDiff, SVD-XT, CogVideoX, and Wan 2.1

Important: this project does not auto-download giant licensed model weights from the internet. Real video models require local GPU hardware, installed weights, and sometimes authentication or manual setup. This app is designed to work with local GPU runtimes if they are already installed, and it includes a fully local FFmpeg/Pillow fallback for immediate functionality on machines without those models.

## Quick start

1. Install Python 3.10+
2. Create a virtual environment if desired
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the backend:

```bash
python app.py
```

5. Open the app in a browser:

```text
http://localhost:8000/
```

## Local model support

The app includes a model catalog in `models.json` with entries such as:

- AnimateDiff (Local Core)
- Stable Video Diffusion (SVD-XT)
- CogVideoX
- Wan 2.1 (manual local install required)
- Custom Pipeline (FFmpeg Script)

These entries are metadata and integration hooks. To use them for real generation, install the required model weights locally and set the correct paths in the config or model runner environment.

## Directories

- `app.py` – FastAPI backend and local render engine
- `models.json` – model catalog and local installation metadata
- `static/` – browser UI assets
- `generated/` – output video files

## Notes

- The app is designed for local-only use.
- Real inference is only available when model weights are installed locally.
- The built-in fallback generates a procedural local MP4 for a working demo without any external API or login.
