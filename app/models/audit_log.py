from app import db
from datetime import datetime

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action     = db.Column(db.Text, nullable=False)  # CREATE/UPDATE/DELETE/EXPORT
    table_name = db.Column(db.Text, nullable=False)
    record_id  = db.Column(db.Integer, nullable=True)
    old_data   = db.Column(db.Text, nullable=True)   # JSON
    new_data   = db.Column(db.Text, nullable=True)   # JSON
    ip_address = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AuditLog {self.action} on {self.table_name} by user {self.user_id}>'
