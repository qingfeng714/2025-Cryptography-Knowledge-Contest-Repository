import os
import uuid
import argparse
import re
import secrets
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file
import torch
import pandas as pd
from services.crossmodal_service import CrossModalAttentionService
from services.audit_service import AuditLogger
from services.cleanup_service import CleanupService
from services.protection_service import ProtectionService
from services.storage_audit_service import StorageAuditService
from services.verification_service import VerificationService

def create_app(config=None):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.update(config or {})
    
    # 设置最大文件上传大小为500MB（支持批量上传）
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

    # 初始化服务组件
    app.crossmodal_svc = CrossModalAttentionService(
        device='cuda' if torch.cuda.is_available() else 'cpu'
    )
    app.audit_logger = AuditLogger()
    app.cleanup_service = CleanupService(upload_dir=app.config['UPLOAD_FOLDER'], max_age_hours=24)
    
    # 初始化保护层服务
    app.protection_key = secrets.token_hex(32)  # 生成32字节密钥
    app.protection_svc = ProtectionService(key_hex=app.protection_key)
    
    # 初始化存储服务
    storage_repo = app.config.get('STORAGE_REPO', './storage_repo')
    app.storage_svc = StorageAuditService(repo_path=storage_repo)
    
    # 初始化验证服务
    app.verification_svc = VerificationService()
    
    # 启动定期清理任务（每1小时清理一次）
    app.cleanup_service.start_periodic_cleanup(interval_hours=1)
    print("[INFO] 文件清理服务已启动")
    print(f"[INFO] 保护层密钥提示: {app.protection_key[:16]}...")
    print(f"[INFO] 存储仓库路径: {storage_repo}")

    # 确保目录存在
    os.makedirs(app.config.get('UPLOAD_FOLDER'), exist_ok=True)
    os.makedirs(app.config.get('OUTPUT_DIR'), exist_ok=True)
    
    # 添加请求错误处理
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({'error': '文件太大，最大支持500MB'}), 413
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f'未处理的异常: {str(e)}')
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500

    @app.route("/api/ingest", methods=["POST"])
    def ingest():
        """数据接入端点"""
        try:
            text = request.form.get("text", "")
            # 支持两种参数名：dicom 和 dicom_file
            dicom_file = request.files.get("dicom") or request.files.get("dicom_file")
            
            ingest_id = f"ingest_{uuid.uuid4().hex[:8]}"
            dicom_path = None
            
            if dicom_file:
                dicom_path = str(Path(app.config['UPLOAD_FOLDER']) / f"{ingest_id}.dcm")
                dicom_file.save(dicom_path)
            
            app.audit_logger.log(ingest_id, "ingest", "client")
            return jsonify({
                "file_id": ingest_id,  # 添加file_id字段，与前端一致
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
            # 支持多种ID字段名
            ingest_id = data.get("ingest_id") or data.get("csv_id") or f"detect_{uuid.uuid4().hex[:8]}"
            
            # 获取文件路径或ID
            csv_id = data.get("csv_id")
            dicom_id = data.get("dicom_id")
            csv_path = data.get("csv_path")
            dicom_path = data.get("dicom_path")
            
            # 如果提供的是ID，需要转换为路径
            if csv_id and not csv_path:
                csv_path = str(Path(app.config['UPLOAD_FOLDER']) / f"{csv_id}.csv")
            if dicom_id and not dicom_path:
                dicom_path = str(Path(app.config['UPLOAD_FOLDER']) / f"{dicom_id}.dcm")
            
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
                "entities": result.get("text_entities", []),
                "text_entities": result.get("text_entities", []),  # 添加此字段，与前端一致
                "roi_regions": result.get("image_regions", {}),
                "image_regions": result.get("image_regions", {}),  # 添加此字段
                "mappings": result.get("mappings", []),
                "cross_modal_risks": result.get("cross_modal_risks", []),
                "metrics": result.get("metrics", {}),
                "status": "success"
            })
        except Exception as e:
            error_msg = str(e)
            print(f"检测错误: {error_msg}")
            app.audit_logger.log("system", "detect_error", error_msg)
            return jsonify({"error": error_msg, "status": "error"}), 500

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
            print(f"[DEBUG] 收到CSV上传请求")
            print(f"[DEBUG] request.files: {request.files}")
            print(f"[DEBUG] request.form: {request.form}")
            
            # 支持两种参数名：csv 和 csv_file
            csv_file = request.files.get("csv") or request.files.get("csv_file")
            if not csv_file:
                print(f"[ERROR] 未找到CSV文件")
                return jsonify({"error": "No CSV file provided", "status": "error"}), 400
            
            # 保存CSV文件
            csv_id = f"csv_{uuid.uuid4().hex[:8]}"
            csv_path = str(Path(app.config['UPLOAD_FOLDER']) / f"{csv_id}.csv")
            csv_file.save(csv_path)
            
            print(f"[SUCCESS] CSV文件已保存: {csv_path}")
            app.audit_logger.log(csv_id, "csv_upload", "client")
            
            return jsonify({
                "file_id": csv_id,  # 添加file_id字段，与前端一致
                "csv_id": csv_id,
                "csv_path": csv_path,
                "filename": csv_file.filename,
                "status": "success"
            })
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] CSV上传失败: {error_msg}")
            app.audit_logger.log("system", "csv_upload_error", error_msg)
            return jsonify({"error": error_msg, "status": "error"}), 500

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
    
    @app.route("/api/batch_upload_dicom", methods=["POST"])
    def batch_upload_dicom():
        """批量上传DICOM文件并提取元数据"""
        try:
            dicom_files = request.files.getlist("dicom_files")
            if not dicom_files:
                return jsonify({"error": "No DICOM files provided"}), 400
            
            print(f"[INFO] 收到 {len(dicom_files)} 个DICOM文件")
            
            # 创建DICOM目录
            dicom_id = f"batch_{uuid.uuid4().hex[:8]}"
            dicom_dir = Path(app.config['UPLOAD_FOLDER']) / dicom_id
            dicom_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存DICOM文件并提取元数据
            from services.roi_service import DicomProcessor
            processor = DicomProcessor(device='cpu')
            metadata_list = []
            
            for i, dicom_file in enumerate(dicom_files):
                if not dicom_file.filename.endswith('.dcm'):
                    continue
                    
                # 保存文件
                file_path = dicom_dir / dicom_file.filename
                dicom_file.save(file_path)
                
                # 提取元数据
                try:
                    result = processor.process_dicom(file_path, try_burnedin=False)
                    if result:
                        metadata_list.append({
                            'filename': dicom_file.filename,
                            'filepath': str(file_path).replace('\\', '/'),  # 跨平台路径兼容
                            'patient_id': result.patient_id or '',
                            'patient_sex': result.patient_sex or '',
                            'patient_age': result.patient_age or '',
                            'study_date': result.study_date or '',
                            'accession': result.accession or '',
                            'institution': result.institution or ''
                        })
                        
                    if (i + 1) % 100 == 0:
                        print(f"[INFO] 已处理 {i + 1}/{len(dicom_files)} 个DICOM文件")
                except Exception as e:
                    print(f"[WARN] 处理 {dicom_file.filename} 失败: {e}")
                    continue
            
            print(f"[SUCCESS] 成功提取 {len(metadata_list)} 个DICOM元数据")
            app.audit_logger.log(dicom_id, "batch_dicom_upload", "client")
            
            return jsonify({
                "dicom_id": dicom_id,
                "dicom_dir": str(dicom_dir),
                "total_files": len(dicom_files),
                "processed": len(metadata_list),
                "metadata_list": metadata_list,
                "status": "success"
            })
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] 批量DICOM上传失败: {error_msg}")
            app.audit_logger.log("system", "batch_dicom_error", error_msg)
            return jsonify({"error": error_msg, "status": "error"}), 500

    @app.route("/api/batch_detect", methods=["POST"])
    def batch_detect():
        """批量跨模态检测（CSV + DICOM元数据列表）"""
        try:
            data = request.json
            csv_path = data.get("csv_path")
            dicom_metadata_list = data.get("dicom_metadata_list", [])
            
            if not csv_path:
                return jsonify({"error": "Missing csv_path"}), 400
            
            print(f"[INFO] 批量检测: CSV={csv_path}, DICOM元数据数={len(dicom_metadata_list)}")
            
            # 读取CSV（自动检测编码）
            try:
                df = pd.read_csv(csv_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    print(f"[WARN] UTF-8解码失败，尝试GBK编码...")
                    df = pd.read_csv(csv_path, encoding='gbk')
                except UnicodeDecodeError:
                    print(f"[WARN] GBK解码失败，尝试latin1编码...")
                    df = pd.read_csv(csv_path, encoding='latin1')
            
            # 提取CSV中的patient_id
            csv_patients = []
            for idx, row in df.iterrows():
                path_value = str(row.get('Path', ''))
                match = re.search(r'patient(\d+)', path_value, re.IGNORECASE)
                if match:
                    csv_patients.append({
                        'row_index': idx,
                        'patient_id': 'patient' + match.group(1),
                        'patient_number': match.group(1),
                        'row_data': row.to_dict()
                    })
            
            print(f"[INFO] CSV中找到 {len(csv_patients)} 个patient记录")
            
            # 创建DICOM patient_id索引
            dicom_index = {}
            for dicom_meta in dicom_metadata_list:
                patient_id = dicom_meta.get('patient_id', '')
                if patient_id:
                    dicom_index[patient_id] = dicom_meta
            
            print(f"[INFO] DICOM元数据中找到 {len(dicom_index)} 个patient_id")
            
            # 匹配CSV和DICOM
            matches = []
            matched_count = 0
            
            for csv_patient in csv_patients:
                csv_pid = csv_patient['patient_id']
                dicom_meta = dicom_index.get(csv_pid)
                
                if dicom_meta:
                    matched_count += 1
                    matches.append({
                        'patient_id': csv_pid,
                        'row_index': csv_patient['row_index'],
                        'dicom_file': dicom_meta.get('filename'),
                        'matched': True,
                        'csv_data': csv_patient['row_data'],
                        'dicom_metadata': dicom_meta,
                        'match_type': 'patient_id_exact_match',
                        'confidence': 1.0,
                        'risk_level': 'critical'
                    })
                else:
                    matches.append({
                        'patient_id': csv_pid,
                        'row_index': csv_patient['row_index'],
                        'dicom_file': 'None',
                        'matched': False
                    })
            
            print(f"[SUCCESS] 匹配完成: {matched_count}/{len(csv_patients)}")
            print(f"[DEBUG] matches数组长度: {len(matches)}")
            print(f"[DEBUG] 前3个match: {matches[:3] if len(matches) >= 3 else matches}")
            
            result = {
                'csv_file': Path(csv_path).name,
                'total_patients': len(csv_patients),
                'processed': len(csv_patients),
                'matched': matched_count,
                'unmatched': len(csv_patients) - matched_count,
                'match_rate': (matched_count / len(csv_patients) * 100) if csv_patients else 0,
                'results': matches,
                'status': 'success'
            }
            
            print(f"[DEBUG] result keys: {result.keys()}")
            print(f"[DEBUG] result['results']长度: {len(result['results'])}")
            
            app.audit_logger.log("batch_detect", "complete", f"matched={matched_count}")
            
            # 清理NaN值，转换为JSON安全的格式
            import json
            import numpy as np
            
            def clean_nan(obj):
                """递归清理NaN值"""
                if isinstance(obj, dict):
                    return {k: clean_nan(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_nan(item) for item in obj]
                elif isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
                    return None
                else:
                    return obj
            
            result_cleaned = clean_nan(result)
            return jsonify(result_cleaned)
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] 批量检测失败: {error_msg}")
            import traceback
            traceback.print_exc()
            app.audit_logger.log("batch_detect", "error", error_msg)
            return jsonify({"error": error_msg, "status": "error"}), 500
    
    @app.route("/api/process_batch", methods=["POST"])
    def process_batch():
        """批量处理CSV和DICOM数据（旧接口，保留兼容性）"""
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

    @app.route("/api/protect_execute", methods=["POST"])
    def protect_execute():
        """执行保护操作（批量）"""
        try:
            data = request.json
            detection_result = data.get("detection_result")
            batch_id = data.get("batch_id", f"batch_{uuid.uuid4().hex[:8]}")
            
            if not detection_result:
                return jsonify({"error": "Missing detection_result"}), 400
            
            # 执行保护
            output_dir = Path(app.config['OUTPUT_DIR']) / batch_id
            result = app.protection_svc.protect_batch(
                detection_result=detection_result,
                output_dir=output_dir,
                batch_id=batch_id
            )
            
            app.audit_logger.log(batch_id, "protect_execute", "system")
            return jsonify(result)
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] 保护执行失败: {error_msg}")
            import traceback
            traceback.print_exc()
            app.audit_logger.log("system", "protect_error", error_msg)
            return jsonify({"error": error_msg, "status": "error"}), 500
    
    @app.route("/api/storage/ingest", methods=["POST"])
    def storage_ingest():
        """存储入库"""
        try:
            data = request.json
            batch_id = data.get("batch_id")
            
            if not batch_id:
                return jsonify({"error": "Missing batch_id"}), 400
            
            # 查找保护后的文件
            output_dir = Path(app.config['OUTPUT_DIR']) / batch_id
            protected_dicom = output_dir / "protected_dicom"
            protected_text = output_dir / "protected_text"
            
            if not protected_dicom.exists() or not protected_text.exists():
                return jsonify({"error": "Protected files not found"}), 404
            
            # 入库
            result = app.storage_svc.ingest_batch(
                protected_dicom=protected_dicom,
                protected_text=protected_text,
                batch_id=batch_id
            )
            
            app.audit_logger.log(batch_id, "storage_ingest", "system")
            return jsonify(result)
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] 存储入库失败: {error_msg}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": error_msg, "status": "error"}), 500
    
    @app.route("/api/storage/list", methods=["GET"])
    def storage_list():
        """列出存储的对象"""
        try:
            limit = int(request.args.get("limit", 20))
            offset = int(request.args.get("offset", 0))
            
            objects = app.storage_svc.list_objects(limit=limit, offset=offset)
            return jsonify({"objects": objects, "limit": limit, "offset": offset})
            
        except Exception as e:
            return jsonify({"error": str(e), "status": "error"}), 500
    
    @app.route("/api/storage/batches", methods=["GET"])
    def storage_batches():
        """列出批次"""
        try:
            limit = int(request.args.get("limit", 20))
            batches = app.storage_svc.list_batches(limit=limit)
            return jsonify({"batches": batches, "limit": limit})
            
        except Exception as e:
            return jsonify({"error": str(e), "status": "error"}), 500
    
    @app.route("/api/storage/stats", methods=["GET"])
    def storage_stats():
        """获取存储统计"""
        try:
            stats = app.storage_svc.get_stats()
            return jsonify(stats)
        except Exception as e:
            return jsonify({"error": str(e), "status": "error"}), 500
    
    @app.route("/api/storage/bundle", methods=["POST"])
    def storage_bundle():
        """构建bundle"""
        try:
            data = request.json
            patient_id = data.get("patient_id")
            
            if not patient_id:
                return jsonify({"error": "Missing patient_id"}), 400
            
            # 构建bundle
            bundle_dir = Path(app.config['OUTPUT_DIR']) / "bundles"
            bundle_dir.mkdir(parents=True, exist_ok=True)
            out_zip = bundle_dir / f"{patient_id}_bundle.zip"
            
            success = app.storage_svc.build_bundle(patient_id=patient_id, out_zip=out_zip)
            
            if success:
                return jsonify({
                    "status": "success",
                    "bundle_path": str(out_zip),
                    "patient_id": patient_id
                })
            else:
                return jsonify({"error": "Patient ID not found"}), 404
                
        except Exception as e:
            return jsonify({"error": str(e), "status": "error"}), 500
    
    @app.route("/api/storage/bundle/<patient_id>/download", methods=["GET"])
    def download_bundle(patient_id):
        """下载bundle"""
        try:
            bundle_path = Path(app.config['OUTPUT_DIR']) / "bundles" / f"{patient_id}_bundle.zip"
            
            if not bundle_path.exists():
                return jsonify({"error": "Bundle not found"}), 404
            
            return send_file(
                str(bundle_path),
                as_attachment=True,
                download_name=f"{patient_id}_bundle.zip"
            )
        except Exception as e:
            return jsonify({"error": str(e), "status": "error"}), 500
    
    @app.route("/api/verify/bundle", methods=["POST"])
    def verify_bundle():
        """验证bundle"""
        try:
            data = request.json
            patient_id = data.get("patient_id")
            
            if not patient_id:
                return jsonify({"error": "Missing patient_id"}), 400
            
            bundle_path = Path(app.config['OUTPUT_DIR']) / "bundles" / f"{patient_id}_bundle.zip"
            
            if not bundle_path.exists():
                return jsonify({"error": "Bundle not found"}), 404
            
            result = app.verification_svc.verify_bundle(bundle_path)
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"error": str(e), "status": "error"}), 500
    
    @app.route("/api/verify/repo", methods=["POST"])
    def verify_repo():
        """从仓库验证对象"""
        try:
            data = request.json
            patient_id = data.get("patient_id")
            
            if not patient_id:
                return jsonify({"error": "Missing patient_id"}), 400
            
            repo_path = Path(app.config.get('STORAGE_REPO', './storage_repo'))
            result = app.verification_svc.verify_repo_object(repo_path, patient_id)
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"error": str(e), "status": "error"}), 500
    
    @app.route("/api/key_info", methods=["GET"])
    def key_info():
        """获取密钥信息"""
        import hashlib
        key_hint = hashlib.sha256(bytes.fromhex(app.protection_key)).hexdigest()[:16]
        return jsonify({
            "key_hint": key_hint,
            "key_length": len(app.protection_key),
            "has_ascon": app.protection_svc.__class__.__module__ is not None
        })

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