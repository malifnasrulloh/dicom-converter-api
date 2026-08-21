import logging
import pydicom
from pynetdicom import AE, StoragePresentationContexts, AllStoragePresentationContexts

logger = logging.getLogger("dicom-sender")

def send_dicom_cstore(dcm_path: str, remote_host: str, remote_port: int, remote_aet: str, calling_aet: str = "SIMRS_CONVERTER") -> bool:
    """Send a DICOM file directly over native C-STORE protocol to a remote DICOM SCU/SCP node."""
    try:
        ds = pydicom.dcmread(dcm_path)
        ae = AE(ae_title=calling_aet.encode('ascii'))
        
        # Explicitly register the dataset's SOP Class and Transfer Syntax + fallbacks
        sop_class = getattr(ds, "SOPClassUID", None)
        transfer_syntax = getattr(getattr(ds, "file_meta", None), "TransferSyntaxUID", "1.2.840.10008.1.2.4.50")
        
        if sop_class:
            t_syntaxes = [
                str(transfer_syntax),
                "1.2.840.10008.1.2.4.50",  # JPEG Baseline Process 1
                "1.2.840.10008.1.2.4.70",  # JPEG Lossless
                "1.2.840.10008.1.2.1",     # Explicit VR Little Endian
                "1.2.840.10008.1.2",       # Implicit VR Little Endian
            ]
            ae.add_requested_context(sop_class, t_syntaxes)
        
        # Include standard storage presentation contexts
        for context in StoragePresentationContexts:
            ae.add_requested_context(context.abstract_syntax)

        assoc = ae.associate(remote_host, remote_port, ae_title=remote_aet.encode('ascii'))
        if assoc.is_established:
            status = assoc.send_c_store(ds)
            assoc.release()
            if status and getattr(status, 'Status', None) == 0x0000:
                logger.info(f"C-STORE transfer successful for {dcm_path} to {remote_aet}@{remote_host}:{remote_port}")
                return True
            else:
                status_code = getattr(status, 'Status', 0xFFFF)
                logger.error(f"C-STORE transfer failed with status 0x{status_code:04x}")
                return False
        else:
            logger.error(f"Failed to establish DICOM association with {remote_aet}@{remote_host}:{remote_port}")
            return False
    except Exception as e:
        logger.error(f"C-STORE exception: {e}", exc_info=True)
        return False
