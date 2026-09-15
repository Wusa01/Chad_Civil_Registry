import json
from flask import request
from flask_login import current_user
from app import db
from app.models.audit_log import AuditLog

def log_action(action, table_name, record_id=None, old_data=None, new_data=None):
    """
    تسجيل كل عملية في سجل المراقبة
    action: CREATE / UPDATE / DELETE / EXPORT / LOGIN / LOGOUT
    """
    log = AuditLog(
        user_id    = current_user.id if current_user.is_authenticated else None,
        action     = action,
        table_name = table_name,
        record_id  = record_id,
        old_data   = json.dumps(old_data,  ensure_ascii=False) if old_data  else None,
        new_data   = json.dumps(new_data,  ensure_ascii=False) if new_data  else None,
        ip_address = request.remote_addr
    )
    db.session.add(log)
    try:
        db.session.commit()
    except Exception:
        db.session.flush()
