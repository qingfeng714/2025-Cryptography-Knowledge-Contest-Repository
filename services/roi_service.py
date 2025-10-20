import pydicom
import numpy as np
import torch
from typing import Optional, Tuple, Dict
from pathlib import Path
from dataclasses import dataclass

@dataclass
class DicomProcessingResult:
    pixel_array: np.ndarray
    normalized_tensor: torch.Tensor
    metadata: Dict[str, str]
    roi_mask: Optional[np.ndarray] = None
    roi_boxes: Optional[list] = None

class DicomProcessor:
    def __init__(self, device: str = 'cpu'):
        self.device = device
        
    def process_dicom(self, dicom_path: Path) -> Optional[DicomProcessingResult]:
        """处理单个DICOM文件，提取像素数据和元数据"""
        try:
            ds = pydicom.dcmread(str(dicom_path), force=True)
            pixel_array = self._get_pixel_array(ds)
            
            return DicomProcessingResult(
                pixel_array=pixel_array,
                normalized_tensor=self._normalize_to_tensor(pixel_array),
                metadata=self._extract_metadata(ds),
                roi_mask=self._detect_roi(pixel_array),
                roi_boxes=self._get_roi_boxes(pixel_array)
            )
        except Exception as e:
            print(f"Error processing {dicom_path}: {str(e)}")
            return None
    
    def _get_pixel_array(self, ds: pydicom.Dataset) -> np.ndarray:
        """提取并标准化像素数据"""
        array = ds.pixel_array.astype(np.float32)
        return (array -