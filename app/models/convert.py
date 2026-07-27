from typing import List, Optional
from pydantic import BaseModel, Field

class Img2DcmRequest(BaseModel):
    input_format: Optional[str] = Field("JPEG", alias="inputFormat")
    output_sop_class: Optional[str] = Field("sec-capture", alias="outputSopClass")
    keys: Optional[List[str]] = Field(default_factory=list)

class Pdf2DcmRequest(BaseModel):
    document_title: Optional[str] = Field(None, alias="documentTitle")
    keys: Optional[List[str]] = Field(default_factory=list)

class Cda2DcmRequest(BaseModel):
    keys: Optional[List[str]] = Field(default_factory=list)

class Stl2DcmRequest(BaseModel):
    keys: Optional[List[str]] = Field(default_factory=list)
