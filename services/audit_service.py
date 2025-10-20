from datetime import datetime

def logAction(resource_id, action_type, actor):
    """模拟审计日志记录"""
    timestamp = datetime.now().isoformat()
    print(f"[AUDIT] {timestamp} - {action_type} action on {resource_id} by {actor}")