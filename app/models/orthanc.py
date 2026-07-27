from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class OrthancUploadResponse(BaseModel):
    ID: str
    ParentPatient: str
    ParentSeries: str
    ParentStudy: str
    Path: str
    Status: str

class OrthancModifyRequest(BaseModel):
    Replace: Optional[Dict[str, Any]] = None
    Remove: Optional[List[str]] = None
    Keep: Optional[List[str]] = None
    KeepSource: bool = True
    KeepLabels: bool = True
    Force: bool = True
    Synchronous: bool = True

class SendToOrthancFromURLsRequest(BaseModel):
    filetype: str
    urls: List[str]
    parameters: Optional[Dict[str, Any]] = None
    orthanc_modify: Optional[OrthancModifyRequest] = None

class FindStudyByAccessionRequest(BaseModel):
    accession_number: str = Field(..., alias="accession_number")

class FindPatientStudiesRequest(BaseModel):
    patient_id: str

class SendToModalityRequest(BaseModel):
    modality_ae: Optional[str] = None
