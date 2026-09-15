"""
backup.py — إدارة النسخ الاحتياطية لنظام الحالة المدنية التشادي
يدعم: SQLite dump كامل + JSON لكل جدول منفرداً + ضغط ZIP
"""

import os
import json
import shutil
import sqlite3
from datetime import datetime
from io import BytesIO
import zipfile

# ─── مسار مجلد النسخ الاحتياطية ───────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP_DIR  = os.path.join(BASE_DIR, 'backups')
DB_PATH     = os.path.join(BASE_DIR, 'instance', 'civil_registry.db')

# الجداول المطلوب نسخها بالترتيب (يراعي Foreign Keys)
TABLES = [
    'centers',
    'users',
    'births',
    'marriages',
    'divorces',
    'deaths',
    'documents',
    'citizen_requests',
    'audit_logs',
]


def _ensure_backup_dir():
    """إنشاء مجلد النسخ الاحتياطية إن لم يكن موجوداً"""
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _timestamp():
    """توليد طابع زمني للاسم"""
    return datetime.utcnow().strftime('%Y%m%d_%H%M%S')


# ══════════════════════════════════════════════════════════════
#  1. نسخة SQLite كاملة (.db)
# ══════════════════════════════════════════════════════════════
def backup_sqlite_file():
    """
    نسخ ملف قاعدة البيانات مباشرة.
    الأسرع والأكثر موثوقية — يحافظ على كل شيء.
    يعيد: (مسار_الملف, حجم_البايت)
    """
    _ensure_backup_dir()

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f'قاعدة البيانات غير موجودة: {DB_PATH}')

    ts       = _timestamp()
    dst_name = f'civil_registry_{ts}.db'
    dst_path = os.path.join(BACKUP_DIR, dst_name)

    # استخدام SQLite Online Backup API لضمان سلامة البيانات
    src_conn = sqlite3.connect(DB_PATH)
    dst_conn = sqlite3.connect(dst_path)
    src_conn.backup(dst_conn)
    src_conn.close()
    dst_conn.close()

    size = os.path.getsize(dst_path)
    return dst_path, size


# ══════════════════════════════════════════════════════════════
#  2. تصدير JSON لكل جدول
# ══════════════════════════════════════════════════════════════
def backup_json():
    """
    تصدير كل جدول كملف JSON منفرد داخل ZIP واحد.
    مفيد للاستيراد في أنظمة أخرى أو قواعد بيانات مختلفة.
    يعيد: (BytesIO للـ ZIP, عدد_السجلات_الإجمالي)
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f'قاعدة البيانات غير موجودة: {DB_PATH}')

    conn        = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor      = conn.cursor()
    total_rows  = 0
    ts          = _timestamp()
    zip_buffer  = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:

        # ملف meta.json — معلومات النسخة
        meta = {
            'system':    'نظام الحالة المدنية التشادية',
            'version':   'civil_registry061',
            'timestamp': ts,
            'tables':    TABLES,
        }
        zf.writestr('meta.json', json.dumps(meta, ensure_ascii=False, indent=2))

        # جدول بجدول
        for table in TABLES:
            try:
                cursor.execute(f'SELECT * FROM {table}')
                rows = [dict(row) for row in cursor.fetchall()]
                total_rows += len(rows)
                content = json.dumps(rows, ensure_ascii=False, indent=2,
                                     default=str)  # default=str يحوّل Date/DateTime
                zf.writestr(f'{table}.json', content)
            except sqlite3.OperationalError:
                # الجدول غير موجود — تخطَّ
                pass

    conn.close()
    zip_buffer.seek(0)
    return zip_buffer, total_rows


# ══════════════════════════════════════════════════════════════
#  3. نسخة ZIP تجمع .db + JSON
# ══════════════════════════════════════════════════════════════
def backup_full_zip():
    """
    أشمل نسخة: ملف .db + جميع ملفات JSON في ZIP واحد.
    يعيد: BytesIO
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f'قاعدة البيانات غير موجودة: {DB_PATH}')

    ts         = _timestamp()
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:

        # أضف ملف .db
        zf.write(DB_PATH, arcname=f'civil_registry_{ts}.db')

        # أضف JSON لكل جدول
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        for table in TABLES:
            try:
                cursor.execute(f'SELECT * FROM {table}')
                rows    = [dict(row) for row in cursor.fetchall()]
                content = json.dumps(rows, ensure_ascii=False, indent=2,
                                     default=str)
                zf.writestr(f'json/{table}.json', content)
            except sqlite3.OperationalError:
                pass

        conn.close()

        # أضف meta.json
        meta = {
            'system':    'نظام الحالة المدنية التشادية',
            'version':   'civil_registry061',
            'timestamp': ts,
        }
        zf.writestr('meta.json', json.dumps(meta, ensure_ascii=False, indent=2))

    zip_buffer.seek(0)
    return zip_buffer, ts


# ══════════════════════════════════════════════════════════════
#  4. حفظ نسخة محلية + تنظيف القديم
# ══════════════════════════════════════════════════════════════
def save_local_backup(keep_last=10):
    """
    يحفظ نسخة .db محلياً في مجلد backups/
    ويحذف النسخ الأقدم من (keep_last) للتوفير في المساحة.
    يعيد: (اسم_الملف, الحجم_بالبايت)
    """
    path, size = backup_sqlite_file()
    _cleanup_old_backups(keep_last)
    return os.path.basename(path), size


def _cleanup_old_backups(keep_last=10):
    """حذف النسخ القديمة والاحتفاظ بآخر (keep_last) فقط"""
    _ensure_backup_dir()
    files = sorted([
        f for f in os.listdir(BACKUP_DIR)
        if f.startswith('civil_registry_') and f.endswith('.db')
    ])
    # احذف الأقدم
    while len(files) > keep_last:
        old = os.path.join(BACKUP_DIR, files.pop(0))
        try:
            os.remove(old)
        except OSError:
            pass


# ══════════════════════════════════════════════════════════════
#  5. قائمة النسخ المحفوظة محلياً
# ══════════════════════════════════════════════════════════════
def list_local_backups():
    """
    يعيد قائمة بالنسخ المحفوظة محلياً مرتبة من الأحدث للأقدم.
    كل عنصر: {'name': str, 'size': int, 'created_at': str}
    """
    _ensure_backup_dir()
    result = []
    for fname in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if fname.startswith('civil_registry_') and fname.endswith('.db'):
            fpath = os.path.join(BACKUP_DIR, fname)
            stat  = os.stat(fpath)
            result.append({
                'name':       fname,
                'size':       stat.st_size,
                'size_kb':    round(stat.st_size / 1024, 1),
                'created_at': datetime.fromtimestamp(stat.st_mtime)
                                      .strftime('%Y-%m-%d %H:%M:%S'),
            })
    return result


# ══════════════════════════════════════════════════════════════
#  6. إحصاءات قاعدة البيانات
# ══════════════════════════════════════════════════════════════
def get_db_stats():
    """
    يعيد dict بعدد السجلات في كل جدول + حجم ملف DB.
    """
    stats = {}
    if not os.path.exists(DB_PATH):
        return stats

    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for table in TABLES:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            stats[table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            stats[table] = 0

    conn.close()
    stats['_db_size_kb'] = round(os.path.getsize(DB_PATH) / 1024, 1)
    return stats
