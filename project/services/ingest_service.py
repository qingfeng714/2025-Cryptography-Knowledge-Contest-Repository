# services/ingest_service.py
import uuid

def parseDICOM(dicom_file=None):
    """
    模拟 DICOM 文件解析，返回一个唯一 ingest_id
    """
    return str(uuid.uuid4())
