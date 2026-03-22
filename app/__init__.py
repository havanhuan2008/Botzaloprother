import json

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .config import Config
from .extensions import db, login_manager
from .models import AdminUser, AutoReplyRule, MessageLog
from .services import process_incoming_message
from .zalo import extract_message_data, validate_webhook_signature


MATCH_TYPES = {
    'contains': 'Chứa từ khóa',
    'exact': 'Khớp chính xác',
    'starts_with': 'Bắt đầu bằng',
    'fallback': 'Mặc định khi không khớp',
}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_admin_exists(app)
        seed_default_rule()

    register_routes(app)
    return app



def ensure_admin_exists(app: Flask):
    if AdminUser.query.count() == 0:
        user = AdminUser(username=app.config['ADMIN_USERNAME'])
        user.set_password(app.config['ADMIN_PASSWORD'])
        db.session.add(user)
        db.session.commit()



def seed_default_rule():
    if AutoReplyRule.query.count() == 0:
        fallback = AutoReplyRule(
            name='Mặc định',
            match_type='fallback',
            keyword='',
            reply_text='Cảm ơn bạn đã nhắn tin. Admin sẽ phản hồi sớm nhất có thể.',
            priority=999,
            is_active=True,
        )
        db.session.add(fallback)
        db.session.commit()



def register_routes(app: Flask):
    @app.context_processor
    def inject_globals():
        return {
            'match_types': MATCH_TYPES,
        }

    @app.route('/')
    def index():
        total_rules = AutoReplyRule.query.count()
        active_rules = AutoReplyRule.query.filter_by(is_active=True).count()
        total_logs = MessageLog.query.count()
        return render_template('index.html', total_rules=total_rules, active_rules=active_rules, total_logs=total_logs)

    @app.route('/healthz')
    def healthz():
        return {'ok': True}

    @app.route('/webhook/zalo', methods=['GET', 'POST'])
    def webhook_zalo():
        if request.method == 'GET':
            return {'ok': True, 'message': 'Webhook endpoint is live'}

        raw_body = request.get_data() or b'{}'
        if not validate_webhook_signature(raw_body, dict(request.headers)):
            return {'ok': False, 'message': 'Invalid signature'}, 401

        payload = request.get_json(silent=True) or {}
        data = extract_message_data(payload)
        result = process_incoming_message(data['user_id'], data['text'], data['raw'])
        return {'ok': True, 'result': result}

    @app.route('/admin/setup', methods=['GET', 'POST'])
    def setup_admin():
        if AdminUser.query.count() > 0:
            return redirect(url_for('login'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            if not username or not password:
                flash('Tên đăng nhập và mật khẩu là bắt buộc.', 'danger')
                return redirect(url_for('setup_admin'))
            user = AdminUser(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Tạo tài khoản admin thành công.', 'success')
            return redirect(url_for('login'))

        return render_template('admin/setup.html')

    @app.route('/admin/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('admin_dashboard'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            user = AdminUser.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash('Đăng nhập thành công.', 'success')
                return redirect(url_for('admin_dashboard'))
            flash('Sai tài khoản hoặc mật khẩu.', 'danger')

        return render_template('admin/login.html')

    @app.route('/admin/logout', methods=['POST'])
    @login_required
    def logout():
        logout_user()
        flash('Đã đăng xuất.', 'info')
        return redirect(url_for('login'))

    @app.route('/admin')
    @login_required
    def admin_dashboard():
        total_rules = AutoReplyRule.query.count()
        active_rules = AutoReplyRule.query.filter_by(is_active=True).count()
        fallback_rules = AutoReplyRule.query.filter_by(match_type='fallback').count()
        total_logs = MessageLog.query.count()
        recent_logs = MessageLog.query.order_by(MessageLog.created_at.desc()).limit(10).all()
        rules = AutoReplyRule.query.order_by(AutoReplyRule.priority.asc(), AutoReplyRule.id.asc()).all()
        return render_template(
            'admin/dashboard.html',
            total_rules=total_rules,
            active_rules=active_rules,
            fallback_rules=fallback_rules,
            total_logs=total_logs,
            recent_logs=recent_logs,
            rules=rules,
        )

    @app.route('/admin/rules/new', methods=['GET', 'POST'])
    @login_required
    def create_rule():
        if request.method == 'POST':
            rule = AutoReplyRule(
                name=request.form.get('name', '').strip(),
                match_type=request.form.get('match_type', 'contains').strip(),
                keyword=request.form.get('keyword', '').strip(),
                reply_text=request.form.get('reply_text', '').strip(),
                priority=int(request.form.get('priority', '100') or 100),
                is_active=request.form.get('is_active') == 'on',
            )
            db.session.add(rule)
            db.session.commit()
            flash('Đã tạo rule trả lời tự động.', 'success')
            return redirect(url_for('admin_dashboard'))
        return render_template('admin/rule_form.html', rule=None)

    @app.route('/admin/rules/<int:rule_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_rule(rule_id: int):
        rule = AutoReplyRule.query.get_or_404(rule_id)
        if request.method == 'POST':
            rule.name = request.form.get('name', '').strip()
            rule.match_type = request.form.get('match_type', 'contains').strip()
            rule.keyword = request.form.get('keyword', '').strip()
            rule.reply_text = request.form.get('reply_text', '').strip()
            rule.priority = int(request.form.get('priority', '100') or 100)
            rule.is_active = request.form.get('is_active') == 'on'
            db.session.commit()
            flash('Đã cập nhật rule.', 'success')
            return redirect(url_for('admin_dashboard'))
        return render_template('admin/rule_form.html', rule=rule)

    @app.route('/admin/rules/<int:rule_id>/delete', methods=['POST'])
    @login_required
    def delete_rule(rule_id: int):
        rule = AutoReplyRule.query.get_or_404(rule_id)
        db.session.delete(rule)
        db.session.commit()
        flash('Đã xóa rule.', 'warning')
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/logs')
    @login_required
    def admin_logs():
        logs = MessageLog.query.order_by(MessageLog.created_at.desc()).limit(200).all()
        return render_template('admin/logs.html', logs=logs)

    @app.route('/admin/test-send', methods=['POST'])
    @login_required
    def admin_test_send():
        user_id = request.form.get('user_id', '').strip()
        text = request.form.get('text', '').strip()
        if not user_id or not text:
            flash('Cần nhập user_id và nội dung tin nhắn.', 'danger')
            return redirect(url_for('admin_dashboard'))
        from .zalo import ZaloClient

        result = ZaloClient().send_text_message(user_id, text)
        if result.get('ok'):
            flash('Gửi tin test thành công.', 'success')
        else:
            preview = json.dumps(result.get('body', {}), ensure_ascii=False)
            flash(f'Gửi test thất bại: {preview}', 'danger')
        return redirect(url_for('admin_dashboard'))
