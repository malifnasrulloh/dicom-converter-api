import httpx
import logging
from typing import Optional, Dict, Any, List
from app.config import settings

logger = logging.getLogger("orthanc-client")

class OrthancClient:
    def _get_client(self) -> httpx.AsyncClient:
        auth = None
        if settings.orthanc_user and settings.orthanc_pass:
            auth = (settings.orthanc_user, settings.orthanc_pass)
        return httpx.AsyncClient(
            base_url=settings.orthanc_base_url,
            auth=auth,
            timeout=120.0
        )

    async def upload_instance(self, dcm_path: str) -> Dict[str, Any]:
        if not settings.is_orthanc_configured:
            raise RuntimeError("Orthanc is not configured")

        with open(dcm_path, "rb") as f:
            content = f.read()

        async with self._get_client() as client:
            resp = await client.post("/instances", content=content, headers={"Content-Type": "application/dicom"})
            resp.raise_for_status()
            return resp.json()

    async def find_study_by_accession(self, accession_number: str, retries: int = 1, delay_sec: float = 0.3) -> Optional[str]:
        if not settings.is_orthanc_configured or not accession_number:
            return None

        clean_acsn = accession_number.strip()
        async with self._get_client() as client:
            for attempt in range(1, retries + 1):
                try:
                    resp = await client.post("/tools/find", json={
                        "Level": "Study",
                        "Query": {"AccessionNumber": clean_acsn}
                    })
                    if resp.status_code == 200:
                        studies = resp.json()
                        if studies and len(studies) > 0:
                            study_id = studies[0]
                            logger.info(f"find_study_by_accession: Found study_id={study_id} for ACSN={clean_acsn} (attempt {attempt}/{retries})")
                            return study_id
                except Exception as e:
                    logger.warning(f"find_study_by_accession attempt {attempt} failed: {e}")

                if attempt < retries:
                    import asyncio
                    await asyncio.sleep(delay_sec)
            return None

    async def find_patient_studies(self, patient_id: str) -> List[Dict[str, Any]]:
        if not settings.is_orthanc_configured:
            return []

        async with self._get_client() as client:
            resp = await client.post("/tools/find", json={
                "Level": "Study",
                "Query": {"PatientID": patient_id}
            })
            if resp.status_code == 200:
                study_ids = resp.json()
                results = []
                for s_id in study_ids:
                    s_resp = await client.get(f"/studies/{s_id}")
                    if s_resp.status_code == 200:
                        results.append(s_resp.json())
                return results
            return []

    async def get_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        if not settings.is_orthanc_configured or not instance_id:
            return None
        async with self._get_client() as client:
            resp = await client.get(f"/instances/{instance_id}")
            if resp.status_code == 200:
                return resp.json()
            return None

    async def find_study_by_sop_instance_uid(self, sop_instance_uid: str, retries: int = 10, delay_sec: float = 0.3) -> Optional[str]:
        if not settings.is_orthanc_configured or not sop_instance_uid:
            return None

        clean_uid = sop_instance_uid.strip()
        async with self._get_client() as client:
            for attempt in range(1, retries + 1):
                try:
                    resp = await client.post("/tools/find", json={
                        "Level": "Instance",
                        "Query": {"SOPInstanceUID": clean_uid}
                    })
                    if resp.status_code == 200:
                        instances = resp.json()
                        if instances and len(instances) > 0:
                            inst_id = instances[0]
                            inst_resp = await client.get(f"/instances/{inst_id}")
                            if inst_resp.status_code == 200:
                                study_id = inst_resp.json().get("ParentStudy")
                                if study_id:
                                    logger.info(f"find_study_by_sop_instance_uid: Found study_id={study_id} for SOPInstanceUID={clean_uid} (attempt {attempt}/{retries})")
                                    return study_id
                except Exception as e:
                    logger.warning(f"find_study_by_sop_instance_uid attempt {attempt} failed: {e}")

                if attempt < retries:
                    import asyncio
                    await asyncio.sleep(delay_sec)
            return None

    async def send_study_to_modality(self, study_id: str, modality_ae: str) -> bool:
        if not settings.is_orthanc_configured:
            return False

        async with self._get_client() as client:
            resp = await client.post(f"/modalities/{modality_ae}/store", content=study_id)
            return resp.status_code == 200

orthanc_client = OrthancClient()
