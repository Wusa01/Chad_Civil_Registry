import json
from functools import wraps
from flask import (render_template, redirect, url_for,
                   request, flash, session, send_file)
from flask_login import login_required, current_user, login_user, logout_user
from datetime import datetime
from app import db
from app.routes.citizen import citizen_bp
from app.models.citizen_request import CitizenRequest
from app.models.document import Document
from app.models.birth import Birth
from app.models.marriage import Marriage
from app.models.death import Death
from app.models.divorce import Divorce
from app.models.center import Center
from app.models.user import User
from app.utils.audit import log_action
from app.utils.decorators import role_required
from app.utils.qr_gen import generate_qr_token


# ─────────────────────────────────────────────
#  مساعد: تحقق أن المستخدم مواطن مُسجَّل دخول
# ─────────────────────────────────────────────
def citizen_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'citizen':
            flash('هذه الصفحة للمواطنين المسجلين فقط', 'warning')
            return redirect(url_for('citizen.login'))
        return f(*args, **kwargs)
    return decorated


# ==================== صفحة البداية (عامة) ====================
@citizen_bp.route('/')
def portal():
    if current_user.is_authenticated and current_user.role == 'citizen':
        return redirect(url_for('citizen.dashboard'))
    lang = session.get('lang', 'ar')
    return render_template('citizen/portal.html', lang=lang)


# ==================== تسجيل الدخول بالـ NNI ====================
@citizen_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and current_user.role == 'citizen':
        return redirect(url_for('citizen.dashboard'))

    lang = session.get('lang', 'ar')

    if request.method == 'POST':
        nni      = request.form.get('nni', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(nni=nni, role='citizen').first()

        if not user or not user.check_password(password):
            flash('الرقم الوطني أو كلمة المرور غير صحيحة', 'danger')
            return render_template('citizen/login.html', lang=lang)

        if not user.is_active:
            flash('حسابك موقوف. تواصل مع مركز الحالة المدنية', 'danger')
            return render_template('citizen/login.html', lang=lang)

        user.last_login = datetime.utcnow()
        db.session.commit()
        login_user(user)
        log_action('LOGIN', 'users', record_id=user.id)
        return redirect(url_for('citizen.dashboard'))

    return render_template('citizen/login.html', lang=lang)


# ==================== تسجيل مواطن جديد ====================
@citizen_bp.route('/register', methods=['GET', 'POST'])
def register():
    lang = session.get('lang', 'ar')

    if request.method == 'POST':
        nni       = request.form.get('nni', '').strip()
        full_name = request.form.get('full_name', '').strip()
        password  = request.form.get('password', '')
        confirm   = request.form.get('confirm_password', '')

        if not nni or not full_name or not password:
            flash('جميع الحقول إلزامية', 'danger')
            return render_template('citizen/register.html', lang=lang)

        if password != confirm:
            flash('كلمة المرور غير متطابقة', 'danger')
            return render_template('citizen/register.html', lang=lang)

        if len(password) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'danger')
            return render_template('citizen/register.html', lang=lang)

        if User.query.filter_by(nni=nni).first():
            flash('هذا الرقم الوطني مسجل مسبقاً', 'danger')
            return render_template('citizen/register.html', lang=lang)

        try:
            citizen = User(
                username  = f'citizen_{nni}',
                full_name = full_name,
                role      = 'citizen',
                nni       = nni,
                is_active = True,
            )
            citizen.set_password(password)
            db.session.add(citizen)
            db.session.commit()
            flash('تم إنشاء حسابك بنجاح. يمكنك تسجيل الدخول الآن', 'success')
            return redirect(url_for('citizen.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

    return render_template('citizen/register.html', lang=lang)


# ==================== تسجيل الخروج ====================
@citizen_bp.route('/logout')
@login_required
def logout():
    log_action('LOGOUT', 'users', record_id=current_user.id)
    logout_user()
    return redirect(url_for('citizen.portal'))


# ==================== لوحة التحكم ====================
@citizen_bp.route('/dashboard')
@citizen_required
def dashboard():
    requests_list = CitizenRequest.query.filter_by(
        citizen_id=current_user.id
    ).order_by(CitizenRequest.created_at.desc()).limit(10).all()

    stats = {
        'pending':  CitizenRequest.query.filter_by(
            citizen_id=current_user.id, status='pending').count(),
        'approved': CitizenRequest.query.filter_by(
            citizen_id=current_user.id, status='approved').count(),
        'rejected': CitizenRequest.query.filter_by(
            citizen_id=current_user.id, status='rejected').count(),
    }

    lang = session.get('lang', 'ar')
    return render_template('citizen/dashboard.html',
                           requests=requests_list, stats=stats, lang=lang)


# ==================== تقديم طلب جديد ====================
@citizen_bp.route('/new-request', methods=['GET', 'POST'])
@citizen_required
def new_request():
    centers = Center.query.filter_by(is_active=True).all()
    lang    = session.get('lang', 'ar')

    if request.method == 'POST':
        doc_type     = request.form.get('doc_type', '')
        request_type = request.form.get('request_type', 'new_certificate')
        relationship = request.form.get('relationship', '').strip()
        center_id    = request.form.get('center_id', type=int)

        if not doc_type or not center_id or not relationship:
            flash('يرجى تعبئة جميع الحقول الإلزامية', 'danger')
            return render_template(
                'citizen/new_request.html',
                centers=centers,
                doc_type=doc_type,
                request_type=request_type,
                lang=lang
            )

        data = {k: v for k, v in request.form.items()
                if k != 'csrf_token' and v}

        try:
            cr = CitizenRequest(
                citizen_id   = current_user.id,
                center_id    = center_id,
                doc_type     = doc_type,
                request_type = request_type,
                relationship = relationship,
                status       = 'pending',
                request_data = json.dumps(data, ensure_ascii=False),
            )
            db.session.add(cr)
            db.session.commit()
            log_action('CREATE', 'citizen_requests', record_id=cr.id)
            flash('تم إرسال طلبك بنجاح. سيتم مراجعته من قِبَل الموظف المختص', 'success')
            return redirect(url_for('citizen.track_request', req_id=cr.id))
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

    doc_type     = request.args.get('doc_type', 'birth')
    request_type = request.args.get('request_type', 'new_certificate')
    return render_template('citizen/new_request.html',
                           centers=centers,
                           doc_type=doc_type,
                           request_type=request_type,
                           lang=lang)


# ==================== تتبع طلب محدد ====================
@citizen_bp.route('/track/<int:req_id>')
@citizen_required
def track_request(req_id):
    cr = CitizenRequest.query.get_or_404(req_id)

    if cr.citizen_id != current_user.id:
        flash('ليس لديك صلاحية لعرض هذا الطلب', 'danger')
        return redirect(url_for('citizen.dashboard'))

    lang = session.get('lang', 'ar')
    return render_template('citizen/track_request.html', cr=cr, lang=lang)


# ==================== تصدير الوثيقة (بعد القبول) ====================
@citizen_bp.route('/download/<int:req_id>')
@citizen_required
def download_doc(req_id):
    cr = CitizenRequest.query.get_or_404(req_id)

    if cr.citizen_id != current_user.id:
        flash('ليس لديك صلاحية', 'danger')
        return redirect(url_for('citizen.dashboard'))

    if cr.status != 'approved':
        flash('الوثيقة غير متاحة بعد', 'warning')
        return redirect(url_for('citizen.track_request', req_id=req_id))

    if not cr.issued_doc_id:
        flash('لم يتم ربط وثيقة بهذا الطلب بعد. تواصل مع المركز', 'warning')
        return redirect(url_for('citizen.track_request', req_id=req_id))

    document = Document.query.get_or_404(cr.issued_doc_id)
    log_action('EXPORT', 'citizen_requests', record_id=cr.id)

    try:
        if cr.doc_type == 'birth':
            from app.utils.pdf_gen import generate_birth_pdf
            record = Birth.query.get_or_404(document.ref_id)
            buf    = generate_birth_pdf(record, document)
            fname  = f'birth_{record.certificate_number}.pdf'

        elif cr.doc_type == 'marriage':
            from app.utils.pdf_gen import generate_marriage_pdf
            record = Marriage.query.get_or_404(document.ref_id)
            buf    = generate_marriage_pdf(record, document)
            fname  = f'marriage_{record.certificate_number}.pdf'

        elif cr.doc_type == 'death':
            from app.utils.pdf_gen import generate_death_pdf
            record = Death.query.get_or_404(document.ref_id)
            buf    = generate_death_pdf(record, document)
            fname  = f'death_{record.certificate_number}.pdf'

        elif cr.doc_type == 'divorce':
            from app.utils.pdf_gen import generate_divorce_pdf
            record = Divorce.query.get_or_404(document.ref_id)
            buf    = generate_divorce_pdf(record, document)
            fname  = f'divorce_{record.certificate_number}.pdf'

        else:
            flash('نوع وثيقة غير معروف', 'danger')
            return redirect(url_for('citizen.dashboard'))

        return send_file(buf, mimetype='application/pdf',
                         as_attachment=False, download_name=fname)

    except Exception as e:
        flash(f'حدث خطأ أثناء توليد الوثيقة: {str(e)}', 'danger')
        return redirect(url_for('citizen.track_request', req_id=req_id))


# ─────────────────────────────────────────────
#  واجهة الموظف: قائمة طلبات المواطنين
# ─────────────────────────────────────────────
@citizen_bp.route('/officer/requests')
@login_required
@role_required('officer', 'region_mgr', 'admin')
def officer_requests():
    status = request.args.get('status', 'pending')
    page   = request.args.get('page', 1, type=int)

    query = CitizenRequest.query

    if current_user.role == 'officer':
        query = query.filter_by(center_id=current_user.center_id)
    elif current_user.role == 'region_mgr':
        if current_user.center_id and current_user.center:
            ids = [c.id for c in Center.query.filter_by(
                region=current_user.center.region).all()]
        else:
            ids = []
        query = query.filter(CitizenRequest.center_id.in_(ids))

    if status in ('pending', 'approved', 'rejected'):
        query = query.filter_by(status=status)

    requests_page = query.order_by(
        CitizenRequest.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    lang = session.get('lang', 'ar')
    return render_template('citizen/officer_requests.html',
                           requests_page=requests_page,
                           status=status, lang=lang)


# ─────────────────────────────────────────────
#  واجهة الموظف: مراجعة طلب محدد
# ─────────────────────────────────────────────
@citizen_bp.route('/officer/requests/<int:req_id>', methods=['GET', 'POST'])
@login_required
@role_required('officer', 'region_mgr', 'admin')
def officer_review(req_id):
    cr   = CitizenRequest.query.get_or_404(req_id)
    lang = session.get('lang', 'ar')
    data = json.loads(cr.request_data) if cr.request_data else {}

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'approve':
            cr.status      = 'approved'
            cr.reviewed_by = current_user.id
            cr.reviewed_at = datetime.utcnow()

            req_data = json.loads(cr.request_data) if cr.request_data else {}
            found_record = None

            # ─── الحالة 1: طلب شهادة جديدة ─── إنشاء السجل من بيانات الطلب
            if cr.request_type == 'new_certificate':
                from app.utils.helpers import generate_certificate_number
                center = cr.center

                if not center:
                    db.session.rollback()
                    flash('خطأ: لا يوجد مركز مرتبط بالطلب', 'danger')
                    return redirect(url_for('citizen.officer_requests'))

                try:
                    if cr.doc_type == 'birth':
                        cert_num = generate_certificate_number('birth', center.code)
                        def _parse_date(val):
                            if not val: return None
                            try: return datetime.strptime(val, '%Y-%m-%d').date()
                            except: return None
                        found_record = Birth(
                            certificate_number = cert_num,
                            center_id          = center.id,
                            registration_date  = _parse_date(req_data.get('registration_date')) or datetime.utcnow().date(),
                            child_full_name    = req_data.get('child_full_name', '').strip(),
                            child_gender       = req_data.get('child_gender', 'M'),
                            birth_date         = _parse_date(req_data.get('birth_date')) or datetime.utcnow().date(),
                            birth_place        = req_data.get('birth_place', '').strip(),
                            father_full_name   = req_data.get('father_full_name', '').strip(),
                            father_profession  = req_data.get('father_profession', '').strip(),
                            father_birth_date  = _parse_date(req_data.get('father_birth_date')),
                            father_birth_place = req_data.get('father_birth_place', '').strip() or None,
                            mother_full_name   = req_data.get('mother_full_name', '').strip(),
                            mother_profession  = req_data.get('mother_profession', '').strip(),
                            mother_birth_date  = _parse_date(req_data.get('mother_birth_date')),
                            mother_birth_place = req_data.get('mother_birth_place', '').strip() or None,
                            witness1_name      = req_data.get('witness1_name', '').strip() or None,
                            witness1_id        = req_data.get('witness1_id', '').strip() or None,
                            witness1_relation  = req_data.get('witness1_relation', '').strip() or None,
                            witness2_name      = req_data.get('witness2_name', '').strip() or None,
                            witness2_id        = req_data.get('witness2_id', '').strip() or None,
                            witness2_relation  = req_data.get('witness2_relation', '').strip() or None,
                            civil_officer      = req_data.get('civil_officer', current_user.full_name).strip(),
                            registered_by      = current_user.id,
                        )
                        db.session.add(found_record)
                        db.session.flush()

                    elif cr.doc_type == 'marriage':
                        cert_num = generate_certificate_number('marriage', center.code)
                        def _parse_date(val):
                            if not val: return None
                            try: return datetime.strptime(val, '%Y-%m-%d').date()
                            except: return None
                        found_record = Marriage(
                            certificate_number  = cert_num,
                            center_id           = center.id,
                            registration_date   = _parse_date(req_data.get('registration_date')) or datetime.utcnow().date(),
                            marriage_date       = _parse_date(req_data.get('marriage_date')) or datetime.utcnow().date(),
                            marriage_place      = req_data.get('marriage_place', '').strip(),
                            marriage_type       = req_data.get('marriage_type', 'monogamy'),
                            dowry_mentioned     = bool(req_data.get('dowry_amount')),
                            dowry_amount        = float(req_data['dowry_amount']) if req_data.get('dowry_amount') else None,
                            age_dispensation    = bool(req_data.get('age_dispensation')),
                            husband_full_name   = req_data.get('husband_full_name', '').strip(),
                            husband_birth_date  = _parse_date(req_data.get('husband_birth_date')) or datetime.utcnow().date(),
                            husband_birth_place = req_data.get('husband_birth_place', '—').strip(),
                            husband_profession  = req_data.get('husband_profession', '—').strip(),
                            husband_nationality = req_data.get('husband_nationality', '—').strip(),
                            husband_id_number   = req_data.get('husband_id_number', '—').strip(),
                            husband_father_name = req_data.get('husband_father_name', '—').strip(),
                            husband_mother_name = req_data.get('husband_mother_name', '—').strip(),
                            wife_full_name      = req_data.get('wife_full_name', '').strip(),
                            wife_birth_date     = _parse_date(req_data.get('wife_birth_date')) or datetime.utcnow().date(),
                            wife_birth_place    = req_data.get('wife_birth_place', '—').strip(),
                            wife_profession     = req_data.get('wife_profession', '—').strip(),
                            wife_nationality    = req_data.get('wife_nationality', '—').strip(),
                            wife_id_number      = req_data.get('wife_id_number', '—').strip(),
                            wife_father_name    = req_data.get('wife_father_name', '—').strip(),
                            wife_mother_name    = req_data.get('wife_mother_name', '—').strip(),
                            witness1_name       = req_data.get('witness1_name', '—').strip(),
                            witness1_id         = req_data.get('witness1_id', '—').strip(),
                            witness1_relation   = req_data.get('witness1_relation', '').strip() or None,
                            witness2_name       = req_data.get('witness2_name', '—').strip(),
                            witness2_id         = req_data.get('witness2_id', '—').strip(),
                            witness2_relation   = req_data.get('witness2_relation', '').strip() or None,
                            civil_officer       = req_data.get('civil_officer', current_user.full_name).strip(),
                            registered_by       = current_user.id,
                        )
                        db.session.add(found_record)
                        db.session.flush()

                    elif cr.doc_type == 'death':
                        cert_num = generate_certificate_number('death', center.code)
                        def _parse_date(val):
                            if not val: return None
                            try: return datetime.strptime(val, '%Y-%m-%d').date()
                            except: return None
                        found_record = Death(
                            certificate_number  = cert_num,
                            center_id           = center.id,
                            registration_date   = _parse_date(req_data.get('registration_date')) or datetime.utcnow().date(),
                            deceased_full_name  = req_data.get('deceased_full_name', '').strip(),
                            deceased_gender     = req_data.get('deceased_gender', 'M'),
                            deceased_birth_date = _parse_date(req_data.get('deceased_birth_date')),
                            deceased_age        = int(req_data['deceased_age']) if req_data.get('deceased_age') else None,
                            usual_residence     = req_data.get('usual_residence', '').strip(),
                            death_date          = _parse_date(req_data.get('death_date')) or datetime.utcnow().date(),
                            death_place         = req_data.get('death_place', '').strip(),
                            death_place_type    = req_data.get('death_place_type', 'other'),
                            cause_of_death      = req_data.get('cause_of_death', '').strip(),
                            certifier_name      = req_data.get('certifier_name', current_user.full_name).strip(),
                            witness1_name       = req_data.get('witness1_name', '').strip() or None,
                            witness1_id         = req_data.get('witness1_id', '').strip() or None,
                            witness1_relation   = req_data.get('witness1_relation', '').strip() or None,
                            witness2_name       = req_data.get('witness2_name', '').strip() or None,
                            witness2_id         = req_data.get('witness2_id', '').strip() or None,
                            witness2_relation   = req_data.get('witness2_relation', '').strip() or None,
                            civil_officer       = req_data.get('civil_officer', current_user.full_name).strip(),
                            registered_by       = current_user.id,
                        )
                        db.session.add(found_record)
                        db.session.flush()

                    elif cr.doc_type == 'divorce':
                        cert_num = generate_certificate_number('divorce', center.code)
                        def _parse_date(val):
                            if not val: return None
                            try: return datetime.strptime(val, '%Y-%m-%d').date()
                            except: return None
                        found_record = Divorce(
                            certificate_number  = cert_num,
                            center_id           = center.id,
                            registration_date   = _parse_date(req_data.get('registration_date')) or datetime.utcnow().date(),
                            divorce_date        = _parse_date(req_data.get('divorce_date')) or datetime.utcnow().date(),
                            divorce_place       = req_data.get('divorce_place', '').strip(),
                            divorce_type        = req_data.get('divorce_type', 'mutual'),
                            marriage_cert_number= req_data.get('marriage_cert_number', '').strip() or None,
                            husband_full_name   = req_data.get('husband_full_name', '').strip(),
                            husband_birth_date  = _parse_date(req_data.get('husband_birth_date')) or datetime.utcnow().date(),
                            husband_birth_place = req_data.get('husband_birth_place', '—').strip(),
                            husband_profession  = req_data.get('husband_profession', '—').strip(),
                            husband_nationality = req_data.get('husband_nationality', '—').strip(),
                            husband_id_number   = req_data.get('husband_id_number', '—').strip(),
                            wife_full_name      = req_data.get('wife_full_name', '').strip(),
                            wife_birth_date     = _parse_date(req_data.get('wife_birth_date')) or datetime.utcnow().date(),
                            wife_birth_place    = req_data.get('wife_birth_place', '—').strip(),
                            wife_profession     = req_data.get('wife_profession', '—').strip(),
                            wife_nationality    = req_data.get('wife_nationality', '—').strip(),
                            wife_id_number      = req_data.get('wife_id_number', '—').strip(),
                            witness1_name       = req_data.get('witness1_name', '—').strip(),
                            witness1_id         = req_data.get('witness1_id', '—').strip(),
                            witness1_relation   = req_data.get('witness1_relation', '').strip() or None,
                            witness2_name       = req_data.get('witness2_name', '—').strip(),
                            witness2_id         = req_data.get('witness2_id', '—').strip(),
                            witness2_relation   = req_data.get('witness2_relation', '').strip() or None,
                            civil_officer       = req_data.get('civil_officer', current_user.full_name).strip(),
                            registered_by       = current_user.id,
                        )
                        db.session.add(found_record)
                        db.session.flush()

                except Exception as e:
                    db.session.rollback()
                    flash(f'خطأ أثناء إنشاء السجل: {str(e)}', 'danger')
                    return redirect(url_for('citizen.officer_review', req_id=cr.id))

            else:
                # ─── الحالة 2: إعادة إصدار أو تصحيح ─── البحث عن سجل موجود
                cert_num = (cr.ref_certificate_number or '').strip()

                if cert_num:
                    if cr.doc_type == 'birth':
                        found_record = Birth.query.filter_by(certificate_number=cert_num).first()
                    elif cr.doc_type == 'marriage':
                        found_record = Marriage.query.filter_by(certificate_number=cert_num).first()
                    elif cr.doc_type == 'death':
                        found_record = Death.query.filter_by(certificate_number=cert_num).first()
                    elif cr.doc_type == 'divorce':
                        found_record = Divorce.query.filter_by(certificate_number=cert_num).first()

                if not found_record:
                    if cr.doc_type == 'birth':
                        name = req_data.get('child_full_name', '').strip()
                        if name:
                            found_record = Birth.query.filter(Birth.child_full_name.ilike(f'%{name}%')).first()
                    elif cr.doc_type == 'marriage':
                        name = req_data.get('husband_full_name', '').strip()
                        if name:
                            found_record = Marriage.query.filter(Marriage.husband_full_name.ilike(f'%{name}%')).first()
                    elif cr.doc_type == 'death':
                        name = req_data.get('deceased_full_name', '').strip()
                        if name:
                            found_record = Death.query.filter(Death.deceased_full_name.ilike(f'%{name}%')).first()
                    elif cr.doc_type == 'divorce':
                        name = req_data.get('husband_full_name', '').strip()
                        if name:
                            found_record = Divorce.query.filter(Divorce.husband_full_name.ilike(f'%{name}%')).first()

                if not found_record:
                    db.session.commit()
                    log_action('UPDATE', 'citizen_requests', record_id=cr.id,
                               new_data={'status': 'approved', 'note': 'no_record_matched'})
                    flash('تم قبول الطلب — لم يُعثر على سجل مطابق، يرجى ربط الوثيقة يدوياً', 'warning')
                    return redirect(url_for('citizen.officer_requests'))

            # ─── إنشاء أو جلب الوثيقة وربطها بالطلب ───
            existing_doc = Document.query.filter_by(
                doc_type=cr.doc_type,
                ref_id=found_record.id,
                is_valid=True
            ).first()

            if not existing_doc:
                existing_doc = Document(
                    doc_type  = cr.doc_type,
                    ref_id    = found_record.id,
                    qr_code   = generate_qr_token(),
                    issued_by = current_user.id,
                )
                db.session.add(existing_doc)
                db.session.flush()

            cr.issued_doc_id = existing_doc.id
            db.session.commit()
            log_action('UPDATE', 'citizen_requests', record_id=cr.id,
                       new_data={'status': 'approved', 'doc_id': existing_doc.id})
            flash('تم قبول الطلب وإصدار الوثيقة بنجاح', 'success')
            return redirect(url_for('citizen.officer_requests'))

        elif action == 'reject':
            reason = request.form.get('rejection_reason', '').strip()
            if not reason:
                flash('يجب تحديد سبب الرفض', 'danger')
                return render_template('citizen/officer_review.html',
                                       cr=cr, data=data, lang=lang)

            cr.status           = 'rejected'
            cr.rejection_reason = reason
            cr.reviewed_by      = current_user.id
            cr.reviewed_at      = datetime.utcnow()
            db.session.commit()
            log_action('UPDATE', 'citizen_requests', record_id=cr.id,
                       new_data={'status': 'rejected', 'reason': reason})
            flash('تم رفض الطلب', 'warning')
            return redirect(url_for('citizen.officer_requests'))

    return render_template('citizen/officer_review.html',
                           cr=cr, data=data, lang=lang)


# ==================== التحقق من وثيقة (عامة بدون دخول) ====================
@citizen_bp.route('/verify', methods=['GET', 'POST'])
def verify():
    result = None

    if request.method == 'POST':
        token    = request.form.get('token', '').strip().upper()
        document = Document.query.filter_by(qr_code=token).first()

        if not document or not document.is_valid:
            result = {
                'valid':   False,
                'message': 'الوثيقة غير موجودة أو ملغاة'
            }
        else:
            name = center = record = None

            if document.doc_type == 'birth':
                record = Birth.query.get(document.ref_id)
                if record:
                    name   = record.child_full_name
                    center = Center.query.get(record.center_id)

            elif document.doc_type == 'marriage':
                record = Marriage.query.get(document.ref_id)
                if record:
                    name   = f'{record.husband_full_name} / {record.wife_full_name}'
                    center = Center.query.get(record.center_id)

            elif document.doc_type == 'death':
                record = Death.query.get(document.ref_id)
                if record:
                    name   = record.deceased_full_name
                    center = Center.query.get(record.center_id)

            elif document.doc_type == 'divorce':
                record = Divorce.query.get(document.ref_id)
                if record:
                    name   = f'{record.husband_full_name} / {record.wife_full_name}'
                    center = Center.query.get(record.center_id)

            result = {
                'valid':     True,
                'doc_type':  document.doc_type,
                'issued_at': document.issued_at,
                'name':      name,
                'center':    center.name_ar if center else '',
                'record':    record,
            }

    lang = session.get('lang', 'ar')
    return render_template('citizen/verify.html', result=result, lang=lang)
