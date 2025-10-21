"""
基于原始三个脚本的简化医疗隐私检测系统
"""
import os
import uuid
import pandas as pd
import pydicom
import numpy as np
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from dataclasses import dataclass
from typing import List, Dict, Optional
import json

# 从原始脚本导入核心功能
from dicom_header_and_roi import process_one, PHI_TAGS
from process_csv import NERService
from cross_modal_privacy import load_and_match_data

app = Flask(__name__)

# 确保上传目录存在
UPLOAD_FOLDER = './uploads'
OUTPUT_FOLDER = './output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("simple_index.html")

@app.route("/api/process_csv", methods=["POST"])
def process_csv():
    """处理CSV文件 - 基于process_csv.py"""
    try:
        csv_file = request.files.get("csv")
        if not csv_file:
            return jsonify({"error": "No CSV file provided"}), 400
        
        # 保存CSV文件
        csv_id = f"csv_{uuid.uuid4().hex[:8]}"
        csv_path = os.path.join(UPLOAD_FOLDER, f"{csv_id}.csv")
        csv_file.save(csv_path)
        
        # 使用原始NER服务处理
        ner = NERService()
        output_path = os.path.join(OUTPUT_FOLDER, f"{csv_id}_processed.csv")
        
        success = ner.process_csv(
            input_path=csv_path,
            output_path=output_path
        )
        
        if success:
            # 读取处理结果
            result_df = pd.read_csv(output_path)
            entities_count = len([row for row in result_df['detected_entities'] if row and row != '[]'])
            
            return jsonify({
                "csv_id": csv_id,
                "csv_path": csv_path,
                "output_path": output_path,
                "entities_count": entities_count,
                "status": "success"
            })
        else:
            return jsonify({"error": "CSV processing failed"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/process_dicom", methods=["POST"])
def process_dicom():
    """处理DICOM文件 - 基于dicom_header_and_roi.py"""
    try:
        dicom_file = request.files.get("dicom")
        if not dicom_file:
            return jsonify({"error": "No DICOM file provided"}), 400
        
        # 保存DICOM文件
        dicom_id = f"dicom_{uuid.uuid4().hex[:8]}"
        dicom_path = os.path.join(UPLOAD_FOLDER, f"{dicom_id}.dcm")
        dicom_file.save(dicom_path)
        
        # 使用原始DICOM处理功能
        result = process_one(Path(dicom_path), Path(OUTPUT_FOLDER), try_burnedin=True)
        
        if result:
            # 转换为可序列化的格式
            dicom_data = {
                "dicom_id": dicom_id,
                "dicom_path": dicom_path,
                "patient_id": result.patient_id,
                "accession": result.accession,
                "study_date": result.study_date,
                "institution": result.institution,
                "patient_sex": result.patient_sex,
                "patient_age": result.patient_age,
                "roi_type": result.roi_type,
                "roi_boxes_count": len(result.roi_boxes) if result.roi_boxes else 0,
                "image_size": result.image_size
            }
            
            return jsonify({
                "dicom_id": dicom_id,
                "dicom_data": dicom_data,
                "status": "success"
            })
        else:
            return jsonify({"error": "DICOM processing failed"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/cross_modal_match", methods=["POST"])
def cross_modal_match():
    """跨模态匹配 - 基于cross_modal_privacy.py"""
    try:
        data = request.json
        csv_path = data.get("csv_path")
        dicom_data = data.get("dicom_data")
        
        if not csv_path or not dicom_data:
            return jsonify({"error": "Missing CSV or DICOM data"}), 400
        
        # 读取CSV文件
        df = pd.read_csv(csv_path, encoding='utf-8', encoding_errors='ignore')
        
        # 执行跨模态匹配
        matches = []
        for _, row in df.iterrows():
            # 检查患者ID匹配
            if 'patient_id' in row and dicom_data.get('patient_id'):
                if str(row['patient_id']) == str(dicom_data['patient_id']):
                    matches.append({
                        "row_index": row.name,
                        "match_type": "patient_id",
                        "confidence": 1.0,
                        "risk_level": "high"
                    })
            
            # 检查其他字段匹配
            for col in df.columns:
                if col in dicom_data and pd.notna(row[col]):
                    if str(row[col]) == str(dicom_data[col]):
                        matches.append({
                            "row_index": row.name,
                            "column": col,
                            "match_type": "field_match",
                            "confidence": 0.8,
                            "risk_level": "medium"
                        })
        
        return jsonify({
            "matches": matches,
            "total_matches": len(matches),
            "high_risk_matches": len([m for m in matches if m['risk_level'] == 'high']),
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/process_complete", methods=["POST"])
def process_complete():
    """完整处理流程"""
    try:
        # 处理CSV
        csv_file = request.files.get("csv")
        dicom_file = request.files.get("dicom")
        
        if not csv_file:
            return jsonify({"error": "No CSV file provided"}), 400
        
        # 保存文件
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        csv_path = os.path.join(UPLOAD_FOLDER, f"{session_id}.csv")
        csv_file.save(csv_path)
        
        dicom_path = None
        dicom_data = None
        if dicom_file:
            dicom_path = os.path.join(UPLOAD_FOLDER, f"{session_id}.dcm")
            dicom_file.save(dicom_path)
            
            # 处理DICOM
            result = process_one(Path(dicom_path), Path(OUTPUT_FOLDER), try_burnedin=True)
            if result:
                dicom_data = {
                    "patient_id": result.patient_id,
                    "accession": result.accession,
                    "study_date": result.study_date,
                    "institution": result.institution,
                    "patient_sex": result.patient_sex,
                    "patient_age": result.patient_age,
                    "roi_type": result.roi_type,
                    "roi_boxes_count": len(result.roi_boxes) if result.roi_boxes else 0
                }
        
        # 处理CSV
        ner = NERService()
        output_path = os.path.join(OUTPUT_FOLDER, f"{session_id}_processed.csv")
        success = ner.process_csv(csv_path, output_path)
        
        if not success:
            return jsonify({"error": "CSV processing failed"}), 500
        
        # 读取处理结果
        result_df = pd.read_csv(output_path)
        entities_data = []
        for _, row in result_df.iterrows():
            if row['detected_entities'] and row['detected_entities'] != '[]':
                entities_data.append({
                    "row_index": row.name,
                    "entities": row['detected_entities']
                })
        
        # 跨模态匹配
        matches = []
        if dicom_data:
            for _, row in result_df.iterrows():
                if 'patient_id' in row and dicom_data.get('patient_id'):
                    if str(row['patient_id']) == str(dicom_data['patient_id']):
                        matches.append({
                            "row_index": row.name,
                            "match_type": "patient_id",
                            "confidence": 1.0,
                            "risk_level": "high"
                        })
        
        return jsonify({
            "session_id": session_id,
            "csv_entities": entities_data,
            "dicom_data": dicom_data,
            "cross_modal_matches": matches,
            "total_entities": len(entities_data),
            "total_matches": len(matches),
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

