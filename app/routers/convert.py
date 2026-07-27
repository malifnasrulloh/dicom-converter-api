import os
import json
import tempfile
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from app.services.conversion import convert_img, convert_pdf, convert_cda, convert_stl
from app.models.convert import Img2DcmRequest, Pdf2DcmRequest, Cda2DcmRequest, Stl2DcmRequest

router = APIRouter(prefix="/api/v1/convert", tags=["convert"])

@router.post("/img2dcm")
async def handle_img2dcm(file: UploadFile = File(...), parameters: Optional[str] = Form(None)):
    keys = []
    if parameters:
        try:
            req_data = Img2DcmRequest.model_validate_json(parameters)
            keys = req_data.keys
        except Exception:
            pass

    temp_dir = tempfile.mkdtemp(prefix="img2dcm_")
    input_path = os.path.join(temp_dir, file.filename or "input.jpg")
    output_path = os.path.join(temp_dir, "output.dcm")

    try:
        with open(input_path, "wb") as f:
            f.write(await file.read())

        await convert_img(input_path, output_path, temp_dir, file.filename or "input.jpg", keys)
        return FileResponse(output_path, media_type="application/dicom", filename="output.dcm")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pdf2dcm")
async def handle_pdf2dcm(file: UploadFile = File(...), parameters: Optional[str] = Form(None)):
    keys = []
    if parameters:
        try:
            req_data = Pdf2DcmRequest.model_validate_json(parameters)
            keys = req_data.keys
        except Exception:
            pass

    temp_dir = tempfile.mkdtemp(prefix="pdf2dcm_")
    input_path = os.path.join(temp_dir, file.filename or "input.pdf")
    output_path = os.path.join(temp_dir, "output.dcm")

    try:
        with open(input_path, "wb") as f:
            f.write(await file.read())

        await convert_pdf(input_path, output_path, keys)
        return FileResponse(output_path, media_type="application/dicom", filename="output.dcm")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cda2dcm")
async def handle_cda2dcm(file: UploadFile = File(...), parameters: Optional[str] = Form(None)):
    keys = []
    if parameters:
        try:
            req_data = Cda2DcmRequest.model_validate_json(parameters)
            keys = req_data.keys
        except Exception:
            pass

    temp_dir = tempfile.mkdtemp(prefix="cda2dcm_")
    input_path = os.path.join(temp_dir, file.filename or "input.xml")
    output_path = os.path.join(temp_dir, "output.dcm")

    try:
        with open(input_path, "wb") as f:
            f.write(await file.read())

        await convert_cda(input_path, output_path, keys)
        return FileResponse(output_path, media_type="application/dicom", filename="output.dcm")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stl2dcm")
async def handle_stl2dcm(file: UploadFile = File(...), parameters: Optional[str] = Form(None)):
    keys = []
    if parameters:
        try:
            req_data = Stl2DcmRequest.model_validate_json(parameters)
            keys = req_data.keys
        except Exception:
            pass

    temp_dir = tempfile.mkdtemp(prefix="stl2dcm_")
    input_path = os.path.join(temp_dir, file.filename or "input.stl")
    output_path = os.path.join(temp_dir, "output.dcm")

    try:
        with open(input_path, "wb") as f:
            f.write(await file.read())

        await convert_stl(input_path, output_path, keys)
        return FileResponse(output_path, media_type="application/dicom", filename="output.dcm")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
