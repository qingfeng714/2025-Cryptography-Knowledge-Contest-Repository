# services/audit_service.py

def logAction(ingest_id, action_type, user):
    """
    占位日志函数
    ingest_id: 数据 ID
    action_type: 操作类型，如 'ingest'、'protect'
    user: 操作者
    """
    print(f"[AUDIT] ingest_id={ingest_id}, action={action_type}, user={user}")
    # 如果以后要写入数据库或文件，可在这里扩展
    return True
