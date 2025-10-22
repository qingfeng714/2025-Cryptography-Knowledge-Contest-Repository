import pydicom
import numpy as np
import torch
import cv2
from typing import Optional, Tuple, Dict, List
from pathlib import Path
from dataclasses import dataclass
from pydicom.errors import InvalidDicomError
from PIL import Image

# PHI标签定义
PHI_TAGS = [
    ("PatientName",        (0x0010,0x0010)),
    ("PatientID",          (0x0010,0x0020)),
    ("PatientBirthDate",   (0x0010,0x0030)),
    ("PatientSex",         (0x0010,0x0040)),
    ("PatientAge",         (0x0010,0x1010)),
    ("AccessionNumber",    (0x0008,0x0050)),
    ("StudyInstanceUID",   (0x0020,0x000D)),
    ("SeriesInstanceUID",  (0x0020,0x000E)),
    ("SOPInstanceUID",     (0x0008,0x0018)),
    ("StudyDate",          (0x0008,0x0020)),
    ("StudyTime",          (0x0008,0x0030)),
    ("InstitutionName",    (0x0008,0x0080)),
]

@dataclass
class DicomProcessingResult:
    dicom_path: str
    pixel_array: np.ndarray
    normalized_tensor: torch.Tensor
    metadata: Dict[str, str]
    roi_mask: Optional[np.ndarray] = None
    roi_boxes: Optional[List[Tuple[int,int,int,int]]] = None
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    accession: Optional[str] = None
    study_date: Optional[str] = None
    institution: Optional[str] = None
    patient_sex: Optional[str] = None
    patient_age: Optional[str] = None
    burned_in_annotation: Optional[str] = None
    roi_type: str = "header_only"
    image_size: Optional[Tuple[int,int]] = None

class DicomProcessor:
    def __init__(self, device: str = 'cpu'):
        self.device = device
        
    def process_dicom(self, dicom_path: Path, try_burnedin: bool = False) -> Optional[DicomProcessingResult]:
        """处理单个DICOM文件，提取像素数据和元数据"""
        try:
            ds = pydicom.dcmread(str(dicom_path), force=True)
            pixel_array = self._get_pixel_array(ds)
            
            # 提取header信息
            header = self._extract_header_info(ds)
            
            # 检测ROI区域
            roi_mask, roi_boxes = self._detect_roi_regions(pixel_array, try_burnedin)
            
            return DicomProcessingResult(
                dicom_path=str(dicom_path),
                pixel_array=pixel_array,
                normalized_tensor=self._normalize_to_tensor(pixel_array),
                metadata=header,
                roi_mask=roi_mask,
                roi_boxes=roi_boxes,
                patient_id=header.get("PatientID"),
                patient_name=header.get("PatientName"),
                accession=header.get("AccessionNumber"),
                study_date=header.get("StudyDate"),
                institution=header.get("InstitutionName"),
                patient_sex=header.get("PatientSex"),
                patient_age=header.get("PatientAge"),
                burned_in_annotation=header.get("BurnedInAnnotation"),
                roi_type="burned_in" if roi_boxes else "header_only",
                image_size=pixel_array.shape[:2] if len(pixel_array.shape) >= 2 else None
            )
        except Exception as e:
            print(f"Error processing {dicom_path}: {str(e)}")
            return None
    
    def _get_pixel_array(self, ds: pydicom.Dataset) -> np.ndarray:
        """提取并标准化像素数据"""
        array = ds.pixel_array.astype(np.float32)
        return (array - array.min()) / (array.max() - array.min() + 1e-6)
    
    def _extract_header_info(self, ds: pydicom.Dataset) -> Dict[str, str]:
        """提取DICOM header中的PHI信息"""
        header = {}
        for name, tag in PHI_TAGS:
            try:
                value = ds.get(tag, None)
                if value is not None:
                    if hasattr(value, 'value'):
                        header[name] = str(value.value)
                    else:
                        header[name] = str(value)
                else:
                    header[name] = None
            except Exception:
                header[name] = None
        return header
    
    def _normalize_to_tensor(self, pixel_array: np.ndarray) -> torch.Tensor:
        """将像素数组转换为标准化的tensor"""
        # 归一化到0-1范围
        normalized = (pixel_array - pixel_array.min()) / (pixel_array.max() - pixel_array.min() + 1e-6)
        # 转换为tensor并添加batch和channel维度
        tensor = torch.FloatTensor(normalized).unsqueeze(0).unsqueeze(0)
        return tensor.to(self.device)
    
    def _detect_roi_regions(self, pixel_array: np.ndarray, try_burnedin: bool = False) -> Tuple[Optional[np.ndarray], Optional[List[Tuple[int,int,int,int]]]]:
        """检测ROI区域"""
        if not try_burnedin:
            return None, []
        
        try:
            # 转换为8位灰度图
            gray_u8 = self._normalize_to_u8(pixel_array)
            roi_boxes = self._detect_burnedin_text(gray_u8)
            
            # 生成ROI掩码
            roi_mask = np.zeros_like(gray_u8, dtype=np.uint8)
            for (x, y, w, h) in roi_boxes:
                roi_mask[y:y+h, x:x+w] = 255
            
            return roi_mask, roi_boxes
        except Exception as e:
            print(f"ROI detection failed: {e}")
            return None, []
    
    def _normalize_to_u8(self, arr: np.ndarray) -> np.ndarray:
        """归一化到8位图像"""
        arr = arr.astype(np.float32)
        a, b = np.percentile(arr, [0.5, 99.5])
        if b <= a:
            b = arr.max()
            a = arr.min()
        arr = np.clip((arr - a) / (b - a + 1e-6), 0, 1)
        return (arr * 255).astype(np.uint8)
    
    def _detect_burnedin_text(self, gray_u8: np.ndarray) -> List[Tuple[int,int,int,int]]:
        """检测烧录文本区域"""
        h, w = gray_u8.shape
        
        # 使用CLAHE增强对比度
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        eq = clahe.apply(gray_u8)
        
        # Otsu阈值化
        _, otsu = cv2.threshold(eq, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        bin_img = 255 - otsu
        
        # 形态学操作
        kx = max(3, w // 300)
        ky = max(1, h // 400)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kx, ky))
        mor = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE, kernel, iterations=1)
        mor = cv2.medianBlur(mor, 3)
        
        # 连通组件分析
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mor, connectivity=8)
        boxes = []
        
        for i in range(1, n):
            x, y, w0, h0, area = stats[i,0], stats[i,1], stats[i,2], stats[i,3], stats[i,4]
            if area < 40 or w0 < 10 or h0 < 8:
                continue
            aspect = w0 / max(h0, 1)
            if aspect < 1.5 or aspect > 40:
                continue
            boxes.append((int(x), int(y), int(w0), int(h0)))
        
        # 非极大值抑制
        return self._nms(boxes)
    
    def _nms(self, boxes: List[Tuple[int,int,int,int]]) -> List[Tuple[int,int,int,int]]:
        """非极大值抑制"""
        def area(b):
            return b[2] * b[3]
        
        def iou(a, b):
            ax, ay, aw, ah = a
            bx, by, bw, bh = b
            xa1, ya1, xa2, ya2 = ax, ay, ax + aw, ay + ah
            xb1, yb1, xb2, yb2 = bx, by, bx + bw, by + bh
            ix1, iy1 = max(xa1, xb1), max(ya1, yb1)
            ix2, iy2 = min(xa2, xb2), min(ya2, yb2)
            iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
            inter = iw * ih
            uni = aw * ah + bw * bh - inter
            return inter / uni if uni > 0 else 0
        
        keep = []
        for b in sorted(boxes, key=area, reverse=True):
            if all(iou(b, k) < 0.3 for k in keep):
                keep.append(b)
        
        return keep[:20]  # 最多保留20个区域

class ROISegmenter:
    """ROI分割服务"""
    def __init__(self):
        self.processor = DicomProcessor()
    
    def segment(self, pixel_array: np.ndarray) -> np.ndarray:
        """分割ROI区域"""
        try:
            _, roi_boxes = self.processor._detect_roi_regions(pixel_array, try_burnedin=True)
            if not roi_boxes:
                return np.zeros_like(pixel_array, dtype=np.uint8)
            
            roi_mask = np.zeros_like(pixel_array, dtype=np.uint8)
            for (x, y, w, h) in roi_boxes:
                roi_mask[y:y+h, x:x+w] = 255
            
            return roi_mask
        except Exception:
            return np.zeros_like(pixel_array, dtype=np.uint8)