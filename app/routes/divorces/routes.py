from flask import render_template, redirect, url_for, request, flash, session, send_file
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.routes.divorces import divorces_bp
from app.models.divorce import Divorce
from app.models.document import Document
from app.models.center import Center
from app.utils.audit import log_action
from app.utils.decorators import role_required
from app.utils.helpers import generate_certificate_number
from app.utils.qr_gen import generate_qr_token
from app.utils.pdf_gen import generate_divorce_pdf


# ==================== قائمة الطلاق ====================
@divorces_bp.route('/')
@login_required
def index():
    page   = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()

    query = Divorce.query

    if current_user.role == 'officer':
        query = query.filter_by(center_id=current_user.center_id)
    elif current_user.role == 'region_mgr':
        if current_user.center_id and current_user.center:
            center_ids = [c.id for c in Center.query.filter_by(
                region=current_user.center.region
            ).all()]
        else:
            center_ids = []
        query = query.filter(Divorce.center_id.in_(center_ids))

    if search:
        query = query.filter(
            Divorce.husband_full_name.ilike(f'%{search}%') |
            Divorce.wife_full_name.ilike(f'%{search}%')    |
            Divorce.certificate_number.ilike(f'%{search}%')
        )

    divorces = query.order_by(Divorce.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    lang = session.get('lang', 'ar')
    return render_template('divorces/list.html',
                           divorces=divorces, search=search, lang=lang)


# ==================== إضافة طلاق ====================
@divorces_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('officer', 'region_mgr', 'admin')
def new():
    centers = Center.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        if current_user.role == 'officer':
            center_id = current_user.center_id
        else:
            center_id = request.form.get('center_id', type=int)

        center = Center.query.get(center_id)
        if not center:
            flash('المركز غير موجود', 'danger')
            return render_template('divorces/form.html', centers=centers)

        cert_number = generate_certificate_number('divorce', center.code)

        try:
            divorce = Divorce(
                certificate_number = cert_number,
                center_id          = center_id,
                registration_date  = datetime.strptime(
                    request.form['registration_date'], '%Y-%m-%d'
                ).date(),
                divorce_date  = datetime.strptime(
                    request.form['divorce_date'], '%Y-%m-%d'
                ).date(),
                divorce_place = request.form['divorce_place'].strip(),
                divorce_type  = request.form.get('divorce_type', 'mutual'),

                marriage_cert_number  = request.form.get('marriage_cert_number', '').strip() or None,
                court_decision_number = request.form.get('court_decision_number', '').strip() or None,
                court_name            = request.form.get('court_name', '').strip() or None,
                children_count        = request.form.get('children_count', type=int) or 0,
                custody_decision      = request.form.get('custody_decision', '').strip() or None,

                husband_full_name   = request.form['husband_full_name'].strip(),
                husband_birth_date  = datetime.strptime(
                    request.form['husband_birth_date'], '%Y-%m-%d'
                ).date(),
                husband_birth_place = request.form['husband_birth_place'].strip(),
                husband_profession  = request.form['husband_profession'].strip(),
                husband_nationality = request.form['husband_nationality'].strip(),
                husband_id_number   = request.form['husband_id_number'].strip(),

                wife_full_name   = request.form['wife_full_name'].strip(),
                wife_birth_date  = datetime.strptime(
                    request.form['wife_birth_date'], '%Y-%m-%d'
                ).date(),
                wife_birth_place = request.form['wife_birth_place'].strip(),
                wife_profession  = request.form['wife_profession'].strip(),
                wife_nationality = request.form['wife_nationality'].strip(),
                wife_id_number   = request.form['wife_id_number'].strip(),

                witness1_name     = request.form.get('witness1_name',     '').strip(),
                witness1_id       = request.form.get('witness1_id',       '').strip(),
                witness1_relation = request.form.get('witness1_relation', '').strip() or None,
                witness2_name     = request.form.get('witness2_name',     '').strip(),
                witness2_id       = request.form.get('witness2_id',       '').strip(),
                witness2_relation = request.form.get('witness2_relation', '').strip() or None,

                civil_officer = request.form['civil_officer'].strip(),
                registered_by = current_user.id,
                notes         = request.form.get('notes', '').strip() or None,
            )

            db.session.add(divorce)
            db.session.flush()

            qr_token = generate_qr_token()
            document = Document(
                doc_type  = 'divorce',
                ref_id    = divorce.id,
                qr_code   = qr_token,
                issued_by = current_user.id
            )
            db.session.add(document)
            db.session.commit()

            log_action('CREATE', 'divorces', record_id=divorce.id,
                       new_data=divorce.to_dict())
            flash(f'تم تسجيل وثيقة الطلاق بنجاح — رقم الشهادة: {cert_number}', 'success')
            return redirect(url_for('divorces.detail', divorce_id=divorce.id))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء الحفظ: {str(e)}', 'danger')

    lang  = session.get('lang', 'ar')
    today = date.today().isoformat()
    return render_template('divorces/form.html',
                           centers=centers, lang=lang, today=today)


# ==================== تفاصيل طلاق ====================
@divorces_bp.route('/<int:divorce_id>')
@login_required
def detail(divorce_id):
    divorce = Divorce.query.get_or_404(divorce_id)

    if current_user.role == 'officer' and divorce.center_id != current_user.center_id:
        flash('ليس لديك صلاحية لعرض هذا السجل', 'danger')
        return redirect(url_for('divorces.index'))

    document = Document.query.filter_by(
        doc_type='divorce', ref_id=divorce_id, is_valid=True
    ).first()

    lang = session.get('lang', 'ar')
    return render_template('divorces/detail.html',
                           divorce=divorce, document=document, lang=lang)


# ==================== تعديل طلاق ====================
@divorces_bp.route('/<int:divorce_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('officer', 'region_mgr', 'admin')
def edit(divorce_id):
    divorce = Divorce.query.get_or_404(divorce_id)
    centers = Center.query.filter_by(is_active=True).all()

    if current_user.role == 'officer' and divorce.center_id != current_user.center_id:
        flash('ليس لديك صلاحية لتعديل هذا السجل', 'danger')
        return redirect(url_for('divorces.index'))

    if request.method == 'POST':
        old_data = divorce.to_dict()
        try:
            divorce.divorce_date  = datetime.strptime(
                request.form['divorce_date'], '%Y-%m-%d'
            ).date()
            divorce.divorce_place = request.form['divorce_place'].strip()
            divorce.divorce_type  = request.form.get('divorce_type', 'mutual')

            divorce.marriage_cert_number  = request.form.get('marriage_cert_number', '').strip() or None
            divorce.court_decision_number = request.form.get('court_decision_number', '').strip() or None
            divorce.court_name            = request.form.get('court_name', '').strip() or None
            divorce.children_count        = request.form.get('children_count', type=int) or 0
            divorce.custody_decision      = request.form.get('custody_decision', '').strip() or None

            divorce.husband_full_name   = request.form['husband_full_name'].strip()
            divorce.husband_birth_date  = datetime.strptime(
                request.form['husband_birth_date'], '%Y-%m-%d'
            ).date()
            divorce.husband_birth_place = request.form['husband_birth_place'].strip()
            divorce.husband_profession  = request.form['husband_profession'].strip()
            divorce.husband_nationality = request.form['husband_nationality'].strip()
            divorce.husband_id_number   = request.form['husband_id_number'].strip()

            divorce.wife_full_name   = request.form['wife_full_name'].strip()
            divorce.wife_birth_date  = datetime.strptime(
                request.form['wife_birth_date'], '%Y-%m-%d'
            ).date()
            divorce.wife_birth_place = request.form['wife_birth_place'].strip()
            divorce.wife_profession  = request.form['wife_profession'].strip()
            divorce.wife_nationality = request.form['wife_nationality'].strip()
            divorce.wife_id_number   = request.form['wife_id_number'].strip()

            divorce.witness1_name     = request.form.get('witness1_name',     '').strip()
            divorce.witness1_id       = request.form.get('witness1_id',       '').strip()
            divorce.witness1_relation = request.form.get('witness1_relation', '').strip() or None
            divorce.witness2_name     = request.form.get('witness2_name',     '').strip()
            divorce.witness2_id       = request.form.get('witness2_id',       '').strip()
            divorce.witness2_relation = request.form.get('witness2_relation', '').strip() or None

            divorce.civil_officer = request.form['civil_officer'].strip()
            divorce.notes         = request.form.get('notes', '').strip() or None
            divorce.updated_at    = datetime.utcnow()

            db.session.commit()
            log_action('UPDATE', 'divorces', record_id=divorce.id,
                       old_data=old_data, new_data=divorce.to_dict())
            flash('تم تحديث البيانات بنجاح', 'success')
            return redirect(url_for('divorces.detail', divorce_id=divorce.id))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

    lang  = session.get('lang', 'ar')
    today = date.today().isoformat()
    return render_template('divorces/form.html',
                           divorce=divorce, centers=centers,
                           edit=True, lang=lang, today=today)


# ==================== تصدير PDF ====================
@divorces_bp.route('/<int:divorce_id>/pdf')
@login_required
def export_pdf(divorce_id):
    divorce = Divorce.query.get_or_404(divorce_id)

    document = Document.query.filter_by(
        doc_type='divorce', ref_id=divorce_id, is_valid=True
    ).first()

    if not document:
        qr_token = generate_qr_token()
        document = Document(
            doc_type  = 'divorce',
            ref_id    = divorce_id,
            qr_code   = qr_token,
            issued_by = current_user.id
        )
        db.session.add(document)
        db.session.commit()

    pdf_buffer = generate_divorce_pdf(divorce, document)
    log_action('EXPORT', 'divorces', record_id=divorce_id)

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f'divorce_{divorce.certificate_number}.pdf'
    )
