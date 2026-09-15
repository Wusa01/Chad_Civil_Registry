from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(*roles):
    """
    التحقق من صلاحية المستخدم
    مثال: @role_required('admin', 'region_mgr')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def center_required(f):
    """
    التحقق من أن الموظف ينتمي لمركز
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role == 'officer' and not current_user.center_id:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def active_required(f):
    """
    التحقق من أن الحساب مفعّل
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_active:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
