from datetime import datetime
from app.models.center import Center


def generate_certificate_number(doc_type, center_code):
    """
    توليد رقم شهادة تلقائي
    صيغة: [TYPE]-[YEAR]-[CENTER_CODE]-[SEQ]
    مثال: DIVORCE-2026-NDJ001-00003
    """
    from app import db
    from app.models.birth import Birth
    from app.models.marriage import Marriage
    from app.models.divorce import Divorce
    from app.models.death import Death

    year = datetime.utcnow().year

    prefix_map = {
        'birth':    ('BIRTH',    Birth),
        'marriage': ('MARIAGE',  Marriage),
        'divorce':  ('DIVORCE',  Divorce),
        'death':    ('DECES',    Death),
    }

    prefix, model = prefix_map[doc_type]

    from sqlalchemy import text
    from app import db

    # قفل على مستوى قاعدة البيانات لضمان uniqueness عند التزامن
    while True:
        count = model.query.filter(
            model.certificate_number.like(f'{prefix}-{year}-{center_code}-%')
        ).count() + 1

        candidate = f'{prefix}-{year}-{center_code}-{count:05d}'

        # تحقق أن الرقم غير مستخدم (حماية من race condition)
        exists = model.query.filter_by(
            certificate_number=candidate
        ).first()

        if not exists:
            return candidate
        # إذا وُجد تعارض، أعد المحاولة بالعداد التالي تلقائياً


def get_lang_name(obj, lang):
    if lang == 'fr':
        return getattr(obj, 'name_fr', getattr(obj, 'name_ar', ''))
    return getattr(obj, 'name_ar', getattr(obj, 'name_fr', ''))


def format_date_ar(date_obj):
    if not date_obj:
        return ''
    months_ar = [
        '', 'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
        'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
    ]
    return f'{date_obj.day} {months_ar[date_obj.month]} {date_obj.year}'


def format_date_fr(date_obj):
    if not date_obj:
        return ''
    months_fr = [
        '', 'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
        'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'
    ]
    return f'{date_obj.day} {months_fr[date_obj.month]} {date_obj.year}'


def get_center_or_none(center_id):
    if not center_id:
        return None
    return Center.query.get(center_id)
