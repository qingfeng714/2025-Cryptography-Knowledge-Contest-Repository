import os
import uuid
import argparse
from pathlib import Path
from flask import Flask, request, jsonify, render_template
import torch
import pandas as pd
from services.crossmodal_service import CrossModalAttentionService
from services.crypto_processor import HybridCryptoProcessor
from services.policy_engine import PolicyEngine
from services.storage_service import StorageService
from services.audit_service import AuditLogger

def create_app(config=None):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.update(config or {})

    # 初始化服务组件
    app.crossmodal_svc = CrossModalAttentionService(
        device='cuda' if torch.cuda.is_available() else 'cpu'
    )
    app.crypto_processor = HybridCryptoProcessor(
        kms_endpoint=app.config.get('KMS_ENDPOINT')
    )
    app.policy_engine = PolicyEngine(
        config_path=app.config.get('POLICY_CONFIG')
    )
    app.storage_svc = StorageService(
        output_dir=app.config.get('OUTPUT_DIR')
    )
    app.audit_logger = AuditLogger()

    # 确保上传目录存在
    os.makedirs(app.config.get('UPLOAD_FOLDER'), exist_ok=True)

    @app.route("/api/ingest", methods=["POST"])
    def ingest():
        """数据接入端点"""
        try:
            text = request.form.get("text", "")
            dicom_file = request.files.get("dicom")
            
            ingest_id = f"ingest_{uuid.uuid4().hex[:8]}"
            dicom_path = None
            
            if dicom_file:
                dicom_path = str(Path(app.config['UPLOAD_FOLDER']) / f"{ingest_id}.dcm")
                dicom_file.save(dicom_path)
            
            app.audit_logger.log(ingest_id, "ingest", "client")
            return jsonify({
                "ingest_id": ingest_id,
                "dicom_path": dicom_path,
                "status": "success"
            })
        except Exception as e:
            app.audit_logger.log("system", "ingest_error", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route("/api/detect", methods=["POST"])
    def detect():
        """跨模态敏感信息检测"""
        try:
            data = request.json
            ingest_id = data["ingest_id"]
            text = data["text"]
            dicom_path = data.get("dicom_path")
            
            result = app.crossmodal_svc.detect_phi_mapping(text, dicom_path)
            app.storage_svc.save_detection(ingest_id, result)
            app.audit_logger.log(ingest_id, "detect", "system")
            
            return jsonify({
                "ingest_id": ingest_id,
                "entities": result["text_entities"],
                "roi_regions": result["image_regions"],
                "status": "success"
            })
        except Exception as e:
            app.audit_logger.log(ingest_id, "detect_error", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route("/api/protect", methods=["POST"])
    def protect():
        """数据脱敏处理"""
        try:
            data = request.json
            ingest_id = data["ingest_id"]
            text = data["text"]
            dicom_path = data.get("dicom_path")
            
            detection = app.storage_svc.get_detection(ingest_id)
            if not detection:
                return jsonify({"error": "Detection result not found"}), 404
            
            policy = app.policy_engine.decide_protection(detection["text_entities"])
            protected_text = text
            
            for entity in detection["text_entities"]:
                if policy[entity["entity_id"]]["action"] == "FPE":
                    protected_text = protected_text.replace(
                        entity["text"],
                        app.crypto_processor.fpe_transform(
                            entity["text"], 
                            entity["type"]
                        )
                    )
            
            protected_dicom = None
            if dicom_path:
                protected_dicom = app.crypto_processor.protect_dicom(
                    dicom_path,
                    detection["image_regions"]["roi_mask"]
                )
            
            artifact_id = app.storage_svc.save_artifact(
                ingest_id, 
                {
                    "text": protected_text,
                    "dicom": protected_dicom
                }
            )
            
            app.audit_logger.log(artifact_id, "protect", "system")
            return jsonify({
                "artifact_id": artifact_id,
                "protected_text": protected_text,
                "status": "success"
            })
        except Exception as e:
            app.audit_logger.log(ingest_id, "protect_error", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route("/api/process_batch", methods=["POST"])
    def process_batch():
        """批量处理CSV和DICOM数据"""
        try:
            data = request.json
            csv_path = data.get("csv_path")
            dicom_dir = data.get("dicom_dir")
            
            if not csv_path or not dicom_dir:
                return jsonify({"error": "Missing csv_path or dicom_dir"}), 400

            df = pd.read_csv(csv_path)
            results = []
            
            for _, row in df.iterrows():
                dicom_path = Path(dicom_dir) / f"{row['dicom_id']}.dcm"
                if not dicom_path.exists():
                    continue
                
                result = app.crossmodal_svc.detect_phi_mapping(
                    text=row['report_text'],
                    dicom_path=str(dicom_path)
                )
                
                case_id = f"case_{uuid.uuid4().hex[:8]}"
                app.storage_svc.save_detection(case_id, result)
                results.append({
                    "case_id": case_id,
                    "dicom_id": row['dicom_id'],
                    "entities": result["text_entities"]
                })
            
            return jsonify({
                "processed_count": len(results),
                "results": results,
                "status": "success"
            })
        except Exception as e:
            app.audit_logger.log("batch", "process_error", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route("/")
    def index():
        return render_template("index.html")

    return app

def parse_args():
    """命令行参数解析"""
    parser = argparse.ArgumentParser(description='医疗隐私保护API服务')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=5000, help='监听端口')
    parser.add_argument('--upload-folder', required=True, help='文件上传目录')
    parser.add_argument('--kms-endpoint', required=True, help='KMS服务地址')
    parser.add_argument('--policy-config', required=True, help='策略配置文件路径')
    parser.add_argument('--output-dir', required=True, help='结果输出目录')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    app = create_app({
        'UPLOAD_FOLDER': args.upload_folder,
        'KMS_ENDPOINT': args.kms_endpoint,
        'POLICY_CONFIG': args.policy_config,
        'OUTPUT_DIR': args.output_dir
    })
    app.run(host=args.host, port=args.port)