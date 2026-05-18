"""FastAPI service exposing the recognition pipeline."""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from ..pipeline_runner import process_video
from .. import config_loader

log = logging.getLogger("api")


# ----------------------------------------------------------------------
def build_app() -> FastAPI:
    cfg = config_loader.load()

    uploads = Path(cfg.runtime.uploads_dir)
    outputs = Path(cfg.runtime.outputs_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)

    jobs: dict[str, dict[str, Any]] = {}

    app = FastAPI(title="Price-Tag Recognition Service", version="0.3.0")

    # ------------------------------------------------------------------
    @app.post("/jobs/submit")
    async def submit(
        background_tasks: BackgroundTasks,
        video: UploadFile = File(...),
        rotation_deg: int = Form(90),
        frames_per_second: float = Form(1.5),
    ) -> dict:
        job_id = uuid.uuid4().hex
        suffix = Path(video.filename or "input.mp4").suffix or ".mp4"
        local_video = uploads / f"{job_id}{suffix}"

        with open(local_video, "wb") as fh:
            shutil.copyfileobj(video.file, fh)

        result_csv = outputs / f"{job_id}.csv"
        jobs[job_id] = {
            "status": "queued",
            "csv": str(result_csv),
            "video": str(local_video),
            "filename": video.filename or local_video.name,
            "rotation_deg": int(rotation_deg),
            "fps": float(frames_per_second),
        }

        background_tasks.add_task(_run_job, jobs, job_id, cfg)
        return {"job_id": job_id, "status": "queued"}

    # ------------------------------------------------------------------
    @app.get("/jobs/{job_id}")
    async def get_job(job_id: str) -> dict:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="job_not_found")
        info = jobs[job_id]
        return {"job_id": job_id, "status": info["status"], "error": info.get("error")}

    # ------------------------------------------------------------------
    @app.get("/jobs/{job_id}/result")
    async def download(job_id: str) -> FileResponse:
        if job_id not in jobs:
            raise HTTPException(status_code=404, detail="job_not_found")
        info = jobs[job_id]
        if info["status"] != "done":
            return JSONResponse(
                status_code=409,
                content={"job_id": job_id, "status": info["status"]},
            )
        csv_path = info["csv"]
        if not Path(csv_path).exists():
            raise HTTPException(status_code=500, detail="csv_missing")
        return FileResponse(
            csv_path,
            filename=f"pricetags_{job_id[:8]}.csv",
            media_type="text/csv",
        )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "jobs": len(jobs)}

    return app


# ----------------------------------------------------------------------
def _run_job(jobs: dict, job_id: str, cfg) -> None:
    record = jobs[job_id]
    record["status"] = "running"
    try:
        process_video(
            video_path=record["video"],
            output_csv=record["csv"],
            cfg=cfg,
            source_filename=record["filename"],
            rotation_deg=record["rotation_deg"],
            frames_per_second=record["fps"],
        )
        record["status"] = "done"
    except Exception as err:  # noqa: BLE001
        log.exception("Job %s failed", job_id)
        record["status"] = "failed"
        record["error"] = str(err)
