import os
import shutil
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    orthanc_url: str = os.getenv("ORTHANC_URL", "")
    orthanc_port: str = os.getenv("ORTHANC_PORT", "8042")
    orthanc_user: str = os.getenv("ORTHANC_USER", "")
    orthanc_pass: str = os.getenv("ORTHANC_PASS", "")
    
    port: int = int(os.getenv("PORT", "8080"))
    host: str = os.getenv("HOST", "0.0.0.0")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    orthanc_dicom_port: int = int(os.getenv("ORTHANC_DICOM_PORT", "4242"))
    orthanc_aet: str = os.getenv("ORTHANC_AET", "ORTHANC")
    use_cstore_upload: bool = os.getenv("USE_CSTORE_UPLOAD", "false").lower() in ("true", "1", "yes")
    
    max_image_upload_size: int = 50 * 1024 * 1024  # 50 MB
    max_pdf_upload_size: int = 100 * 1024 * 1024   # 100 MB
    max_cda_upload_size: int = 20 * 1024 * 1024    # 20 MB
    max_stl_upload_size: int = 100 * 1024 * 1024   # 100 MB
    
    job_ttl_hours: int = int(os.getenv("JOB_TTL_HOURS", "24"))

    @property
    def orthanc_base_url(self) -> str:
        if not self.orthanc_url:
            return ""
        url = self.orthanc_url.rstrip("/")
        if self.orthanc_port and not url.endswith(f":{self.orthanc_port}"):
            return f"{url}:{self.orthanc_port}"
        return url

    @property
    def is_orthanc_configured(self) -> bool:
        return bool(self.orthanc_url)

    def check_dcmtk_tools(self) -> dict[str, bool]:
        tools = ["img2dcm", "pdf2dcm", "cda2dcm", "stl2dcm"]
        return {tool: bool(shutil.which(tool)) for tool in tools}

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
