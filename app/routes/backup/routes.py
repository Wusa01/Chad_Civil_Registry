from flask import render_template, redirect, url_for, flash, session, send_file, request
from flask_login import login_required, current_user
from datetime import datetime
from app.routes.backup import backup_bp
from app.utils.decorators import role_required
from app.utils.audit import log_action
from app.utils import backup as bk


# ══════════════════════════════════════════════════════════════
#  صفحة إدارة النسخ الاحتياطية
# ══════════════════════════════════════════════════════════════
@backup_bp.route('/')
@login_required
@role_required('admin')
def index():
    backups  = bk.list_local_backups()
    db_stats = bk.get_db_stats()
    lang     = session.get('lang', 'ar')
    return render_template('admin/backup.html',
                           backups=backups,
                           db_stats=db_stats,
                           lang=lang)


# ══════════════════════════════════════════════════════════════
#  تحميل نسخة .db (ملف قاعدة البيانات الكامل)
# ══════════════════════════════════════════════════════════════
@backup_bp.route('/download/db')
@login_required
@role_required('admin')
def download_db():
    try:
        path, size = bk.backup_sqlite_file()
        log_action('EXPORT', 'backup', new_data={'type': 'sqlite_db', 'size': size})

        import os
        return send_file(
            path,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=os.path.basename(path)
        )
    except Exception as e:
        flash(f'خطأ أثناء إنشاء النسخة: {str(e)}', 'danger')
        return redirect(url_for('backup.index'))


# ══════════════════════════════════════════════════════════════
#  تحميل نسخة JSON (جميع الجداول في ZIP)
# ══════════════════════════════════════════════════════════════
@backup_bp.route('/download/json')
@login_required
@role_required('admin')
def download_json():
    try:
        zip_buffer, total_rows = bk.backup_json()
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        log_action('EXPORT', 'backup',
                   new_data={'type': 'json_zip', 'total_rows': total_rows})

        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'civil_registry_json_{ts}.zip'
        )
    except Exception as e:
        flash(f'خطأ أثناء التصدير: {str(e)}', 'danger')
        return redirect(url_for('backup.index'))


# ══════════════════════════════════════════════════════════════
#  تحميل نسخة كاملة ZIP (.db + JSON)
# ══════════════════════════════════════════════════════════════
@backup_bp.route('/download/full')
@login_required
@role_required('admin')
def download_full():
    try:
        zip_buffer, ts = bk.backup_full_zip()
        log_action('EXPORT', 'backup', new_data={'type': 'full_zip'})

        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'civil_registry_full_{ts}.zip'
        )
    except Exception as e:
        flash(f'خطأ أثناء إنشاء النسخة الكاملة: {str(e)}', 'danger')
        return redirect(url_for('backup.index'))


# ══════════════════════════════════════════════════════════════
#  حفظ نسخة محلية على الخادم
# ══════════════════════════════════════════════════════════════
@backup_bp.route('/save-local', methods=['POST'])
@login_required
@role_required('admin')
def save_local():
    try:
        fname, size = bk.save_local_backup(keep_last=10)
        size_kb = round(size / 1024, 1)
        log_action('CREATE', 'backup',
                   new_data={'type': 'local', 'file': fname, 'size_kb': size_kb})
        flash(f'تم حفظ النسخة الاحتياطية محلياً: {fname} ({size_kb} KB)', 'success')
    except Exception as e:
        flash(f'خطأ: {str(e)}', 'danger')
    return redirect(url_for('backup.index'))


# ══════════════════════════════════════════════════════════════
#  حذف نسخة محلية
# ══════════════════════════════════════════════════════════════
@backup_bp.route('/delete-local', methods=['POST'])
@login_required
@role_required('admin')
def delete_local():
    import os
    fname = request.form.get('filename', '').strip()

    # حماية: فقط ملفات .db تبدأ بـ civil_registry_
    if not fname.startswith('civil_registry_') or not fname.endswith('.db'):
        flash('اسم ملف غير صالح', 'danger')
        return redirect(url_for('backup.index'))

    fpath = os.path.join(bk.BACKUP_DIR, fname)
    if os.path.exists(fpath):
        os.remove(fpath)
        log_action('DELETE', 'backup', new_data={'file': fname})
        flash(f'تم حذف النسخة: {fname}', 'warning')
    else:
        flash('الملف غير موجود', 'danger')

    return redirect(url_for('backup.index'))
