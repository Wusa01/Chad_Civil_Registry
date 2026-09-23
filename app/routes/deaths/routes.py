from flask import render_template, redirect, url_for, request, flash, session, send_file
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.routes.deaths import deaths_bp
from app.models.death import Death
from app.models.document import Document
from app.models.center import Center
from app.utils.audit import log_action
from app.utils.decorators import role_required
from app.utils.helpers import generate_certificate_number
from app.utils.qr_gen import generate_qr_token
from app.utils.pdf_gen import generate_death_pdf


# ==================== قائمة الوفيات ====================
@deaths_bp.route('/')
@login_required
def index():
    page   = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()

    query = Death.query

    if current_user.role == 'officer':
        query = query.filter_by(center_id=current_user.center_id)
    elif current_user.role == 'region_mgr':
        if current_user.center_id and current_user.center:
            center_ids = [c.id for c in Center.query.filter_by(
                region=current_user.center.region
            ).all()]
        else:
            center_ids = []
        query = query.filter(Death.center_id.in_(center_ids))

    if search:
        query = query.filter(
            Death.deceased_full_name.ilike(f'%{search}%') |
            Death.certificate_number.ilike(f'%{search}%')
        )

    deaths = query.order_by(Death.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    lang = session.get('lang', 'ar')
    return render_template('deaths/list.html',
                           deaths=deaths, search=search, lang=lang)


# ==================== إضافة وفاة ====================
@deaths_bp.route('/new', methods=['GET', 'POST'])
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
            return render_template('deaths/form.html', centers=centers)

        cert_number = generate_certificate_number('death', center.code)

        try:
            death = Death(
                certificate_number = cert_number,
                center_id          = center_id,
                registration_date  = datetime.strptime(
                    request.form['registration_date'], '%Y-%m-%d'
                ).date(),

                deceased_full_name  = request.form['deceased_full_name'].strip(),
                deceased_gender     = request.form['deceased_gender'],
                deceased_age        = request.form.get('deceased_age', type=int) or None,
                deceased_birth_date = datetime.strptime(
                    request.form['deceased_birth_date'], '%Y-%m-%d'
                ).date() if request.form.get('deceased_birth_date') else None,
                usual_residence     = request.form['usual_residence'].strip(),

                death_date       = datetime.strptime(
                    request.form['death_date'], '%Y-%m-%d'
                ).date(),
                death_place      = request.form['death_place'].strip(),
                death_place_type = request.form['death_place_type'],
                cause_of_death   = request.form['cause_of_death'].strip(),
                certifier_name   = request.form['certifier_name'].strip(),

                witness1_name     = request.form.get('witness1_name',     '').strip() or None,
                witness1_id       = request.form.get('witness1_id',       '').strip() or None,
                witness1_relation = request.form.get('witness1_relation', '').strip() or None,
                witness2_name     = request.form.get('witness2_name',     '').strip() or None,
                witness2_id       = request.form.get('witness2_id',       '').strip() or None,
                witness2_relation = request.form.get('witness2_relation', '').strip() or None,

                civil_officer = request.form['civil_officer'].strip(),
                registered_by = current_user.id,
                notes         = request.form.get('notes', '').strip() or None,
            )

            db.session.add(death)
            db.session.flush()

            qr_token = generate_qr_token()
            document = Document(
                doc_type  = 'death',
                ref_id    = death.id,
                qr_code   = qr_token,
                issued_by = current_user.id
            )
            db.session.add(document)
            db.session.commit()

            log_action('CREATE', 'deaths', record_id=death.id,
                       new_data=death.to_dict())
            flash(f'تم تسجيل الوفاة بنجاح — رقم الشهادة: {cert_number}', 'success')
            return redirect(url_for('deaths.detail', death_id=death.id))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء الحفظ: {str(e)}', 'danger')

    lang  = session.get('lang', 'ar')
    today = date.today().isoformat()
    return render_template('deaths/form.html',
                           centers=centers, lang=lang, today=today)


# ==================== تفاصيل وفاة ====================
@deaths_bp.route('/<int:death_id>')
@login_required
def detail(death_id):
    death = Death.query.get_or_404(death_id)

    if current_user.role == 'officer' and death.center_id != current_user.center_id:
        flash('ليس لديك صلاحية لعرض هذا السجل', 'danger')
        return redirect(url_for('deaths.index'))

    document = Document.query.filter_by(
        doc_type='death', ref_id=death_id, is_valid=True
    ).first()

    lang = session.get('lang', 'ar')
    return render_template('deaths/detail.html',
                           death=death, document=document, lang=lang)


# ==================== تعديل وفاة ====================
@deaths_bp.route('/<int:death_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('officer', 'region_mgr', 'admin')
def edit(death_id):
    death   = Death.query.get_or_404(death_id)
    centers = Center.query.filter_by(is_active=True).all()

    if current_user.role == 'officer' and death.center_id != current_user.center_id:
        flash('ليس لديك صلاحية لتعديل هذا السجل', 'danger')
        return redirect(url_for('deaths.index'))

    if request.method == 'POST':
        old_data = death.to_dict()
        try:
            death.deceased_full_name  = request.form['deceased_full_name'].strip()
            death.deceased_gender     = request.form['deceased_gender']
            death.deceased_age        = request.form.get('deceased_age', type=int) or None
            death.usual_residence     = request.form['usual_residence'].strip()
            death.death_date          = datetime.strptime(
                request.form['death_date'], '%Y-%m-%d'
            ).date()
            death.death_place         = request.form['death_place'].strip()
            death.death_place_type    = request.form['death_place_type']
            death.cause_of_death      = request.form['cause_of_death'].strip()
            death.certifier_name      = request.form['certifier_name'].strip()

            death.witness1_name     = request.form.get('witness1_name',     '').strip() or None
            death.witness1_id       = request.form.get('witness1_id',       '').strip() or None
            death.witness1_relation = request.form.get('witness1_relation', '').strip() or None
            death.witness2_name     = request.form.get('witness2_name',     '').strip() or None
            death.witness2_id       = request.form.get('witness2_id',       '').strip() or None
            death.witness2_relation = request.form.get('witness2_relation', '').strip() or None

            death.civil_officer = request.form['civil_officer'].strip()
            death.notes         = request.form.get('notes', '').strip() or None
            death.updated_at    = datetime.utcnow()

            db.session.commit()
            log_action('UPDATE', 'deaths', record_id=death.id,
                       old_data=old_data, new_data=death.to_dict())
            flash('تم تحديث البيانات بنجاح', 'success')
            return redirect(url_for('deaths.detail', death_id=death.id))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

    lang  = session.get('lang', 'ar')
    today = date.today().isoformat()
    return render_template('deaths/form.html',
                           death=death, centers=centers,
                           edit=True, lang=lang, today=today)


# ==================== تصدير PDF ====================
@deaths_bp.route('/<int:death_id>/pdf')
@login_required
def export_pdf(death_id):
    death = Death.query.get_or_404(death_id)

    document = Document.query.filter_by(
        doc_type='death', ref_id=death_id, is_valid=True
    ).first()

    if not document:
        qr_token = generate_qr_token()
        document = Document(
            doc_type  = 'death',
            ref_id    = death_id,
            qr_code   = qr_token,
            issued_by = current_user.id
        )
        db.session.add(document)
        db.session.commit()

    pdf_buffer = generate_death_pdf(death, document)
    log_action('EXPORT', 'deaths', record_id=death_id)

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f'death_{death.certificate_number}.pdf'
    )


# ==================== بحث سريع (JSON) ====================
@deaths_bp.route('/search')
@login_required
def search():
    from flask import jsonify
    q       = request.args.get('q', '').strip()
    results = []

    if q:
        query = Death.query.filter(
            Death.deceased_full_name.ilike(f'%{q}%') |
            Death.certificate_number.ilike(f'%{q}%')
        )
        if current_user.role == 'officer':
            query = query.filter_by(center_id=current_user.center_id)

        deaths = query.limit(10).all()
        results = [{'id': d.id, 'name': d.deceased_full_name,
                    'cert': d.certificate_number} for d in deaths]

    return jsonify(results)
