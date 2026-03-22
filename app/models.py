from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


class AdminUser(UserMixin, db.Model):
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))


class AutoReplyRule(db.Model):
    __tablename__ = 'auto_reply_rules'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    match_type = db.Column(db.String(20), nullable=False, default='contains')
    keyword = db.Column(db.String(255), nullable=True)
    reply_text = db.Column(db.Text, nullable=False)
    priority = db.Column(db.Integer, default=100, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def matches(self, incoming_text: str) -> bool:
        if not self.is_active:
            return False

        text = (incoming_text or '').strip().lower()
        keyword = (self.keyword or '').strip().lower()

        if self.match_type == 'fallback':
            return True
        if self.match_type == 'exact':
            return text == keyword
        if self.match_type == 'starts_with':
            return text.startswith(keyword)
        return keyword in text


class MessageLog(db.Model):
    __tablename__ = 'message_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=True)
    incoming_text = db.Column(db.Text, nullable=True)
    matched_rule_name = db.Column(db.String(120), nullable=True)
    reply_text = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, default='received')
    raw_payload = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
