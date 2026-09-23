from flask import render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app import db
from app.routes.auth import auth_bp
from app.models.user import User
from app.utils.audit import log_action
from app.utils.mail import send_reset_email


# ══════════════════════════════════════════════════════
#  الإعداد الأولي — إنشاء المدير الأول من داخل المنصة
# ══════════════════════════════════════════════════════
@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    lang = session.get('lang', 'ar')

    # إذا كان هناك مدير بالفعل، هذا المسار مغلق نهائياً
    if User.query.filter_by(role='admin').first() is not None:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username      = request.form.get('username', '').strip()
        full_name     = request.form.get('full_name', '').strip()
        email         = request.form.get('email', '').strip()
        password      = request.form.get('password', '')
        confirm       = request.form.get('confirm_password', '')

        if not username or not full_name or not email:
            flash('جميع الحقول إلزامية', 'danger')
            return render_template('auth/setup.html', lang=lang)

        if User.query.filter_by(username=username).first():
            flash('اسم المستخدم مستخدَم بالفعل', 'danger')
            return render_template('auth/setup.html', lang=lang)

        if User.query.filter_by(email=email).first():
            flash('البريد الإلكتروني مستخدَم بالفعل', 'danger')
            return render_template('auth/setup.html', lang=lang)

        if password != confirm:
            flash('كلمة المرور غير متطابقة', 'danger')
            return render_template('auth/setup.html', lang=lang)

        if len(password) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'danger')
            return render_template('auth/setup.html', lang=lang)

        # فحص أمان إضافي: لو أنشأ طلبان متزامنان مديرَين، نمنع الثاني عند الحفظ
        if User.query.filter_by(role='admin').first() is not None:
            flash('تم إنشاء المدير بالفعل من جهة أخرى', 'warning')
            return redirect(url_for('auth.login'))

        user = User(username=username, full_name=full_name,
                    email=email, role='admin', is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        log_action('CREATE', 'users', record_id=user.id, new_data=user.to_dict())
        _complete_login(user)
        flash('تم إنشاء حساب المدير بنجاح، مرحباً بك', 'success')
        return redirect(url_for('auth.dashboard'))

    return render_template('auth/setup.html', lang=lang)


# ══════════════════════════════════════════════════════
#  تسجيل الدخول
# ══════════════════════════════════════════════════════
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    lang = session.get('lang', 'ar')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
            return render_template('auth/login.html', lang=lang)

        if not user.is_active:
            flash('حسابك موقوف. تواصل مع المدير', 'danger')
            return render_template('auth/login.html', lang=lang)

        # ── إذا كان 2FA مفعَّلاً → حفظ user_id في session مؤقتاً ──
        if user.totp_enabled:
            session['2fa_user_id'] = user.id
            session['2fa_next']    = request.args.get('next', '')
            return redirect(url_for('auth.two_factor'))

        # ── دخول مباشر بدون 2FA ──
        _complete_login(user)
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        if user.role == 'citizen':
            return redirect(url_for('citizen.dashboard'))
        return redirect(url_for('auth.dashboard'))

    return render_template('auth/login.html', lang=lang)


# ══════════════════════════════════════════════════════
#  نسيت كلمة المرور — طلب كود تفعيل عبر البريد
# ══════════════════════════════════════════════════════
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    lang = session.get('lang', 'ar')

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first() if email else None

        if user and user.is_active:
            try:
                code = user.generate_reset_code()
                db.session.commit()
                send_reset_email(user, code, lang=lang)
                log_action('UPDATE', 'users', record_id=user.id,
                           new_data={'action': 'password_reset_requested'})
                session['reset_user_id'] = user.id
            except Exception:
                # لا نُظهر تفاصيل الخطأ التقني للمستخدم لأسباب أمنية
                db.session.rollback()

        # رسالة عامة دائماً — لا نكشف هل البريد مسجّل أم لا
        flash(
            'إذا كان البريد الإلكتروني مسجّلاً لدينا، ستصلك رسالة تحتوي كوداً '
            'مكوَّناً من 8 أرقام خلال دقائق' if lang == 'ar' else
            'Si cet e-mail est enregistré, un code à 8 chiffres vous sera envoyé.',
            'info'
        )
        return redirect(url_for('auth.verify_reset_code'))

    return render_template('auth/forgot_password.html', lang=lang)


# ══════════════════════════════════════════════════════
#  إدخال كود التفعيل (8 أرقام) وتعيين كلمة مرور جديدة
# ══════════════════════════════════════════════════════
@auth_bp.route('/verify-reset-code', methods=['GET', 'POST'])
def verify_reset_code():
    lang = session.get('lang', 'ar')

    if request.method == 'POST':
        code      = request.form.get('code', '').strip()
        new_pass  = request.form.get('new_password', '')
        confirm   = request.form.get('confirm_password', '')

        user_id = session.get('reset_user_id')
        user = User.query.get(user_id) if user_id else None

        # رسالة خطأ موحَّدة لعدم كشف أي تفاصيل (كود خاطئ / منتهي / لا يوجد طلب أصلاً)
        invalid_msg = (
            'الكود غير صحيح أو منتهي الصلاحية، اطلب كوداً جديداً' if lang == 'ar'
            else 'Code invalide ou expiré, veuillez en redemander un.'
        )

        if not user or not user.verify_reset_code(code):
            flash(invalid_msg, 'danger')
            return render_template('auth/verify_reset_code.html', lang=lang)

        if new_pass != confirm:
            flash('كلمة المرور غير متطابقة' if lang == 'ar' else 'Les mots de passe ne correspondent pas', 'danger')
            return render_template('auth/verify_reset_code.html', lang=lang)

        if len(new_pass) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل' if lang == 'ar'
                  else 'Le mot de passe doit contenir au moins 6 caractères', 'danger')
            return render_template('auth/verify_reset_code.html', lang=lang)

        user.set_password(new_pass)
        user.clear_reset_code()
        db.session.commit()
        session.pop('reset_user_id', None)
        log_action('UPDATE', 'users', record_id=user.id,
                   new_data={'action': 'password_reset_completed'})
        flash('تم تغيير كلمة المرور بنجاح، يمكنك تسجيل الدخول الآن' if lang == 'ar'
              else 'Mot de passe modifié avec succès, vous pouvez vous connecter.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/verify_reset_code.html', lang=lang)


# ══════════════════════════════════════════════════════
#  صفحة رمز 2FA (بعد كلمة المرور)
# ══════════════════════════════════════════════════════
@auth_bp.route('/2fa', methods=['GET', 'POST'])
def two_factor():
    # يجب أن تكون هناك جلسة مؤقتة من خطوة كلمة المرور
    user_id = session.get('2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        session.pop('2fa_user_id', None)
        return redirect(url_for('auth.login'))

    lang = session.get('lang', 'ar')

    if request.method == 'POST':
        code = request.form.get('otp_code', '').strip().replace(' ', '')

        if user.verify_totp(code):
            session.pop('2fa_user_id', None)
            next_page = session.pop('2fa_next', '')
            _complete_login(user)
            if next_page:
                return redirect(next_page)
            if user.role == 'citizen':
                return redirect(url_for('citizen.dashboard'))
            return redirect(url_for('auth.dashboard'))
        else:
            flash('رمز التحقق غير صحيح أو منتهي الصلاحية', 'danger')

    return render_template('auth/2fa.html', lang=lang)


# ══════════════════════════════════════════════════════
#  إعداد 2FA (تفعيل)
# ══════════════════════════════════════════════════════
@auth_bp.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    lang = session.get('lang', 'ar')

    # توليد مفتاح جديد إن لم يكن موجوداً
    if not current_user.totp_secret:
        current_user.generate_totp_secret()
        db.session.commit()

    if request.method == 'POST':
        code = request.form.get('otp_code', '').strip()

        if current_user.verify_totp(code):
            current_user.totp_enabled = True
            db.session.commit()
            log_action('UPDATE', 'users', record_id=current_user.id,
                       new_data={'action': 'enable_2fa'})
            flash('تم تفعيل التحقق بخطوتين بنجاح ✔', 'success')
            return redirect(url_for('auth.dashboard'))
        else:
            flash('رمز التحقق غير صحيح. تأكد من مزامنة الوقت في التطبيق', 'danger')

    # توليد QR Code بصيغة base64
    qr_uri  = current_user.get_totp_uri()
    qr_b64  = _make_qr_b64(qr_uri)

    return render_template('auth/setup_2fa.html',
                           qr_b64=qr_b64,
                           totp_secret=current_user.totp_secret,
                           lang=lang)


# ══════════════════════════════════════════════════════
#  تعطيل 2FA
# ══════════════════════════════════════════════════════
@auth_bp.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    password = request.form.get('password', '')

    if not current_user.check_password(password):
        flash('كلمة المرور غير صحيحة', 'danger')
        return redirect(url_for('auth.setup_2fa'))

    current_user.totp_enabled = False
    current_user.totp_secret  = None
    db.session.commit()
    log_action('UPDATE', 'users', record_id=current_user.id,
               new_data={'action': 'disable_2fa'})
    flash('تم تعطيل التحقق بخطوتين', 'warning')
    return redirect(url_for('auth.dashboard'))


# ══════════════════════════════════════════════════════
#  لوحة التحكم
# ══════════════════════════════════════════════════════
@auth_bp.route('/dashboard')
@login_required
def dashboard():
    from app.models.birth    import Birth
    from app.models.marriage import Marriage
    from app.models.death    import Death
    from app.models.divorce  import Divorce

    stats = {
        'births':    Birth.query.count(),
        'marriages': Marriage.query.count(),
        'deaths':    Death.query.count(),
        'divorces':  Divorce.query.count(),
    }
    if current_user.role == 'officer' and current_user.center_id:
        stats['births']    = Birth.query.filter_by(center_id=current_user.center_id).count()
        stats['marriages'] = Marriage.query.filter_by(center_id=current_user.center_id).count()
        stats['deaths']    = Death.query.filter_by(center_id=current_user.center_id).count()
        stats['divorces']  = Divorce.query.filter_by(center_id=current_user.center_id).count()

    lang = session.get('lang', 'ar')
    return render_template('auth/dashboard.html', stats=stats, lang=lang)


# ══════════════════════════════════════════════════════
#  تسجيل الخروج
# ══════════════════════════════════════════════════════
@auth_bp.route('/logout')
@login_required
def logout():
    log_action('LOGOUT', 'users', record_id=current_user.id)
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('auth.login'))


# ══════════════════════════════════════════════════════
#  تغيير اللغة
# ══════════════════════════════════════════════════════
@auth_bp.route('/set-lang/<lang>')
def set_lang(lang):
    if lang in ['ar', 'fr']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('auth.dashboard'))


# ══════════════════════════════════════════════════════
#  تغيير كلمة المرور
# ══════════════════════════════════════════════════════
@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    lang = session.get('lang', 'ar')

    if request.method == 'POST':
        current_pass = request.form.get('current_password', '')
        new_pass     = request.form.get('new_password', '')
        confirm_pass = request.form.get('confirm_password', '')

        if not current_user.check_password(current_pass):
            flash('كلمة المرور الحالية غير صحيحة', 'danger')
            return render_template('auth/change_password.html', lang=lang)

        if new_pass != confirm_pass:
            flash('كلمة المرور الجديدة غير متطابقة', 'danger')
            return render_template('auth/change_password.html', lang=lang)

        if len(new_pass) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'danger')
            return render_template('auth/change_password.html', lang=lang)

        current_user.set_password(new_pass)
        db.session.commit()
        log_action('UPDATE', 'users', record_id=current_user.id)
        flash('تم تغيير كلمة المرور بنجاح', 'success')
        return redirect(url_for('auth.dashboard'))

    return render_template('auth/change_password.html', lang=lang)


# ══════════════════════════════════════════════════════
#  دوال مساعدة خاصة
# ══════════════════════════════════════════════════════
def _complete_login(user):
    """إكمال عملية الدخول وتسجيل الوقت"""
    user.last_login = datetime.utcnow()
    db.session.commit()
    login_user(user)
    log_action('LOGIN', 'users', record_id=user.id)


def _make_qr_b64(uri):
    """توليد صورة QR بصيغة base64 من الـ URI"""
    import qrcode
    import base64
    from io import BytesIO
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('utf-8')
