import os
import json
import shutil
import tempfile
import logging
import httpx
from typing import Optional, List
from urllib.parse import urlparse
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException, status
from app.config import settings
from app.services.job_manager import job_manager
from app.services.orthanc_client import orthanc_client
from app.services.conversion import (
    convert_img, convert_pdf, convert_cda, convert_stl, sanitize_filename
)
from app.services.dicom_sender import send_dicom_cstore
from app.models.job import SendToOrthancResponse
from app.models.orthanc import SendToOrthancFromURLsRequest

logger = logging.getLogger("send-to-orthanc")
router = APIRouter(prefix="/api/v1", tags=["orthanc"])

def parse_keys_from_params_str(params_str: Optional[str]) -> List[str]:
    if not params_str:
        return []
    try:
        data = json.loads(params_str)
        if isinstance(data, dict):
            return data.get("keys", [])
    except Exception:
        pass
    return []

def extract_accession_from_keys(keys: Optional[List[str]]) -> str:
    if not keys:
        return ""
    for k in keys:
        if k and "=" in k:
            tag, val = k.split("=", 1)
            clean_tag = tag.strip().lower()
            if clean_tag in ["accessionnumber", "0008,0050", "(0008,0050)"]:
                return val.strip()
    return ""

async def process_file_send_job(
    job_id: str,
    file_type: str,
    temp_dir: str,
    input_file_path: str,
    filename: str,
    keys: List[str]
):
    try:
        job_manager.update_job(job_id, "processing", progress=20)
        output_file_path = os.path.join(temp_dir, "output.dcm")

        # Step 1: Convert to DICOM (all tags embedded during conversion)
        if file_type == "img":
            await convert_img(input_file_path, output_file_path, temp_dir, filename, keys)
        elif file_type == "pdf":
            await convert_pdf(input_file_path, output_file_path, keys)
        elif file_type == "cda":
            await convert_cda(input_file_path, output_file_path, keys)
        elif file_type == "stl":
            await convert_stl(input_file_path, output_file_path, keys)
        else:
            raise ValueError(f"Unsupported filetype: {file_type}")

        job_manager.update_job(job_id, "processing", progress=60)

        # Step 2: Upload to Orthanc (via pynetdicom C-STORE or HTTP REST API)
        resolved_study_id = ""
        if settings.use_cstore_upload:
            host = urlparse(settings.orthanc_url).hostname or "orthanc"
            success = send_dicom_cstore(
                output_file_path,
                remote_host=host,
                remote_port=settings.orthanc_dicom_port,
                remote_aet=settings.orthanc_aet
            )
            if not success:
                raise RuntimeError("pynetdicom C-STORE transfer failed")
            upload_resp = {"Status": "Success", "Protocol": "DICOM C-STORE", "TargetAET": settings.orthanc_aet}
        else:
            upload_resp = await orthanc_client.upload_instance(output_file_path)
            if isinstance(upload_resp, dict):
                resolved_study_id = upload_resp.get("ParentStudy", "")

        # Step 3: Verify Orthanc indexing & resolve Study ID
        acsn = extract_accession_from_keys(keys)
        if not resolved_study_id and acsn:
            # Poll Orthanc /tools/find with retries to guarantee SQLite commit
            resolved_study_id = await orthanc_client.find_study_by_accession(acsn, retries=10, delay_sec=0.4) or ""

        job_manager.update_job(
            job_id,
            "completed",
            progress=100,
            result={
                "upload": upload_resp,
                "study_id": resolved_study_id,
                "accession_number": acsn
            }
        )
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        job_manager.update_job(job_id, "failed", error=str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

async def process_urls_send_job(
    job_id: str,
    file_type: str,
    urls: List[str],
    keys: List[str]
):
    temp_dir = tempfile.mkdtemp(prefix="send_urls_")
    try:
        job_manager.update_job(job_id, "processing", progress=10)
        last_upload_resp = None
        resolved_study_id = ""

        async with httpx.AsyncClient(timeout=60.0) as client:
            for idx, url_str in enumerate(urls):
                parsed = urlparse(url_str)
                base_name = os.path.basename(parsed.path) or f"image_{idx}.jpg"
                clean_name = sanitize_filename(base_name)
                input_file_path = os.path.join(temp_dir, f"{idx}_{clean_name}")

                resp = await client.get(url_str)
                resp.raise_for_status()

                with open(input_file_path, "wb") as f:
                    f.write(resp.content)

                output_file_path = os.path.join(temp_dir, f"output_{idx}.dcm")
                if file_type == "img":
                    await convert_img(input_file_path, output_file_path, temp_dir, clean_name, keys)
                elif file_type == "pdf":
                    await convert_pdf(input_file_path, output_file_path, keys)
                elif file_type == "cda":
                    await convert_cda(input_file_path, output_file_path, keys)
                elif file_type == "stl":
                    await convert_stl(input_file_path, output_file_path, keys)

                if settings.use_cstore_upload:
                    host = urlparse(settings.orthanc_url).hostname or "orthanc"
                    success = send_dicom_cstore(
                        output_file_path,
                        remote_host=host,
                        remote_port=settings.orthanc_dicom_port,
                        remote_aet=settings.orthanc_aet
                    )
                    if not success:
                        raise RuntimeError("pynetdicom C-STORE transfer failed")
                    last_upload_resp = {"Status": "Success", "Protocol": "DICOM C-STORE", "TargetAET": settings.orthanc_aet}
                else:
                    last_upload_resp = await orthanc_client.upload_instance(output_file_path)
                    if isinstance(last_upload_resp, dict) and "ParentStudy" in last_upload_resp:
                        resolved_study_id = last_upload_resp.get("ParentStudy", "")

        # Verify Orthanc indexing & resolve Study ID
        acsn = extract_accession_from_keys(keys)
        if not resolved_study_id and acsn:
            # Poll Orthanc /tools/find with retries to guarantee SQLite commit
            resolved_study_id = await orthanc_client.find_study_by_accession(acsn, retries=10, delay_sec=0.4) or ""

        if last_upload_resp:
            job_manager.update_job(
                job_id,
                "completed",
                progress=100,
                result={
                    "upload": last_upload_resp,
                    "study_id": resolved_study_id,
                    "accession_number": acsn
                }
            )
        else:
            job_manager.update_job(job_id, "failed", error="No instances uploaded")
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        job_manager.update_job(job_id, "failed", error=str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@router.post("/send-to-orthanc", response_model=SendToOrthancResponse, status_code=status.HTTP_202_ACCEPTED)
async def handle_send_to_orthanc(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    filetype: str = Form(...),
    parameters: Optional[str] = Form(None),
    orthanc_modify: Optional[str] = Form(None)
):
    if not settings.is_orthanc_configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Orthanc is not configured")

    ft = filetype.strip().lower()
    if ft not in ["img", "pdf", "cda", "stl"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filetype. Must be one of: img, pdf, cda, stl")

    keys = parse_keys_from_params_str(parameters)
    temp_dir = tempfile.mkdtemp(prefix="send_to_orthanc_")
    clean_filename = sanitize_filename(file.filename or "input.bin")
    input_file_path = os.path.join(temp_dir, clean_filename)

    with open(input_file_path, "wb") as f:
        f.write(await file.read())

    job_id = job_manager.create_job()
    background_tasks.add_task(
        process_file_send_job,
        job_id,
        ft,
        temp_dir,
        input_file_path,
        clean_filename,
        keys
    )

    return SendToOrthancResponse(status="success", job_id=job_id)

@router.post("/send-to-orthanc-from-urls", response_model=SendToOrthancResponse, status_code=status.HTTP_202_ACCEPTED)
async def handle_send_to_orthanc_from_urls(
    req: SendToOrthancFromURLsRequest,
    background_tasks: BackgroundTasks
):
    if not settings.is_orthanc_configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Orthanc is not configured")

    ft = req.filetype.strip().lower()
    if ft not in ["img", "pdf", "cda", "stl"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filetype. Must be one of: img, pdf, cda, stl")

    if not req.urls:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing urls parameter")

    keys = []
    if req.parameters and isinstance(req.parameters, dict):
        keys = req.parameters.get("keys", [])

    job_id = job_manager.create_job()
    background_tasks.add_task(process_urls_send_job, job_id, ft, req.urls, keys)

    return SendToOrthancResponse(status="success", job_id=job_id)
