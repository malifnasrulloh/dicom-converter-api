import os
import re
import asyncio
import logging
from typing import List, Optional
from PIL import Image
import pydicom

logger = logging.getLogger("conversion-service")

def sanitize_filename(filename: str) -> str:
    """Sanitize user-uploaded filename to prevent directory traversal and null byte injections."""
    if not filename:
        return "unnamed_file"
    # Remove path components
    clean = os.path.basename(filename)
    # Remove null bytes and control chars
    clean = re.sub(r'[\x00-\x1f\x7f]', '', clean)
    # Allow alphanumeric, underscore, hyphen, dot
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', clean)
    return clean or "unnamed_file"

async def run_dcmtk_tool(tool: str, args: List[str], timeout: float = 60.0) -> None:
    logger.info(f"Executing DCMTK tool {tool} with {len(args)} arguments")
    try:
        proc = await asyncio.create_subprocess_exec(
            tool,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            err_msg = stderr.decode('utf-8', errors='ignore')
            logger.error(f"DCMTK tool {tool} failed with exit code {proc.returncode}: {err_msg}")
            raise RuntimeError(f"DCMTK tool {tool} failed: {err_msg}")
    except asyncio.TimeoutError:
        proc.kill()
        logger.error(f"DCMTK tool {tool} timed out after {timeout} seconds")
        raise RuntimeError(f"DCMTK tool {tool} execution timed out")

def parse_keys_to_args(keys: Optional[List[str]]) -> List[str]:
    args = []
    if keys:
        for k in keys:
            if k and "=" in k:
                args.extend(["--key", k.strip()])
    return args

def refine_dicom_metadata(dcm_path: str):
    """Ensure SpecificCharacterSet ISO_IR 192 (UTF-8) and clean DICOM metadata using pydicom."""
    try:
        ds = pydicom.dcmread(dcm_path)
        ds.SpecificCharacterSet = "ISO_IR 192"
        ds.save_as(dcm_path)
        logger.debug(f"Refined DICOM metadata for {dcm_path}")
    except Exception as e:
        logger.warning(f"Could not refine pydicom metadata for {dcm_path}: {e}")

async def convert_img(input_path: str, output_path: str, temp_dir: str, original_filename: str, keys: Optional[List[str]] = None) -> str:
    ext = os.path.splitext(original_filename)[1].lower()
    work_input = input_path
    cmd_args = []
    
    # img2dcm natively supports JPEG and BMP. Convert PNG to BMP using Pillow first if needed.
    if ext == ".png":
        bmp_path = os.path.join(temp_dir, "temp_converted.bmp")
        with Image.open(input_path) as img:
            img.convert("RGB").save(bmp_path, "BMP")
        work_input = bmp_path
        cmd_args.extend(["-i", "BMP"])
    elif ext == ".bmp":
        cmd_args.extend(["-i", "BMP"])

    cmd_args.extend(parse_keys_to_args(keys))
    cmd_args.extend([work_input, output_path])
    
    await run_dcmtk_tool("img2dcm", cmd_args)
    refine_dicom_metadata(output_path)
    return output_path

async def convert_pdf(input_path: str, output_path: str, keys: Optional[List[str]] = None) -> str:
    cmd_args = parse_keys_to_args(keys)
    cmd_args.extend([input_path, output_path])
    await run_dcmtk_tool("pdf2dcm", cmd_args)
    refine_dicom_metadata(output_path)
    return output_path

async def convert_cda(input_path: str, output_path: str, keys: Optional[List[str]] = None) -> str:
    cmd_args = parse_keys_to_args(keys)
    cmd_args.extend([input_path, output_path])
    await run_dcmtk_tool("cda2dcm", cmd_args)
    refine_dicom_metadata(output_path)
    return output_path

async def convert_stl(input_path: str, output_path: str, keys: Optional[List[str]] = None) -> str:
    cmd_args = parse_keys_to_args(keys)
    cmd_args.extend([input_path, output_path])
    await run_dcmtk_tool("stl2dcm", cmd_args)
    refine_dicom_metadata(output_path)
    return output_path
