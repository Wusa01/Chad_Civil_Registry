"""
routes.py — مسارات وحدة الأرشفة الرقمية
"""

import os
from datetime import datetime
from flask import (render_template, redirect, url_for, request,
                   flash, session, current_app)
from flask_login import login_required, current_user
from app import db
from app.routes.archive import archive_bp
from app.models.archive import ArchiveRecord
from app.models.center  import Center
from app.utils.audit     import log_action
from app.utils.decorators import role_required

# مجلد حفظ الصور الممسوحة
SCAN_UPLOAD_FOLDER = os.path.join('app', 'static', 'archive_scans')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tif', 'tiff'}


def _allowed_file(filename):
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS)


def _save_scan(file, record_id):
    """حفظ الصورة الممسوحة وإعادة المسار النسبي"""
    os.makedirs(SCAN_UPLOAD_FOLDER, exist_ok=True)
    ext      = file.filename.rsplit('.', 1)[1].lower()
    filename = f'archive_{record_id}_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.{ext}'
    filepath = os.path.join(SCAN_UPLOAD_FOLDER, filename)
    file.save(filepath)
    return filename


# ══════════════════════════════════════════════════════════════
#  قائمة السجلات المؤرشفة
# ══════════════════════════════════════════════════════════════
@archive_bp.route('/')
@login_required
def index():
    page     = request.args.get('page',     1,    type=int)
    search   = request.args.get('search',   '').strip()
    doc_type = request.args.get('doc_type', '').strip()
    status   = request.args.get('status',   '').strip()
    year     = request.args.get('year',     '',   ).strip()
    lang     = session.get('lang', 'ar')

    query = ArchiveRecord.query

    # فلترة حسب الدور
    if current_user.role == 'officer' and current_user.center_id:
        query = query.filter_by(center_id=current_user.center_id)
    elif current_user.role == 'region_mgr' and current_user.center:
        ids   = [c.id for c in Center.query.filter_by(
                    region=current_user.center.region).all()]
        query = query.filter(ArchiveRecord.center_id.in_(ids))

    # فلاتر البحث
    if search:
        query = query.filter(
            ArchiveRecord.person_name.ilike(f'%{search}%') |
            ArchiveRecord.original_number.ilike(f'%{search}%') |
            ArchiveRecord.father_name.ilike(f'%{search}%')
        )
    if doc_type:
        query = query.filter_by(doc_type=doc_type)
    if status:
        query = query.filter_by(transcription_status=status)
    if year and year.isdigit():
        query = query.filter_by(original_year=int(year))

    records = query.order_by(
        ArchiveRecord.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    # إحصاءات سريعة
    stats = {
        'total':       ArchiveRecord.query.count(),
        'pending':     ArchiveRecord.query.filter_by(transcription_status='pending').count(),
        'done':        ArchiveRecord.query.filter_by(transcription_status='done').count(),
        'verified':    ArchiveRecord.query.filter_by(transcription_status='verified').count(),
        'with_scan':   ArchiveRecord.query.filter(
                           ArchiveRecord.scan_file.isnot(None)).count(),
    }

    return render_template('archive/index.html',
                           records=records,
                           stats=stats,
                           search=search,
                           doc_type=doc_type,
                           status=status,
                           year=year,
                           lang=lang)


# ══════════════════════════════════════════════════════════════
#  إضافة سجل أرشيف جديد
# ══════════════════════════════════════════════════════════════
@archive_bp.route('/new', methods=['GET', 'POST'])
@login_required
@role_required('officer', 'region_mgr', 'admin')
def new():
    centers = Center.query.filter_by(is_active=True).all()
    lang    = session.get('lang', 'ar')

    if request.method == 'POST':
        f = request.form

        # تحديد المركز
        if current_user.role == 'officer':
            center_id = current_user.center_id
        else:
            center_id = f.get('center_id', type=int)

        try:
            record = ArchiveRecord(
                doc_type     = f['doc_type'],
                doc_subtype  = f.get('doc_subtype', '').strip() or None,

                original_number = f.get('original_number', '').strip() or None,
                original_date   = datetime.strptime(f['original_date'], '%Y-%m-%d').date()
                                  if f.get('original_date') else None,
                original_year   = int(f['original_year'])
                                  if f.get('original_year', '').isdigit() else None,
                original_center = f.get('original_center', '').strip() or None,
                original_region = f.get('original_region', '').strip() or None,

                person_name      = f['person_name'].strip(),
                person_name_fr   = f.get('person_name_fr', '').strip() or None,
                person_birth_year= int(f['person_birth_year'])
                                   if f.get('person_birth_year', '').isdigit() else None,
                father_name      = f.get('father_name', '').strip() or None,
                mother_name      = f.get('mother_name', '').strip() or None,

                transcription        = f.get('transcription', '').strip() or None,
                transcription_status = f.get('transcription_status', 'pending'),

                source_type    = f.get('source_type', 'paper'),
                register_volume= f.get('register_volume', '').strip() or None,
                register_page  = f.get('register_page',  '').strip() or None,
                register_entry = f.get('register_entry', '').strip() or None,

                center_id      = center_id,
                digitized_by   = current_user.id,
                notes          = f.get('notes', '').strip() or None,
                is_confidential= 'is_confidential' in f,
            )
            db.session.add(record)
            db.session.flush()  # للحصول على الـ ID قبل الصورة

            # رفع الصورة إن وُجدت
            file = request.files.get('scan_file')
            if file and file.filename and _allowed_file(file.filename):
                record.scan_file = _save_scan(file, record.id)
            elif file and file.filename:
                flash('نوع الملف غير مدعوم. يُقبل: PNG, JPG, PDF, TIFF', 'warning')

            db.session.commit()
            log_action('CREATE', 'archive_records', record_id=record.id,
                       new_data=record.to_dict())
            flash(f'تم حفظ السجل بنجاح — {record.person_name}', 'success')
            return redirect(url_for('archive.detail', record_id=record.id))

        except Exception as e:
            db.session.rollback()
            flash(f'خطأ أثناء الحفظ: {str(e)}', 'danger')

    return render_template('archive/new.html',
                           centers=centers,
                           lang=lang)


# ══════════════════════════════════════════════════════════════
#  تفاصيل سجل أرشيف
# ══════════════════════════════════════════════════════════════
@archive_bp.route('/<int:record_id>')
@login_required
def detail(record_id):
    record = ArchiveRecord.query.get_or_404(record_id)
    lang   = session.get('lang', 'ar')

    # جلب السجل الرقمي المرتبط إن وُجد
    linked = None
    if record.linked_record_id and record.linked_doc_type:
        try:
            if record.linked_doc_type == 'birth':
                from app.models.birth import Birth
                linked = Birth.query.get(record.linked_record_id)
            elif record.linked_doc_type == 'marriage':
                from app.models.marriage import Marriage
                linked = Marriage.query.get(record.linked_record_id)
            elif record.linked_doc_type == 'death':
                from app.models.death import Death
                linked = Death.query.get(record.linked_record_id)
            elif record.linked_doc_type == 'divorce':
                from app.models.divorce import Divorce
                linked = Divorce.query.get(record.linked_record_id)
        except Exception:
            pass

    return render_template('archive/detail.html',
                           record=record,
                           linked=linked,
                           lang=lang)


# ══════════════════════════════════════════════════════════════
#  تعديل سجل أرشيف
# ══════════════════════════════════════════════════════════════
@archive_bp.route('/<int:record_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('officer', 'region_mgr', 'admin')
def edit(record_id):
    record  = ArchiveRecord.query.get_or_404(record_id)
    centers = Center.query.filter_by(is_active=True).all()
    lang    = session.get('lang', 'ar')

    if request.method == 'POST':
        old_data = record.to_dict()
        f = request.form
        try:
            record.doc_type         = f['doc_type']
            record.doc_subtype      = f.get('doc_subtype', '').strip() or None
            record.original_number  = f.get('original_number', '').strip() or None
            record.original_date    = datetime.strptime(f['original_date'], '%Y-%m-%d').date() \
                                      if f.get('original_date') else None
            record.original_year    = int(f['original_year']) \
                                      if f.get('original_year', '').isdigit() else None
            record.original_center  = f.get('original_center', '').strip() or None
            record.original_region  = f.get('original_region', '').strip() or None
            record.person_name      = f['person_name'].strip()
            record.person_name_fr   = f.get('person_name_fr', '').strip() or None
            record.person_birth_year= int(f['person_birth_year']) \
                                      if f.get('person_birth_year', '').isdigit() else None
            record.father_name      = f.get('father_name', '').strip() or None
            record.mother_name      = f.get('mother_name', '').strip() or None
            record.transcription    = f.get('transcription', '').strip() or None
            record.transcription_status = f.get('transcription_status', record.transcription_status)
            record.source_type      = f.get('source_type', 'paper')
            record.register_volume  = f.get('register_volume', '').strip() or None
            record.register_page    = f.get('register_page',  '').strip() or None
            record.register_entry   = f.get('register_entry', '').strip() or None
            record.notes            = f.get('notes', '').strip() or None
            record.is_confidential  = 'is_confidential' in f

            # رفع صورة جديدة
            file = request.files.get('scan_file')
            if file and file.filename and _allowed_file(file.filename):
                record.scan_file = _save_scan(file, record.id)

            db.session.commit()
            log_action('UPDATE', 'archive_records', record_id=record.id,
                       old_data=old_data, new_data=record.to_dict())
            flash('تم تحديث السجل بنجاح', 'success')
            return redirect(url_for('archive.detail', record_id=record.id))

        except Exception as e:
            db.session.rollback()
            flash(f'خطأ: {str(e)}', 'danger')

    return render_template('archive/new.html',
                           record=record,
                           centers=centers,
                           edit=True,
                           lang=lang)


# ══════════════════════════════════════════════════════════════
#  تحديث حالة النسخ فقط (AJAX أو POST سريع)
# ══════════════════════════════════════════════════════════════
@archive_bp.route('/<int:record_id>/set-status', methods=['POST'])
@login_required
@role_required('officer', 'region_mgr', 'admin')
def set_status(record_id):
    record = ArchiveRecord.query.get_or_404(record_id)
    new_status = request.form.get('status', '').strip()
    valid = ['pending', 'in_progress', 'done', 'verified']

    if new_status not in valid:
        flash('حالة غير صالحة', 'danger')
        return redirect(url_for('archive.detail', record_id=record_id))

    record.transcription_status = new_status

    # إذا تحقق → سجّل مَن تحقق ومتى
    if new_status == 'verified':
        record.verified_by = current_user.id
        record.verified_at = datetime.utcnow()

    db.session.commit()
    log_action('UPDATE', 'archive_records', record_id=record.id,
               new_data={'transcription_status': new_status})
    flash(f'تم تحديث الحالة إلى: {record.status_label_ar}', 'success')
    return redirect(url_for('archive.detail', record_id=record_id))


# ══════════════════════════════════════════════════════════════
#  ربط سجل أرشيف بسجل رقمي موجود
# ══════════════════════════════════════════════════════════════
@archive_bp.route('/<int:record_id>/link', methods=['POST'])
@login_required
@role_required('officer', 'region_mgr', 'admin')
def link_record(record_id):
    record     = ArchiveRecord.query.get_or_404(record_id)
    linked_type= request.form.get('linked_doc_type', '').strip()
    linked_id  = request.form.get('linked_record_id', '').strip()

    if not linked_type or not linked_id or not linked_id.isdigit():
        flash('بيانات الربط غير مكتملة', 'danger')
        return redirect(url_for('archive.detail', record_id=record_id))

    record.linked_doc_type   = linked_type
    record.linked_record_id  = int(linked_id)
    db.session.commit()
    log_action('UPDATE', 'archive_records', record_id=record.id,
               new_data={'linked_doc_type': linked_type,
                         'linked_record_id': linked_id})
    flash('تم ربط السجل الأرشيفي بالسجل الرقمي بنجاح', 'success')
    return redirect(url_for('archive.detail', record_id=record_id))
