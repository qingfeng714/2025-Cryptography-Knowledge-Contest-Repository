import os
import uuid
import argparse
from pathlib import Path
from flask import Flask, request, jsonify, render_template
import torch
import pandas as pd
from services.crossmodal_service import CrossModalAttentionService
# 简化导入，去掉加密相关模块
from services.audit_service import AuditLogger

def create_app(config=None):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.update(config or {})

    # 初始化服务组件
    app.crossmodal_svc = CrossModalAttentionService(
        device='cuda' if torch.cuda.is_available() else 'cpu'
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
            csv_path = data.get("csv_path")
            dicom_path = data.get("dicom_path")
            
            # 如果提供了CSV路径，处理CSV文件
            if csv_path:
                result = app.crossmodal_svc.process_csv_detection(csv_path, dicom_path)
                print(f"CSV检测结果: 实体数量={len(result.get('text_entities', []))}")
            else:
                # 兼容原有的文本处理方式
                text = data.get("text", "")
                result = app.crossmodal_svc.detect_phi_mapping(text, dicom_path)
                print(f"文本检测结果: 实体数量={len(result.get('text_entities', []))}")
            
            app.audit_logger.log(ingest_id, "detect", "system")
            
            return jsonify({
                "ingest_id": ingest_id,
                "entities": result["text_entities"],
                "roi_regions": result["image_regions"],
                "mappings": result["mappings"],
                "cross_modal_risks": result["cross_modal_risks"],
                "metrics": result["metrics"],
                "status": "success"
            })
        except Exception as e:
            app.audit_logger.log(ingest_id, "detect_error", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route("/api/protect", methods=["POST"])
    def protect():
        """为下一层提供检测结果接口"""
        try:
            data = request.json
            ingest_id = data["ingest_id"]
            
            # 这里只是示例，实际应该从存储中获取检测结果
            # 为下一层提供标准化的接口
            protection_request = {
                "session_id": ingest_id,
                "detection_complete": True,
                "next_layer_interface": {
                    "text_entities": "已检测的文本实体列表",
                    "dicom_metadata": "已提取的DICOM元数据",
                    "cross_modal_risks": "跨模态风险列表",
                    "roi_regions": "ROI区域信息",
                    "risk_score": "综合风险分数",
                    "protection_recommendations": "保护建议"
                },
                "status": "ready_for_protection_layer"
            }
            
            app.audit_logger.log(ingest_id, "protect_interface", "system")
            return jsonify(protection_request)
        except Exception as e:
            app.audit_logger.log(ingest_id, "protect_error", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route("/api/upload_csv", methods=["POST"])
    def upload_csv():
        """上传CSV文件"""
        try:
            csv_file = request.files.get("csv")
            if not csv_file:
                return jsonify({"error": "No CSV file provided"}), 400
            
            # 保存CSV文件
            csv_id = f"csv_{uuid.uuid4().hex[:8]}"
            csv_path = str(Path(app.config['UPLOAD_FOLDER']) / f"{csv_id}.csv")
            csv_file.save(csv_path)
            
            app.audit_logger.log(csv_id, "csv_upload", "client")
            return jsonify({
                "csv_id": csv_id,
                "csv_path": csv_path,
                "status": "success"
            })
        except Exception as e:
            app.audit_logger.log("system", "csv_upload_error", str(e))
            return jsonify({"error": str(e)}), 500

    @app.route("/api/upload_dicom", methods=["POST"])
    def upload_dicom():
        """上传DICOM文件目录"""
        try:
            dicom_files = request.files.getlist("dicom_files")
            if not dicom_files:
                return jsonify({"error": "No DICOM files provided"}), 400
            
            # 创建DICOM目录
            dicom_id = f"dicom_{uuid.uuid4().hex[:8]}"
            dicom_dir = Path(app.config['UPLOAD_FOLDER']) / dicom_id
            dicom_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存DICOM文件
            for dicom_file in dicom_files:
                if dicom_file.filename.endswith('.dcm'):
                    dicom_file.save(dicom_dir / dicom_file.filename)
            
            app.audit_logger.log(dicom_id, "dicom_upload", "client")
            return jsonify({
                "dicom_id": dicom_id,
                "dicom_dir": str(dicom_dir),
                "file_count": len(dicom_files),
                "status": "success"
            })
        except Exception as e:
            app.audit_logger.log("system", "dicom_upload_error", str(e))
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

            # 使用跨模态服务进行批量处理
            result = app.crossmodal_svc.process_batch_data(
                csv_path=csv_path,
                dicom_dir=dicom_dir,
                output_path=str(Path(app.config['OUTPUT_DIR']) / f"batch_{uuid.uuid4().hex[:8]}")
            )
            
            app.audit_logger.log("batch", "process_complete", "system")
            return jsonify(result)
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
    parser.add_argument('--upload-folder', default='./uploads', help='文件上传目录')
    parser.add_argument('--output-dir', default='./output', help='结果输出目录')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    app = create_app({
        'UPLOAD_FOLDER': args.upload_folder,
        'OUTPUT_DIR': args.output_dir
    })
    app.run(host=args.host, port=args.port)