from fastapi import APIRouter, HTTPException
from app.services.job_manager import job_manager
from app.models.job import JobStatusResponse

router = APIRouter(prefix="/api/v1")

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
