
"""
Parse DICOM header for PHI-like tags (especially PatientID) and produce a ROI mask.
Since PatientID is metadata (header) and not pixels, the default ROI mask is empty.
(Optionally, you can enable a heuristic detector to try finding burned-in text.)

Usage (Windows PowerShell):
  python dicom_header_and_roi.py ^
    --in-root "C:\path\to\dicoms" ^
    --out "C:\path\to\out" ^
    --pattern "*.dcm" ^
    --max 500

Optional (try detect burned-in text areas):
  python dicom_header_and_roi.py ^
    --in-root "C:\path\to\dicoms" ^
    --out "C:\path\to\out" ^
    --try-burnedin

Dependencies:
  pip install pydicom pillow numpy pandas tqdm
  # if using --try-burnedin:
  pip install opencv-python pytesseract
  # and install the Tesseract binary (system-dependent)
"""
import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
import pandas as pd
import pydicom
from pydicom.errors import InvalidDicomError
from PIL import Image
from tqdm import tqdm

# Optional CV/OCR only if --try-burnedin
_cv_loaded = False
_ocr_loaded = False

def _lazy_import_cv_ocr():
    global _cv_loaded, _ocr_loaded, cv2, pytesseract
    if not _cv_loaded:
        import cv2  # type: ignore
        _cv_loaded = True
    if not _ocr_loaded:
        try:
            import pytesseract  # type: ignore
            _ocr_loaded = True
        except Exception:
            _ocr_loaded = False

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

def ds_get(ds, tag, default=None):
    try:
        v = ds.get(tag, default)
        if v is None: return default
        return v if isinstance(v, (str, int, float)) else str(v.value) if hasattr(v, "value") else str(v)
    except Exception:
        return default

def normalize_u8(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32)
    a, b = np.percentile(arr, [0.5, 99.5])
    if b <= a:
        b = arr.max(); a = arr.min()
    arr = np.clip((arr - a) / (b - a + 1e-6), 0, 1)
    return (arr * 255).astype(np.uint8)

@dataclass
class HeaderAndROI:
    dicom_path: str
    patient_id: Optional[str] = None
    accession: Optional[str] = None
    study_date: Optional[str] = None
    institution: Optional[str] = None
    patient_sex: Optional[str] = None
    patient_age: Optional[str] = None
    burned_in_annotation: Optional[str] = None  # (0028,0301)
    roi_boxes: Optional[List[Tuple[int,int,int,int]]] = None  # empty by default
    roi_type: str = "header_only"  # or 'burned_in' if detected
    image_size: Optional[Tuple[int,int]] = None

def detect_burnedin(gray_u8: np.ndarray) -> List[Tuple[int,int,int,int]]:
    # Minimal heuristic for text-like areas (edge/threshold + morphology)
    _lazy_import_cv_ocr()
    h, w = gray_u8.shape
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    eq = clahe.apply(gray_u8)
    _, otsu = cv2.threshold(eq, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bin_img = 255 - otsu
    kx = max(3, w // 300); ky = max(1, h // 400)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kx, ky))
    mor = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE, kernel, iterations=1)
    mor = cv2.medianBlur(mor, 3)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mor, connectivity=8)
    boxes = []
    for i in range(1, n):
        x,y,w0,h0,area = stats[i,0], stats[i,1], stats[i,2], stats[i,3], stats[i,4]
        if area < 40 or w0 < 10 or h0 < 8: continue
        aspect = w0 / max(h0,1)
        if aspect < 1.5 or aspect > 40: continue
        boxes.append((int(x), int(y), int(w0), int(h0)))
    # Greedy NMS
    def area(b): return b[2]*b[3]
    def iou(a,b):
        ax,ay,aw,ah=a; bx,by,bw,bh=b
        xa1,ya1,xa2,ya2=ax,ay,ax+aw,ay+ah
        xb1,yb1,xb2,yb2=bx,by,bx+bw,by+bh
        ix1,iy1=max(xa1,xb1),max(ya1,yb1)
        ix2,iy2=min(xa2,xb2),min(ya2,yb2)
        iw,ih=max(0,ix2-ix1),max(0,iy2-iy1)
        inter=iw*ih; uni=aw*ah+bw*bh-inter
        return inter/uni if uni>0 else 0
    keep=[]
    for b in sorted(boxes, key=area, reverse=True):
        if all(iou(b,k)<0.3 for k in keep): keep.append(b)
    return keep[:20]

def process_one(dcm_path: Path, out_dir: Path, try_burnedin: bool=False) -> Optional[HeaderAndROI]:
    try:
        ds = pydicom.dcmread(str(dcm_path), force=True)
    except (InvalidDicomError, Exception):
        return None

    header = {name: ds_get(ds, tag) for name, tag in PHI_TAGS}
    burned_in = ds_get(ds, (0x0028,0x0301))

    # By default, ROI is empty because PatientID is header-only
    roi_boxes: List[Tuple[int,int,int,int]] = []
    roi_type = "header_only"
    size = None

    if try_burnedin:
        try:
            arr = ds.pixel_array
            gray = normalize_u8(arr)
            size = gray.shape[:2]
            boxes = detect_burnedin(gray)
            if boxes:
                roi_boxes = boxes
                roi_type = "burned_in"
            # Save an empty/real mask for reference
            masks_dir = out_dir / "masks"; masks_dir.mkdir(parents=True, exist_ok=True)
            mask = np.zeros_like(gray, dtype=np.uint8)
            for (x,y,w,h) in roi_boxes:
                mask[y:y+h, x:x+w] = 255
            Image.fromarray(mask).save(masks_dir / f"{dcm_path.stem}_mask.png")
        except Exception:
            pass

    rec = HeaderAndROI(
        dicom_path=str(dcm_path),
        patient_id=header.get("PatientID"),
        accession=header.get("AccessionNumber"),
        study_date=header.get("StudyDate"),
        institution=header.get("InstitutionName"),
        patient_sex=header.get("PatientSex"),
        patient_age=header.get("PatientAge"),
        burned_in_annotation=burned_in,
        roi_boxes=roi_boxes,
        roi_type=roi_type,
        image_size=size,
    )
    return rec

def run(in_root: Path, out_root: Path, pattern: str="*.dcm", max_files: int=500, try_burnedin: bool=False):
    out_root.mkdir(parents=True, exist_ok=True)
    files = sorted(in_root.rglob(pattern))
    if max_files is not None:
        files = files[:max_files]

    results = []
    for f in tqdm(files, desc="Parsing DICOM headers"):
        r = process_one(f, out_root, try_burnedin=try_burnedin)
        if r is not None:
            results.append(r)

    rows = [asdict(r) for r in results]
    pd.DataFrame(rows).to_csv(out_root / "header_and_roi_summary.csv", index=False)
    with open(out_root / "header_and_roi_summary.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Done. Files scanned: {len(files)}; Results: {len(results)}")
    print(f"Outputs:\n  - {out_root / 'header_and_roi_summary.csv'}\n  - {out_root / 'header_and_roi_summary.jsonl'}\n  - masks/ (only if --try-burnedin)")

def main():
    ap = argparse.ArgumentParser(description="Extract header PHI (e.g., PatientID) and produce ROI (empty by default).")
    ap.add_argument("--in-root", required=True, help="Input folder with DICOM files")
    ap.add_argument("--out", required=True, help="Output folder")
    ap.add_argument("--pattern", default="*.dcm", help="Glob pattern (default: *.dcm)")
    ap.add_argument("--max", type=int, default=500, help="Max files to process")
    ap.add_argument("--try-burnedin", action="store_true", help="Attempt burned-in text detection to create pixel ROI")
    args = ap.parse_args()

    run(Path(args.in_root), Path(args.out), pattern=args.pattern, max_files=args.max, try_burnedin=args.try_burnedin)

if __name__ == "__main__":
    main()
