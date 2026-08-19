import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from app.services.orthanc_client import orthanc_client
from app.models.orthanc import (
    FindStudyByAccessionRequest,
    FindPatientStudiesRequest,
    SendToModalityRequest,
    OrthancModifyRequest
)

logger = logging.getLogger("proxy-router")
router = APIRouter(prefix="/api/v1", tags=["proxy"])

@router.post("/studies/{study_id}/modify")
async def handle_modify_study(study_id: str, req: Optional[OrthancModifyRequest] = None):
    # Proxy or stub response for modify
    return {"status": "success", "study_id": study_id}

@router.post("/studies/find-by-acsn")
async def handle_find_study_by_accession(req: FindStudyByAccessionRequest):
    study_id = await orthanc_client.find_study_by_accession(req.accession_number, retries=1, delay_sec=0.0)
    if not study_id:
        return {"status": "not_found", "study_id": ""}
    return {"status": "success", "study_id": study_id}

@router.post("/patients/{patient_id}/studies")
async def handle_find_patient_studies(patient_id: str):
    studies = await orthanc_client.find_patient_studies(patient_id)
    return {"status": "success", "patient_id": patient_id, "studies": studies}

@router.post("/studies/{study_id}/send-to-modality/{modality_ae}")
async def handle_send_study_to_modality(study_id: str, modality_ae: str):
    success = await orthanc_client.send_study_to_modality(study_id, modality_ae)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to send study {study_id} to modality {modality_ae}")
    return {"status": "success", "study_id": study_id, "modality_ae": modality_ae}

@router.post("/orchestrate/upload-and-send")
async def handle_orchestrate_upload_and_send():
    return {"status": "success", "message": "Orchestrate endpoint ready"}
