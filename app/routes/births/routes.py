from flask import render_template, redirect, url_for, request, flash, session, send_file
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.routes.births import births_bp
from app.models.birth import Birth
from app.models.document import Document
from app.models.center import Center
from app.utils.audit import log_action
from app.utils.decorators import role_required
from app.utils.helpers import generate_certificate_number
from app.utils.qr_gen import generate_qr_token
from app.utils.pdf_gen import generate_birth_pdf


# ==================== قائمة المواليد ====================
@births_bp.route('/')
@login_required
def index():
    page   = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()

    query = Birth.query

    if current_user.role == 'officer':
        query = query.filter_by(center_id=current_user.center_id)
    elif current_user.role == 'region_mgr':
        if current_user.center_id and current_user.center:
            center_ids = [c.id for c in Center.query.filter_by(
                region=current_user.center.region
            ).all()]
        else:
            center_ids = []
        query = query.filter(Birth.center_id.in_(center_ids))

    if search:
        query = query.filter(
            Birth.child_full_name.ilike(f'%{search}%')  |
            Birth.certificate_number.ilike(f'%{search}%') |
            Birth.father_full_name.ilike(f'%{search}%') |
            Birth.mother_full_name.ilike(f'%{search}%')
        )

    births = query.order_by(Birth.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    lang = session.get('lang', 'ar')
    return render_template('births/list.html',
                           births=births, search=search, lang=lang)


# ==================== إضافة مولود ====================
@births_bp.route('/new', methods=['GET', 'POST'])
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
            return render_template('births/form.html', centers=centers)

        cert_number = generate_certificate_number('birth', center.code)

        try:
            birth = Birth(
                certificate_number = cert_number,
                center_id          = center_id,
                registration_date  = datetime.strptime(
                    request.form['registration_date'], '%Y-%m-%d'
                ).date(),

                child_full_name = request.form['child_full_name'].strip(),
                child_gender    = request.form['child_gender'],
                birth_date      = datetime.strptime(
                    request.form['birth_date'], '%Y-%m-%d'
                ).date(),
                birth_place     = request.form['birth_place'].strip(),

                father_full_name   = request.form['father_full_name'].strip(),
                father_profession  = request.form['father_profession'].strip(),
                father_birth_place = request.form.get('father_birth_place', '').strip() or None,
                father_birth_date  = datetime.strptime(
                    request.form['father_birth_date'], '%Y-%m-%d'
                ).date() if request.form.get('father_birth_date') else None,

                mother_full_name   = request.form['mother_full_name'].strip(),
                mother_profession  = request.form['mother_profession'].strip(),
                mother_birth_place = request.form.get('mother_birth_place', '').strip() or None,
                mother_birth_date  = datetime.strptime(
                    request.form['mother_birth_date'], '%Y-%m-%d'
                ).date() if request.form.get('mother_birth_date') else None,

                witness1_name     = request.form.get('witness1_name', '').strip() or None,
                witness1_id       = request.form.get('witness1_id',   '').strip() or None,
                witness1_relation = request.form.get('witness1_relation', '').strip() or None,
                witness2_name     = request.form.get('witness2_name', '').strip() or None,
                witness2_id       = request.form.get('witness2_id',   '').strip() or None,
                witness2_relation = request.form.get('witness2_relation', '').strip() or None,

                civil_officer = request.form['civil_officer'].strip(),
                registered_by = current_user.id,
                notes         = request.form.get('notes', '').strip() or None,
            )

            db.session.add(birth)
            db.session.flush()

            qr_token = generate_qr_token()
            document = Document(
                doc_type  = 'birth',
                ref_id    = birth.id,
                qr_code   = qr_token,
                issued_by = current_user.id
            )
            db.session.add(document)
            db.session.commit()

            log_action('CREATE', 'births', record_id=birth.id,
                       new_data=birth.to_dict())
            flash(f'تم تسجيل المولود بنجاح — رقم الشهادة: {cert_number}', 'success')
            return redirect(url_for('births.detail', birth_id=birth.id))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء الحفظ: {str(e)}', 'danger')

    lang  = session.get('lang', 'ar')
    today = date.today().isoformat()
    return render_template('births/form.html',
                           centers=centers, lang=lang, today=today)


# ==================== تفاصيل مولود ====================
@births_bp.route('/<int:birth_id>')
@login_required
def detail(birth_id):
    birth = Birth.query.get_or_404(birth_id)

    if current_user.role == 'officer' and birth.center_id != current_user.center_id:
        flash('ليس لديك صلاحية لعرض هذا السجل', 'danger')
        return redirect(url_for('births.index'))

    document = Document.query.filter_by(
        doc_type='birth', ref_id=birth_id, is_valid=True
    ).first()

    lang = session.get('lang', 'ar')
    return render_template('births/detail.html',
                           birth=birth, document=document, lang=lang)


# ==================== تعديل مولود ====================
@births_bp.route('/<int:birth_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('officer', 'region_mgr', 'admin')
def edit(birth_id):
    birth   = Birth.query.get_or_404(birth_id)
    centers = Center.query.filter_by(is_active=True).all()

    if current_user.role == 'officer' and birth.center_id != current_user.center_id:
        flash('ليس لديك صلاحية لتعديل هذا السجل', 'danger')
        return redirect(url_for('births.index'))

    if request.method == 'POST':
        old_data = birth.to_dict()
        try:
            birth.child_full_name    = request.form['child_full_name'].strip()
            birth.child_gender       = request.form['child_gender']
            birth.birth_date         = datetime.strptime(
                request.form['birth_date'], '%Y-%m-%d'
            ).date()
            birth.birth_place        = request.form['birth_place'].strip()
            birth.father_full_name   = request.form['father_full_name'].strip()
            birth.father_profession  = request.form['father_profession'].strip()
            birth.mother_full_name   = request.form['mother_full_name'].strip()
            birth.mother_profession  = request.form['mother_profession'].strip()

            birth.witness1_name     = request.form.get('witness1_name',     '').strip() or None
            birth.witness1_id       = request.form.get('witness1_id',       '').strip() or None
            birth.witness1_relation = request.form.get('witness1_relation', '').strip() or None
            birth.witness2_name     = request.form.get('witness2_name',     '').strip() or None
            birth.witness2_id       = request.form.get('witness2_id',       '').strip() or None
            birth.witness2_relation = request.form.get('witness2_relation', '').strip() or None

            birth.civil_officer = request.form['civil_officer'].strip()
            birth.notes         = request.form.get('notes', '').strip() or None
            birth.updated_at    = datetime.utcnow()

            db.session.commit()
            log_action('UPDATE', 'births', record_id=birth.id,
                       old_data=old_data, new_data=birth.to_dict())
            flash('تم تحديث البيانات بنجاح', 'success')
            return redirect(url_for('births.detail', birth_id=birth.id))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

    lang = session.get('lang', 'ar')
    return render_template('births/form.html',
                           birth=birth, centers=centers,
                           edit=True, lang=lang)


# ==================== تصدير PDF ====================
@births_bp.route('/<int:birth_id>/pdf')
@login_required
def export_pdf(birth_id):
    birth = Birth.query.get_or_404(birth_id)

    document = Document.query.filter_by(
        doc_type='birth', ref_id=birth_id, is_valid=True
    ).first()

    if not document:
        qr_token = generate_qr_token()
        document = Document(
            doc_type  = 'birth',
            ref_id    = birth_id,
            qr_code   = qr_token,
            issued_by = current_user.id
        )
        db.session.add(document)
        db.session.commit()

    pdf_buffer = generate_birth_pdf(birth, document)
    log_action('EXPORT', 'births', record_id=birth_id)

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f'birth_{birth.certificate_number}.pdf'
    )


# ==================== بحث سريع (JSON) ====================
@births_bp.route('/search')
@login_required
def search():
    from flask import jsonify
    q       = request.args.get('q', '').strip()
    results = []

    if q:
        query = Birth.query.filter(
            Birth.child_full_name.ilike(f'%{q}%') |
            Birth.certificate_number.ilike(f'%{q}%')
        )
        if current_user.role == 'officer':
            query = query.filter_by(center_id=current_user.center_id)

        births = query.limit(10).all()
        results = [{'id': b.id, 'name': b.child_full_name,
                    'cert': b.certificate_number} for b in births]

    return jsonify(results)
