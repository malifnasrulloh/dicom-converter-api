import time
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import health, jobs, convert, send_to_orthanc, proxy

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("main")

app = FastAPI(
    title="DICOM Converter API (Python)",
    description="Production-grade DICOM conversion & Orthanc PACS gateway powered by FastAPI, pydicom, and pynetdicom",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Request execution timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handler for structured JSON errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": str(exc)
        }
    )

# Include routers
app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(convert.router)
app.include_router(send_to_orthanc.router)
app.include_router(proxy.router)

@app.on_event("startup")
async def startup_event():
    logger.info("==================================================")
    logger.info(" DICOM Converter API (Python) - Production Ready ")
    logger.info("==================================================")
    logger.info(f" Server Port: {settings.port}")
    logger.info(f" Orthanc Configured: {settings.is_orthanc_configured}")
    if settings.is_orthanc_configured:
        logger.info(f" Orthanc Base URL: {settings.orthanc_base_url}")
    dcmtk_tools = settings.check_dcmtk_tools()
    for tool, found in dcmtk_tools.items():
        logger.info(f" DCMTK Tool '{tool}': {'READY' if found else 'MISSING'}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
