FROM python:3.12-slim

LABEL maintainer="malifnasrulloh"
LABEL description="DICOM Converter API (Python + pydicom + pynetdicom + DCMTK)"

# Set Python runtime flags (unbuffered output & disable pyc writing)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies (DCMTK binaries, native Python packages, and C libraries)
RUN apt-get update && \
    apt-get install -y \
        dcmtk \
        libgl1 \
        libglib2.0-0 \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install pynetdicom (not present in standard apt repos)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ app/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
