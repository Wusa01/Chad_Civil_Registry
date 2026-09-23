from flask import render_template, redirect, url_for, request, flash, session, send_file
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.routes.marriages import marriages_bp
from app.models.marriage import Marriage
from app.models.document import Document
from app.models.center import Center
from app.utils.audit import log_action
from app.utils.decorators import role_required
from app.utils.helpers import generate_certificate_number
from app.utils.qr_gen import generate_qr_token
from app.utils.pdf_gen import generate_marriage_pdf


# ==================== قائمة الزيجات ====================
@marriages_bp.route('/')
@login_required
def index():
    page   = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()

    query = Marriage.query

    if current_user.role == 'officer':
        query = query.filter_by(center_id=current_user.center_id)
    elif current_user.role == 'region_mgr':
        if current_user.center_id and current_user.center:
            center_ids = [c.id for c in Center.query.filter_by(
                region=current_user.center.region
            ).all()]
        else:
            center_ids = []
        query = query.filter(Marriage.center_id.in_(center_ids))

    if search:
        query = query.filter(
            Marriage.husband_full_name.ilike(f'%{search}%') |
            Marriage.wife_full_name.ilike(f'%{search}%')    |
            Marriage.certificate_number.ilike(f'%{search}%')
        )

    marriages = query.order_by(Marriage.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    lang = session.get('lang', 'ar')
    return render_template('marriages/list.html',
                           marriages=marriages, search=search, lang=lang)


# ==================== إضافة زواج ====================
@marriages_bp.route('/new', methods=['GET', 'POST'])
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
            return render_template('marriages/form.html', centers=centers)

        cert_number = generate_certificate_number('marriage', center.code)

        try:
            marriage = Marriage(
                certificate_number = cert_number,
                center_id          = center_id,
                registration_date  = datetime.strptime(
                    request.form['registration_date'], '%Y-%m-%d'
                ).date() if request.form.get('registration_date') else None,
                marriage_date  = datetime.strptime(
                    request.form['marriage_date'], '%Y-%m-%d'
                ).date(),
                marriage_place = request.form['marriage_place'].strip(),
                marriage_type  = request.form.get('marriage_type', 'monogamy'),
                dowry_amount   = request.form.get('dowry_amount', type=float) or None,
                dowry_mentioned  = bool(request.form.get('dowry_amount')),
                age_dispensation = bool(request.form.get('age_dispensation')),

                husband_full_name   = request.form['husband_full_name'].strip(),
                husband_birth_date  = datetime.strptime(
                    request.form['husband_birth_date'], '%Y-%m-%d'
                ).date(),
                husband_birth_place = request.form['husband_birth_place'].strip(),
                husband_profession  = request.form['husband_profession'].strip(),
                husband_nationality = request.form['husband_nationality'].strip(),
                husband_id_number   = request.form['husband_id_number'].strip(),
                husband_father_name = request.form['husband_father_name'].strip(),
                husband_mother_name = request.form['husband_mother_name'].strip(),

                wife_full_name   = request.form['wife_full_name'].strip(),
                wife_birth_date  = datetime.strptime(
                    request.form['wife_birth_date'], '%Y-%m-%d'
                ).date(),
                wife_birth_place = request.form['wife_birth_place'].strip(),
                wife_profession  = request.form['wife_profession'].strip(),
                wife_nationality = request.form['wife_nationality'].strip(),
                wife_id_number   = request.form['wife_id_number'].strip(),
                wife_father_name = request.form['wife_father_name'].strip(),
                wife_mother_name = request.form['wife_mother_name'].strip(),

                witness1_name     = request.form.get('witness1_name',     '').strip(),
                witness1_id       = request.form.get('witness1_id',       '').strip(),
                witness1_relation = request.form.get('witness1_relation', '').strip() or None,
                witness2_name     = request.form.get('witness2_name',     '').strip(),
                witness2_id       = request.form.get('witness2_id',       '').strip(),
                witness2_relation = request.form.get('witness2_relation', '').strip() or None,

                civil_officer = request.form['civil_officer'].strip(),
                registered_by = current_user.id,
            )

            db.session.add(marriage)
            db.session.flush()

            qr_token = generate_qr_token()
            document = Document(
                doc_type  = 'marriage',
                ref_id    = marriage.id,
                qr_code   = qr_token,
                issued_by = current_user.id
            )
            db.session.add(document)
            db.session.commit()

            log_action('CREATE', 'marriages', record_id=marriage.id,
                       new_data=marriage.to_dict())
            flash(f'تم تسجيل عقد الزواج بنجاح — رقم الشهادة: {cert_number}', 'success')
            return redirect(url_for('marriages.detail', marriage_id=marriage.id))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء الحفظ: {str(e)}', 'danger')

    lang  = session.get('lang', 'ar')
    today = date.today().isoformat()
    return render_template('marriages/form.html',
                           centers=centers, lang=lang, today=today)


# ==================== تفاصيل زواج ====================
@marriages_bp.route('/<int:marriage_id>')
@login_required
def detail(marriage_id):
    marriage = Marriage.query.get_or_404(marriage_id)

    if current_user.role == 'officer' and marriage.center_id != current_user.center_id:
        flash('ليس لديك صلاحية لعرض هذا السجل', 'danger')
        return redirect(url_for('marriages.index'))

    document = Document.query.filter_by(
        doc_type='marriage', ref_id=marriage_id, is_valid=True
    ).first()

    lang = session.get('lang', 'ar')
    return render_template('marriages/detail.html',
                           marriage=marriage, document=document, lang=lang)


# ==================== تعديل زواج ====================
@marriages_bp.route('/<int:marriage_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('officer', 'region_mgr', 'admin')
def edit(marriage_id):
    marriage = Marriage.query.get_or_404(marriage_id)
    centers  = Center.query.filter_by(is_active=True).all()

    if current_user.role == 'officer' and marriage.center_id != current_user.center_id:
        flash('ليس لديك صلاحية لتعديل هذا السجل', 'danger')
        return redirect(url_for('marriages.index'))

    if request.method == 'POST':
        old_data = marriage.to_dict()
        try:
            marriage.marriage_date  = datetime.strptime(
                request.form['marriage_date'], '%Y-%m-%d'
            ).date()
            marriage.marriage_place = request.form['marriage_place'].strip()
            marriage.marriage_type  = request.form.get('marriage_type', 'monogamy')
            marriage.dowry_amount   = request.form.get('dowry_amount', type=float) or None
            marriage.dowry_mentioned  = bool(request.form.get('dowry_amount'))
            marriage.age_dispensation = bool(request.form.get('age_dispensation'))

            marriage.husband_full_name   = request.form['husband_full_name'].strip()
            marriage.husband_birth_date  = datetime.strptime(
                request.form['husband_birth_date'], '%Y-%m-%d'
            ).date()
            marriage.husband_birth_place = request.form['husband_birth_place'].strip()
            marriage.husband_profession  = request.form['husband_profession'].strip()
            marriage.husband_nationality = request.form['husband_nationality'].strip()
            marriage.husband_id_number   = request.form['husband_id_number'].strip()
            marriage.husband_father_name = request.form['husband_father_name'].strip()
            marriage.husband_mother_name = request.form['husband_mother_name'].strip()

            marriage.wife_full_name   = request.form['wife_full_name'].strip()
            marriage.wife_birth_date  = datetime.strptime(
                request.form['wife_birth_date'], '%Y-%m-%d'
            ).date()
            marriage.wife_birth_place = request.form['wife_birth_place'].strip()
            marriage.wife_profession  = request.form['wife_profession'].strip()
            marriage.wife_nationality = request.form['wife_nationality'].strip()
            marriage.wife_id_number   = request.form['wife_id_number'].strip()
            marriage.wife_father_name = request.form['wife_father_name'].strip()
            marriage.wife_mother_name = request.form['wife_mother_name'].strip()

            marriage.witness1_name     = request.form.get('witness1_name',     '').strip()
            marriage.witness1_id       = request.form.get('witness1_id',       '').strip()
            marriage.witness1_relation = request.form.get('witness1_relation', '').strip() or None
            marriage.witness2_name     = request.form.get('witness2_name',     '').strip()
            marriage.witness2_id       = request.form.get('witness2_id',       '').strip()
            marriage.witness2_relation = request.form.get('witness2_relation', '').strip() or None

            marriage.civil_officer = request.form['civil_officer'].strip()
            marriage.updated_at    = datetime.utcnow()

            db.session.commit()
            log_action('UPDATE', 'marriages', record_id=marriage.id,
                       old_data=old_data, new_data=marriage.to_dict())
            flash('تم تحديث البيانات بنجاح', 'success')
            return redirect(url_for('marriages.detail', marriage_id=marriage.id))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

    lang  = session.get('lang', 'ar')
    today = date.today().isoformat()
    return render_template('marriages/form.html',
                           marriage=marriage, centers=centers,
                           edit=True, lang=lang, today=today)


# ==================== تصدير PDF ====================
@marriages_bp.route('/<int:marriage_id>/pdf')
@login_required
def export_pdf(marriage_id):
    marriage = Marriage.query.get_or_404(marriage_id)

    document = Document.query.filter_by(
        doc_type='marriage', ref_id=marriage_id, is_valid=True
    ).first()

    if not document:
        qr_token = generate_qr_token()
        document = Document(
            doc_type  = 'marriage',
            ref_id    = marriage_id,
            qr_code   = qr_token,
            issued_by = current_user.id
        )
        db.session.add(document)
        db.session.commit()

    pdf_buffer = generate_marriage_pdf(marriage, document)
    log_action('EXPORT', 'marriages', record_id=marriage_id)

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f'marriage_{marriage.certificate_number}.pdf'
    )
