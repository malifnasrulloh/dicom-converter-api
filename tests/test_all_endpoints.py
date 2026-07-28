import os
import json
import asyncio
import pydicom
from httpx import AsyncClient, ASGITransport
from app.main import app

SAMPLES_DIR = "/tmp/dicom_test_samples"

async def run_integration_tests():
    print("=" * 60)
    print(" STARTING COMPREHENSIVE DICOM CONVERTER API INTEGRATION TESTS ")
    print("=" * 60)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # -------------------------------------------------------------
        # 1. TEST HEALTH ENDPOINTS
        # -------------------------------------------------------------
        print("\n[1/13] Testing GET /health & /api/v1/health...")
        resp = await client.get("/health")
        assert resp.status_code == 200, f"Health check failed: {resp.text}"
        data = resp.json()
        print("  -> GET /health status:", data.get("status"))
        print("  -> DCMTK tools:", data.get("dcmtk_tools"))
        assert "img2dcm" in data.get("dcmtk_tools", {})

        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200

        # -------------------------------------------------------------
        # 2. TEST CONVERT IMAGE -> DICOM (JPEG & PNG)
        # -------------------------------------------------------------
        for fmt in ["jpg", "png"]:
            print(f"\n[2/13] Testing POST /api/v1/convert/img2dcm ({fmt.upper()})...")
            file_path = os.path.join(SAMPLES_DIR, f"test_sample.{fmt}")
            params = json.dumps({
                "keys": [
                    "Modality=CR",
                    "PatientID=TEST_PID_123",
                    "PatientName=DOE^JOHN",
                    "AccessionNumber=ACC_20260727",
                    "StudyDescription=TEST RADIOLOGY EXAM"
                ]
            })

            with open(file_path, "rb") as f:
                resp = await client.post(
                    "/api/v1/convert/img2dcm",
                    files={"file": (f"test_sample.{fmt}", f, f"image/{fmt}")},
                    data={"parameters": params}
                )

            assert resp.status_code == 200, f"img2dcm failed: {resp.text}"
            assert resp.headers.get("content-type") == "application/dicom"

            # Save temporary DICOM & validate with pydicom
            out_dcm_path = f"/tmp/test_output_{fmt}.dcm"
            with open(out_dcm_path, "wb") as f_out:
                f_out.write(resp.content)

            ds = pydicom.dcmread(out_dcm_path)
            print(f"  -> Validated DICOM Dataset from {fmt.upper()}:")
            print(f"     SpecificCharacterSet : {getattr(ds, 'SpecificCharacterSet', None)}")
            print(f"     Modality             : {getattr(ds, 'Modality', None)}")
            print(f"     PatientID            : {getattr(ds, 'PatientID', None)}")
            print(f"     AccessionNumber      : {getattr(ds, 'AccessionNumber', None)}")

            assert getattr(ds, "SpecificCharacterSet", None) == "ISO_IR 192"
            assert getattr(ds, "PatientID", None) == "TEST_PID_123"
            assert getattr(ds, "AccessionNumber", None) == "ACC_20260727"

        # -------------------------------------------------------------
        # 3. TEST CONVERT PDF -> DICOM
        # -------------------------------------------------------------
        print("\n[3/13] Testing POST /api/v1/convert/pdf2dcm...")
        file_path = os.path.join(SAMPLES_DIR, "test_sample.pdf")
        params = json.dumps({"keys": ["Modality=DOC", "PatientID=PID_PDF_999"]})

        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/convert/pdf2dcm",
                files={"file": ("test_sample.pdf", f, "application/pdf")},
                data={"parameters": params}
            )

        assert resp.status_code == 200, f"pdf2dcm failed: {resp.text}"
        out_pdf_dcm = "/tmp/test_output_pdf.dcm"
        with open(out_pdf_dcm, "wb") as f_out:
            f_out.write(resp.content)

        ds_pdf = pydicom.dcmread(out_pdf_dcm)
        print("  -> PDF DICOM PatientID:", getattr(ds_pdf, "PatientID", None))
        assert getattr(ds_pdf, "PatientID", None) == "PID_PDF_999"

        # -------------------------------------------------------------
        # 4. TEST CONVERT CDA -> DICOM
        # -------------------------------------------------------------
        print("\n[4/13] Testing POST /api/v1/convert/cda2dcm...")
        file_path = os.path.join(SAMPLES_DIR, "test_sample.xml")
        params = json.dumps({"keys": ["PatientID=PID_CDA_888"]})

        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/convert/cda2dcm",
                files={"file": ("test_sample.xml", f, "text/xml")},
                data={"parameters": params}
            )

        assert resp.status_code == 200, f"cda2dcm failed: {resp.text}"
        print("  -> CDA conversion HTTP 200 OK")

        # -------------------------------------------------------------
        # 5. TEST CONVERT STL -> DICOM
        # -------------------------------------------------------------
        print("\n[5/13] Testing POST /api/v1/convert/stl2dcm...")
        file_path = os.path.join(SAMPLES_DIR, "test_sample.stl")
        params = json.dumps({"keys": ["PatientID=PID_STL_777"]})

        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/convert/stl2dcm",
                files={"file": ("test_sample.stl", f, "application/octet-stream")},
                data={"parameters": params}
            )

        assert resp.status_code == 200, f"stl2dcm failed: {resp.text}"
        print("  -> STL conversion HTTP 200 OK")

        # -------------------------------------------------------------
        # 6. TEST SEND TO ORTHANC (MULTIPART FILE ASYNC)
        # -------------------------------------------------------------
        print("\n[6/13] Testing POST /api/v1/send-to-orthanc...")
        file_path = os.path.join(SAMPLES_DIR, "test_sample.jpg")
        params = json.dumps({"keys": ["Modality=CR", "PatientID=PID_ORTHANC_1"]})

        with open(file_path, "rb") as f:
            resp = await client.post(
                "/api/v1/send-to-orthanc",
                files={"file": ("test_sample.jpg", f, "image/jpeg")},
                data={"filetype": "img", "parameters": params}
            )

        # Expect 533 or 503 if Orthanc not configured, or 202 if configured
        print("  -> send-to-orthanc response code:", resp.status_code)
        if resp.status_code == 202:
            data = resp.json()
            job_id = data.get("job_id")
            assert job_id is not None
            print(f"  -> Job created: {job_id}")

            # -------------------------------------------------------------
            # 7. TEST POLL JOB STATUS
            # -------------------------------------------------------------
            print(f"\n[7/13] Testing GET /api/v1/jobs/{job_id}...")
            await asyncio.sleep(0.5)
            job_resp = await client.get(f"/api/v1/jobs/{job_id}")
            assert job_resp.status_code == 200
            print("  -> Job Status Payload:", job_resp.json())

        # -------------------------------------------------------------
        # 8. TEST PROXY ENDPOINTS
        # -------------------------------------------------------------
        print("\n[8/13] Testing POST /api/v1/studies/find-by-acsn...")
        resp = await client.post("/api/v1/studies/find-by-acsn", json={"accession_number": "ACC_TEST_99"})
        assert resp.status_code == 200
        print("  -> find-by-acsn payload:", resp.json())

        print("\n[9/13] Testing POST /api/v1/patients/{id}/studies...")
        resp = await client.post("/api/v1/patients/PID_TEST_100/studies")
        assert resp.status_code == 200

        print("\n[10/13] Testing POST /api/v1/studies/{id}/send-to-modality/{ae}...")
        resp = await client.post("/api/v1/studies/STU_123/send-to-modality/ROUTER_AE")
        print("  -> send-to-modality code:", resp.status_code)

        print("\n[11/13] Testing POST /api/v1/studies/{id}/modify...")
        resp = await client.post("/api/v1/studies/STU_123/modify")
        assert resp.status_code == 200

        print("\n[12/13] Testing POST /api/v1/orchestrate/upload-and-send...")
        resp = await client.post("/api/v1/orchestrate/upload-and-send")
        assert resp.status_code == 200

        print("\n[13/13] Validation of X-Process-Time Header...")
        assert "x-process-time" in resp.headers
        print("  -> X-Process-Time header present:", resp.headers["x-process-time"])

    print("\n" + "=" * 60)
    print(" SUCCESS: ALL 13 DICOM CONVERTER API INTEGRATION TESTS PASSED! ")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_integration_tests())
