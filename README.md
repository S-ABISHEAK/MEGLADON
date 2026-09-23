# MEGALODON — Intelligent Single-Pass Drone 3D Reconstruction System

A working prototype for SIH26158: single-pass 4K drone video → metric,
georeferenced 3D model, with real-time pipeline visibility and an
interactive browser-based 3D viewer.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for what's real vs. DEMO
MODE in the current environment, and [`docs/PIPELINE.md`](docs/PIPELINE.md)
for the full 10-stage data-flow diagram.

## Quick start (Docker)

```bash
cp .env.example backend/.env   # optional, docker-compose sets its own env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs

## Quick start (local, no Docker)

Requires: Python 3.11+, Node 20+, `ffmpeg` on PATH, Redis (optional — the
backend falls back to an in-process thread queue if Redis is unreachable).

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Worker (separate terminal, only needed if Redis is running)
cd backend
python -m app.workers.worker

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, upload an MP4/MOV/AVI/MKV, optionally attach a
GPS/IMU/RTK sensor file (CSV/JSON), click **START RECONSTRUCTION**, and
watch the 10 pipeline stages update live over WebSocket.

## Running tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Project structure

```
megalodon/
├── frontend/        React + Vite + TypeScript + Tailwind + React Three Fiber
├── backend/
│   └── app/
│       ├── api/         REST endpoints + WebSocket
│       ├── models/      SQLAlchemy models
│       ├── schemas/      Pydantic schemas
│       ├── pipeline/     the 10 real pipeline stages
│       ├── algorithms/  adapter interfaces (spec section 27)
│       ├── workers/      RQ queue + worker entrypoint
│       └── services/    stage tracking, event bus
├── models/          downloaded model weights (gitignored)
├── jobs/            per-job artifact directories (gitignored)
├── docker/          Dockerfiles + nginx config
├── docs/            ARCHITECTURE.md, PIPELINE.md
└── docker-compose.yml
```

## What's real vs. DEMO MODE

FFmpeg, OpenCV, ORB-based visual odometry, YOLOv8, Open3D fusion/TSDF/Poisson,
scipy-based bundle adjustment, and PROJ/pyproj georeferencing all execute
for real in this environment. SAM2, Depth Anything V2, VGGT-O and Speed3R
run as explicitly labeled DEMO ARTIFACTS because their checkpoints/packages
are unreachable in this sandbox (network blocked to huggingface.co/github.com,
no GPU) — see `docs/ARCHITECTURE.md` for the full table and the adapter
architecture that makes swapping in the real models a drop-in change with no
API surface changes.
