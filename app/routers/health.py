from fastapi import APIRouter
from app.config import settings
from app.services.job_manager import job_manager

router = APIRouter()

@router.get("/health")
@router.get("/api/v1/health")
async def health_check():
    dcmtk_status = settings.check_dcmtk_tools()
    all_tools_ready = all(dcmtk_status.values())
    
    return {
        "status": "ok" if all_tools_ready else "degraded",
        "orthanc_configured": settings.is_orthanc_configured,
        "orthanc_base_url": settings.orthanc_base_url if settings.is_orthanc_configured else None,
        "dcmtk_tools": dcmtk_status,
        "job_stats": job_manager.get_stats()
    }
