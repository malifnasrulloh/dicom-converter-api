import logging
import pydicom
from pynetdicom import AE, StoragePresentationContexts

logger = logging.getLogger("dicom-sender")

def send_dicom_cstore(dcm_path: str, remote_host: str, remote_port: int, remote_aet: str, calling_aet: str = "PYTHON_SCU") -> bool:
    """Send a DICOM file directly over native C-STORE protocol to a remote DICOM SCU/SCP node."""
    try:
        ds = pydicom.dcmread(dcm_path)
        ae = AE(ae_title=calling_aet.encode('ascii'))
        ae.requested_contexts = StoragePresentationContexts

        assoc = ae.associate(remote_host, remote_port, ae_title=remote_aet.encode('ascii'))
        if assoc.is_established:
            status = assoc.send_c_store(ds)
            assoc.release()
            if status and getattr(status, 'Status', None) == 0x0000:
                logger.info(f"C-STORE transfer successful for {dcm_path} to {remote_aet}@{remote_host}:{remote_port}")
                return True
            else:
                logger.error(f"C-STORE transfer failed with status 0x{status.Status:04x}")
                return False
        else:
            logger.error(f"Failed to establish DICOM association with {remote_aet}@{remote_host}:{remote_port}")
            return False
    except Exception as e:
        logger.error(f"C-STORE exception: {e}")
        return False
