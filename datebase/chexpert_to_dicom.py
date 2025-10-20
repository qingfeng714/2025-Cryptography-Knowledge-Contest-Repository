
import argparse
import hashlib
import json
import os
from datetime import datetime, date, timedelta, timezone
from uuid import uuid5, NAMESPACE_URL

import numpy as np
import pandas as pd
from PIL import Image, ImageFile
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian

ImageFile.LOAD_TRUNCATED_IMAGES = True

# ----------------- Utilities -----------------

PSEUDONYM_SALT = "proj-med-privacy-2025"  # change per domain for isolation

def stable_token(seed: str, length: int = 12) -> str:
    h = hashlib.sha256((PSEUDONYM_SALT + "|" + str(seed)).encode()).hexdigest().upper()
    return h[:length]

def make_uid(seed: str) -> str:
    # UUIDv5 turned into a decimal UID under 2.25.* (valid DICOM UID)
    return "2.25." + str(int(uuid5(NAMESPACE_URL, seed).int))

def synth_date(seed: str, start=date(2018,1,1), end=date(2022,12,31)) -> str:
    # Deterministic pseudo-random date per seed within [start, end]
    h = int(hashlib.sha256((PSEUDONYM_SALT + "|DATE|" + str(seed)).encode()).hexdigest(), 16)
    delta_days = (end - start).days
    d = start + timedelta(days=(h % max(delta_days, 1)))
    return d.strftime("%Y%m%d")

def to_patient_age(age_val) -> str:
    # DICOM PatientAge is 3 digits + 'Y' (or M/D). We use years.
    try:
        age = int(float(age_val))
    except Exception:
        age = 0
    age = max(0, min(age, 999))
    return f"{age:03d}Y"

def sex_to_dicom(sex):
    if isinstance(sex, str):
        s = sex.strip().upper()
        if s in ("M","MALE"): return "M"
        if s in ("F","FEMALE"): return "F"
    return "O"

def image_to_numpy(img_path: str, force_gray=True):
    im = Image.open(img_path)
    if force_gray:
        im = im.convert("L")
        arr = np.asarray(im)
        photometric = "MONOCHROME2"
        samples = 1
        planar = None
    else:
        im = im.convert("RGB")
        arr = np.asarray(im)
        photometric = "RGB"
        samples = 3
        planar = 0
    if arr.dtype != np.uint8:
        arr = (255 * (arr.astype(np.float32) / (arr.max() + 1e-6))).astype(np.uint8)
    return arr, photometric, samples, planar

# ----------------- ID from folder -----------------

def derive_folder_component(rel_path: str, ancestor: int = 2) -> str:
    """
    Return a folder name from the original dataset relative path.
    ancestor = 1 -> parent folder name (e.g., 'study1')
    ancestor = 2 -> grandparent folder name (e.g., 'patient00001')  [DEFAULT for CheXpert]
    """
    parts = rel_path.replace("\\", "/").split("/")
    if len(parts) < ancestor + 1:
        return os.path.splitext(os.path.basename(rel_path))[0]
    return parts[-(ancestor+1)]

# ----------------- Core conversion -----------------

def build_dicom_from_image(
    img_path: str,
    out_path: str,
    patient_id: str,
    patient_name: str,
    patient_sex: str,
    patient_age: str,
    accession: str,
    study_uid: str,
    series_uid: str,
    sop_uid: str,
    study_date: str,
    institution: str = "CHEXPERT-KAGGLE",
    modality: str = "SC",
    body_part: str = "CHEST",
    private_json: dict | None = None
):
    arr, photometric, samples, planar = image_to_numpy(img_path, force_gray=True)
    rows, cols = arr.shape[:2]

    # File Meta
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = "1.2.826.0.1.3680043.10.543.1"

    ds = FileDataset(out_path, {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # Patient / Study / Series
    ds.PatientID = patient_id
    ds.PatientName = patient_name
    ds.PatientSex = patient_sex
    ds.PatientAge = patient_age
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid
    ds.SOPInstanceUID = sop_uid
    ds.Modality = modality
    ds.AccessionNumber = accession
    ds.InstitutionName = institution
    ds.StudyDate = study_date
    ds.StudyTime = "120000"
    ds.SeriesNumber = 1
    ds.InstanceNumber = 1
    ds.BodyPartExamined = body_part
    ds.ConversionType = "SYN"

    # Pixels
    ds.Rows = int(rows); ds.Columns = int(cols)
    ds.SamplesPerPixel = samples
    ds.PhotometricInterpretation = photometric
    if planar is not None:
        ds.PlanarConfiguration = planar
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    ds.PixelSpacing = [1.0, 1.0]  # unknown
    ds.PixelData = arr.tobytes()

    # Optional private metadata snapshot
    if private_json is not None:
        try:
            ds.add_new(0x00110010, 'LO', 'CHEXPERT-META')          # Private Creator
            payload = json.dumps(private_json)[:65530]             # LT limit
            ds.add_new(0x00111001, 'LT', payload)
        except Exception:
            pass

    ds.save_as(out_path, write_like_original=False)
    return out_path

def derive_ids_from_path(rel_path: str, id_from_folder_ancestor: int = 2):
    """
    PatientID/PatientName = folder name from original dataset path (configurable level).
    AccessionNumber      = hashed token from (patient_folder|study_folder).
    UIDs & StudyDate     = deterministic from path components.
    """
    parts = rel_path.replace("\\", "/").split("/")
    patient_folder = derive_folder_component(rel_path, ancestor=id_from_folder_ancestor)
    study_folder = derive_folder_component(rel_path, ancestor=1)  # usually 'studyX'
    view = os.path.basename(rel_path)

    # Patient ID/Name from folder
    patient_id = str(patient_folder)
    patient_name = "".join(ch for ch in patient_id if ch.isalnum()) or "PN_UNKNOWN"

    # AccessionNumber derived (deterministic) from patient+study
    accession = "A" + stable_token(f"{patient_id}|{study_folder}", 10)

    # Deterministic UIDs & date
    study_uid = make_uid(f"study|{patient_id}|{study_folder}")
    series_uid = make_uid(f"series|{patient_id}|{study_folder}|{view}")
    sop_uid = make_uid(f"sop|{rel_path}|{datetime.now(timezone.utc).isoformat()}")
    study_date = synth_date(f"{patient_id}|{study_folder}")
    return patient_id, patient_name, accession, study_uid, series_uid, sop_uid, study_date

def hashed_output_name(rel_path: str) -> str:
    # Use SHA-256 of the relative path to avoid collisions in a flat folder
    h = hashlib.sha256(rel_path.replace("\\","/").encode()).hexdigest()[:24]
    return f"{h}.dcm"

def convert_csv(csv_path: str, images_root: str, out_dir: str, limit: int | None = None,
                id_from_folder_ancestor: int = 2, institution: str = "CHEXPERT-KAGGLE"):
    os.makedirs(out_dir, exist_ok=True)
    df = pd.read_csv(csv_path)

    # We assume only two patient info columns exist: Sex and Age.
    # Path is still required to locate the image files.
    path_col = "Path" if "Path" in df.columns else "path"
    if path_col not in df.columns:
        raise ValueError("CSV must include 'Path' column.")
    sex_col = "Sex" if "Sex" in df.columns else None
    age_col = "Age" if "Age" in df.columns else None

    n = len(df) if limit is None else min(limit, len(df))
    converted, missing = 0, 0

    for idx, row in df.head(n).iterrows():
        rel_path = row[path_col]
        img_path = os.path.join(images_root, rel_path)
        if not os.path.exists(img_path):
            missing += 1
            continue

        # Only patient info: Sex & Age (fallbacks if missing)
        sex = sex_to_dicom(row[sex_col]) if sex_col else "O"
        age = to_patient_age(row[age_col]) if age_col else "000Y"

        patient_id, patient_name, accession, study_uid, series_uid, sop_uid, study_date = derive_ids_from_path(
            rel_path, id_from_folder_ancestor=id_from_folder_ancestor
        )

        private_json = {
            "source_path": rel_path,
            "csv_row_index": int(idx),
            "sex_csv": row.get(sex_col, None) if sex_col else None,
            "age_csv": row.get(age_col, None) if age_col else None,
            "id_from_folder_ancestor": id_from_folder_ancestor
        }

        out_name = hashed_output_name(rel_path)          # flat hashed filename
        out_path = os.path.join(out_dir, out_name)

        build_dicom_from_image(
            img_path=img_path,
            out_path=out_path,
            patient_id=patient_id,
            patient_name=patient_name,
            patient_sex=sex,
            patient_age=age,
            accession=accession,
            study_uid=study_uid,
            series_uid=series_uid,
            sop_uid=sop_uid,
            study_date=study_date,
            institution=institution,
            private_json=private_json
        )
        converted += 1

    print(f"Converted: {converted}, Missing images: {missing}, From CSV rows: {n}")

def main():
    ap = argparse.ArgumentParser(description="CheXpert JPGs -> DICOM SC, using ONLY Sex/Age from CSV; PatientID from folder name.")
    ap.add_argument("--csv", required=True, help="Path to CheXpert CSV (train.csv or valid.csv)")
    ap.add_argument("--images-root", required=True, help="Root folder where 'Path' in CSV is relative to")
    ap.add_argument("--out", required=True, help="Output directory for DICOM files")
    ap.add_argument("--limit", type=int, default=None, help="Convert only first N rows (for testing)")
    ap.add_argument("--id-from-folder-ancestor", type=int, default=2, help="Which folder level to use for PatientID: 1=parent, 2=grandparent (CheXpert 'patientXXXX')")
    ap.add_argument("--institution", default="CHEXPERT-KAGGLE", help="InstitutionName to store in DICOM")
    args = ap.parse_args()

    convert_csv(
        csv_path=args.csv,
        images_root=args.images_root,
        out_dir=args.out,
        limit=args.limit,
        id_from_folder_ancestor=args.id_from_folder_ancestor,
        institution=args.institution
    )

if __name__ == "__main__":
    main()
