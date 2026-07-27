import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from threading import Lock

logger = logging.getLogger("job-manager")

class JobManager:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._cleanup_expired_jobs_nolock()
            self._jobs[job_id] = {
                "id": job_id,
                "status": "pending",
                "progress": 0,
                "created_at": now,
                "updated_at": now,
                "result": None,
                "error": None,
            }
        logger.debug(f"Job created: {job_id}")
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                return dict(job)
            return None

    def update_job(
        self,
        job_id: str,
        status: str,
        progress: int = 0,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ):
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = status
                self._jobs[job_id]["progress"] = progress
                self._jobs[job_id]["updated_at"] = now
                if result is not None:
                    self._jobs[job_id]["result"] = result
                if error is not None:
                    self._jobs[job_id]["error"] = error
        logger.debug(f"Job updated: {job_id} -> {status} ({progress}%)")

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._jobs)
            status_counts = {}
            for j in self._jobs.values():
                st = j["status"]
                status_counts[st] = status_counts.get(st, 0) + 1
            return {"total_jobs": total, "status_breakdown": status_counts}

    def _cleanup_expired_jobs_nolock(self, max_age_hours: int = 24):
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        expired_ids = []
        for j_id, j in self._jobs.items():
            try:
                created_dt = datetime.fromisoformat(j["created_at"])
                if created_dt < cutoff:
                    expired_ids.append(j_id)
            except Exception:
                pass
        for j_id in expired_ids:
            del self._jobs[j_id]

job_manager = JobManager()
