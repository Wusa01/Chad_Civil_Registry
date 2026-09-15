from flask import render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import login_required, current_user
from app import db
from app.routes.documents import documents_bp
from app.models.document import Document
from app.models.birth import Birth
from app.models.marriage import Marriage
from app.models.death import Death
from app.models.divorce import Divorce
from app.utils.audit import log_action


# ==================== التحقق من وثيقة عبر QR ====================
@documents_bp.route('/verify/<token>')
def verify(token):
    document = Document.query.filter_by(qr_code=token).first()

    if not document:
        lang = session.get('lang', 'ar')
        return render_template('documents/verify.html',
                               valid=False, lang=lang,
                               message='الوثيقة غير موجودة في النظام')

    if not document.is_valid:
        lang = session.get('lang', 'ar')
        return render_template('documents/verify.html',
                               valid=False, lang=lang,
                               message='هذه الوثيقة ملغاة أو غير صالحة')

    # جلب بيانات الوثيقة حسب نوعها
    record = None
    if document.doc_type == 'birth':
        record = Birth.query.get(document.ref_id)
    elif document.doc_type == 'marriage':
        record = Marriage.query.get(document.ref_id)
    elif document.doc_type == 'death':
        record = Death.query.get(document.ref_id)
    elif document.doc_type == 'divorce':
        record = Divorce.query.get(document.ref_id)
    if not record:
        lang = session.get('lang', 'ar')
        return render_template('documents/verify.html',
                               valid=False, lang=lang,
                               message='بيانات الوثيقة غير موجودة')

    log_action('VERIFY', 'documents', record_id=document.id)

    lang = session.get('lang', 'ar')
    return render_template('documents/verify.html',
                           valid=True,
                           document=document,
                           record=record,
                           lang=lang)


# ==================== إلغاء وثيقة ====================
@documents_bp.route('/invalidate/<int:doc_id>', methods=['POST'])
@login_required
def invalidate(doc_id):
    from app.utils.decorators import role_required
    document = Document.query.get_or_404(doc_id)

    if current_user.role not in ['admin', 'region_mgr']:
        flash('ليس لديك صلاحية لإلغاء الوثائق', 'danger')
        return redirect(url_for('auth.dashboard'))

    document.is_valid = False
    db.session.commit()
    log_action('INVALIDATE', 'documents', record_id=doc_id)
    flash('تم إلغاء الوثيقة بنجاح', 'success')
    return redirect(request.referrer or url_for('auth.dashboard'))


# ==================== قائمة الوثائق المُصدَرة ====================
@documents_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    doc_type = request.args.get('type', '').strip()

    query = Document.query

    if doc_type in ['birth', 'marriage', 'death', 'divorce']:
        query = query.filter_by(doc_type=doc_type)

    documents = query.order_by(Document.issued_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    lang = session.get('lang', 'ar')
    return render_template('documents/list.html',
                           documents=documents,
                           doc_type=doc_type,
                           lang=lang)


# ==================== API: التحقق السريع ====================
@documents_bp.route('/api/verify/<token>')
def api_verify(token):
    document = Document.query.filter_by(qr_code=token).first()

    if not document or not document.is_valid:
        return jsonify({'valid': False, 'message': 'وثيقة غير صالحة'}), 404

    record = None
    name   = ''

    if document.doc_type == 'birth':
        record = Birth.query.get(document.ref_id)
        name   = record.child_full_name if record else ''
    elif document.doc_type == 'marriage':
        record = Marriage.query.get(document.ref_id)
        name   = f'{record.husband_full_name} & {record.wife_full_name}' if record else ''
    elif document.doc_type == 'death':
        record = Death.query.get(document.ref_id)
        name   = record.deceased_full_name if record else ''
    elif document.doc_type == 'divorce':
        record = Divorce.query.get(document.ref_id)
        name   = f'{record.husband_full_name} & {record.wife_full_name}' if record else ''
    return jsonify({
        'valid':     True,
        'doc_type':  document.doc_type,
        'issued_at': str(document.issued_at),
        'name':      name,
        'qr_code':   token
    })
