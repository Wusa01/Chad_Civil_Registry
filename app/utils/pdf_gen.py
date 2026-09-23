"""
pdf_gen.py — توليد شهادات PDF بدعم كامل للغة العربية
جمهورية تشاد — نظام الحالة المدنية
"""

import os
from io import BytesIO
import base64

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, Image, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

from arabic_reshaper import reshape
from bidi.algorithm import get_display

from app.utils.helpers import format_date_ar
from app.utils.qr_gen import generate_qr_image

# ---------------------------------------------------------------------------
# إعداد الخط العربي
# ---------------------------------------------------------------------------
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(BASE_DIR, 'static', 'fonts', 'Amiri-Regular.ttf')

AR_FONT = 'Helvetica'  # fallback

try:
    pdfmetrics.registerFont(TTFont('Amiri', FONT_PATH))
    AR_FONT = 'Amiri'
except Exception as e:
    print("[pdf_gen] تحذير: تعذر تحميل خط Amiri —", e)

# ---------------------------------------------------------------------------
# دالة معالجة النص العربي
# ---------------------------------------------------------------------------
def ar(text):
    """
    تحويل النص العربي ليظهر بشكل صحيح في ReportLab:
    1. arabic_reshaper  -> يصل الحروف (reshaping)
    2. get_display      -> يعكس الاتجاه (BiDi)
    """
    if not text or not isinstance(text, str):
        return text or ''
    try:
        return get_display(reshape(text))
    except Exception:
        return text

# ---------------------------------------------------------------------------
# ألوان الهوية البصرية لتشاد
# ---------------------------------------------------------------------------
CHAD_BLUE   = colors.HexColor('#003082')
CHAD_YELLOW = colors.HexColor('#FCDD09')
CHAD_RED    = colors.HexColor('#C60C30')
GRAY_LIGHT  = colors.HexColor('#F8F8F8')
BLUE_LIGHT  = colors.HexColor('#E8EFFF')

# ---------------------------------------------------------------------------
# الأنماط (Styles)
# ---------------------------------------------------------------------------
def _make_styles():
    base = getSampleStyleSheet()

    title = ParagraphStyle(
        'AR_Title',
        parent=base['Normal'],
        fontName=AR_FONT,
        fontSize=14,
        leading=20,
        textColor=CHAD_BLUE,
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    subtitle = ParagraphStyle(
        'AR_Subtitle',
        parent=base['Normal'],
        fontName=AR_FONT,
        fontSize=10,
        leading=15,
        textColor=colors.HexColor('#333333'),
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    section = ParagraphStyle(
        'AR_Section',
        parent=base['Normal'],
        fontName=AR_FONT,
        fontSize=11,
        leading=16,
        textColor=CHAD_BLUE,
        alignment=TA_RIGHT,
        spaceBefore=6,
        spaceAfter=2,
    )
    footer = ParagraphStyle(
        'AR_Footer',
        parent=base['Normal'],
        fontName=AR_FONT,
        fontSize=9,
        leading=14,
        alignment=TA_RIGHT,
    )
    small = ParagraphStyle(
        'AR_Small',
        parent=base['Normal'],
        fontName=AR_FONT,
        fontSize=7,
        leading=10,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    return title, subtitle, section, footer, small


def _cell_style():
    base = getSampleStyleSheet()
    return ParagraphStyle(
        'AR_Cell',
        parent=base['Normal'],
        fontName=AR_FONT,
        fontSize=9,
        leading=13,
        alignment=TA_RIGHT,
    )


def _label_style():
    base = getSampleStyleSheet()
    return ParagraphStyle(
        'AR_Label',
        parent=base['Normal'],
        fontName=AR_FONT,
        fontSize=9,
        leading=13,
        textColor=CHAD_BLUE,
        alignment=TA_RIGHT,
    )

# ---------------------------------------------------------------------------
# مساعدات بناء الجداول
# ---------------------------------------------------------------------------
def _flag_strip(col_w):
    """شريط ألوان العلم التشادي"""
    tbl = Table([['', '', '']], colWidths=[col_w] * 3, rowHeights=[0.45 * cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), CHAD_BLUE),
        ('BACKGROUND', (1, 0), (1, 0), CHAD_YELLOW),
        ('BACKGROUND', (2, 0), (2, 0), CHAD_RED),
        ('LINEABOVE',  (0, 0), (-1, 0), 0.5, colors.white),
        ('LINEBELOW',  (0, 0), (-1, 0), 0.5, colors.white),
    ]))
    return tbl


def _data_table(rows, col_w_value, col_w_label, bg=GRAY_LIGHT):
    """جدول بيانات ثنائي العمود"""
    label_s = _label_style()
    cell_s  = _cell_style()
    data = []
    for value, label in rows:
        v_cell = Paragraph(ar(str(value)), cell_s) if isinstance(value, str) else value
        l_cell = Paragraph(ar(label), label_s)
        data.append([v_cell, l_cell])

    tbl = Table(data, colWidths=[col_w_value, col_w_label])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',   (1, 0), (1, -1), bg),
        ('GRID',         (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ALIGN',        (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',   (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
        ('LEFTPADDING',  (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _header(story, doc_title_ar, doc_title_fr, title_s, subtitle_s, usable_w):
    """رأس مشترك لكل الشهادات"""
    story.append(Paragraph(ar('جمهورية تشاد'), title_s))
    story.append(Paragraph("Republique du Tchad", title_s))
    story.append(Paragraph(ar('مركز الاحوال المدنسة التشادية'), subtitle_s))
    story.append(Paragraph(
        "Centre d'etat civil tchadien",
        subtitle_s
    ))
    story.append(Spacer(1, 0.25 * cm))
    story.append(_flag_strip(usable_w / 3))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(ar(doc_title_ar) + " — " + doc_title_fr, title_s))
    story.append(HRFlowable(
        width='100%', thickness=1.5, color=CHAD_BLUE, spaceAfter=6
    ))


def _footer_with_qr(story, qr_code_token, officer_name,
                    footer_s, small_s, usable_w):
    """ذيل مشترك: QR + توقيع"""
    qr_b64, verify_url = generate_qr_image(qr_code_token)
    qr_img = Image(
        BytesIO(base64.b64decode(qr_b64)), width=2.5 * cm, height=2.5 * cm
    )

    lbl_officer = ar('ضابط الحالة المدنية / Officier d etat civil:')
    lbl_sign    = ar('التوقيع / Signature:')
    name_val    = ar(str(officer_name))
    sign_blank  = '_______________________'

    officer_text = (
        lbl_officer + '<br/>' +
        name_val + '<br/><br/>' +
        lbl_sign + '  ' + sign_blank
    )

    sig_para = Paragraph(officer_text, footer_s)

    foot_tbl = Table(
        [[qr_img, sig_para]],
        colWidths=[3.2 * cm, usable_w - 3.2 * cm]
    )
    foot_tbl.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',         (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('BACKGROUND',   (0, 0), (0, 0),   GRAY_LIGHT),
        ('TOPPADDING',   (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
        ('LEFTPADDING',  (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))

    verify_label = ar('للتحقق من صحة هذه الوثيقة:')
    story.append(Spacer(1, 0.6 * cm))
    story.append(foot_tbl)
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(verify_label + '  ' + verify_url, small_s))


# ---------------------------------------------------------------------------
# 1. شهادة الميلاد
# ---------------------------------------------------------------------------
def generate_birth_pdf(birth, document):
    buffer = BytesIO()
    LM = RM = 1.5 * cm
    TM = BM = 1.5 * cm
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=RM, leftMargin=LM,
        topMargin=TM, bottomMargin=BM
    )
    usable_w = A4[0] - LM - RM
    title_s, subtitle_s, section_s, footer_s, small_s = _make_styles()
    story = []

    _header(story, 'شهادة ميلاد', 'Acte de Naissance',
            title_s, subtitle_s, usable_w)

    story.append(Paragraph(ar('معلومات التسجيل'), section_s))
    center_ar = birth.center.name_ar if birth.center else '—'
    center_fr = birth.center.name_fr if birth.center else '—'
    story.append(_data_table([
        (birth.certificate_number,    'رقم الشهادة / N Acte'),
        (center_ar,                   'مركز الحالة المدنية / Centre'),
        (center_fr,                   'Centre (francais)'),
        (format_date_ar(birth.registration_date), 'تاريخ التسجيل / Date enregistrement'),
    ], usable_w * 0.55, usable_w * 0.45, bg=BLUE_LIGHT))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(ar('بيانات المولود — Informations sur l enfant'), section_s))
    gender_ar = 'ذكر / Masculin' if birth.child_gender == 'M' else 'انثى / Feminin'
    story.append(_data_table([
        (birth.child_full_name,           'الاسم الكامل / Nom complet'),
        (gender_ar,                        'الجنس / Sexe'),
        (format_date_ar(birth.birth_date), 'تاريخ الميلاد / Date de naissance'),
        (birth.birth_place,                'مكان الميلاد / Lieu de naissance'),
    ], usable_w * 0.55, usable_w * 0.45))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(ar('بيانات الاب — Informations sur le pere'), section_s))
    father_bdate = format_date_ar(birth.father_birth_date) if birth.father_birth_date else '—'
    story.append(_data_table([
        (birth.father_full_name,      'الاسم الكامل / Nom complet'),
        (birth.father_profession,     'المهنة / Profession'),
        (birth.father_birth_place or '—', 'مكان الميلاد / Lieu de naissance'),
        (father_bdate,                'تاريخ الميلاد / Date de naissance'),
    ], usable_w * 0.55, usable_w * 0.45, bg=BLUE_LIGHT))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(ar('بيانات الام — Informations sur la mere'), section_s))
    mother_bdate = format_date_ar(birth.mother_birth_date) if birth.mother_birth_date else '—'
    story.append(_data_table([
        (birth.mother_full_name,      'الاسم الكامل / Nom complet'),
        (birth.mother_profession,     'المهنة / Profession'),
        (birth.mother_birth_place or '—', 'مكان الميلاد / Lieu de naissance'),
        (mother_bdate,                'تاريخ الميلاد / Date de naissance'),
    ], usable_w * 0.55, usable_w * 0.45))

    if birth.notes:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(ar('ملاحظات / Observations'), section_s))
        story.append(Paragraph(ar(birth.notes), _cell_style()))

    _footer_with_qr(story, document.qr_code, birth.civil_officer,
                    footer_s, small_s, usable_w)
    doc.build(story)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# 2. عقد الزواج
# ---------------------------------------------------------------------------
def generate_marriage_pdf(marriage, document):
    buffer = BytesIO()
    LM = RM = 1.5 * cm
    TM = BM = 1.5 * cm
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=RM, leftMargin=LM,
        topMargin=TM, bottomMargin=BM
    )
    usable_w = A4[0] - LM - RM
    title_s, subtitle_s, section_s, footer_s, small_s = _make_styles()
    story = []

    _header(story, 'عقد زواج', 'Acte de Mariage',
            title_s, subtitle_s, usable_w)

    story.append(Paragraph(ar('معلومات العقد'), section_s))
    center_ar = marriage.center.name_ar if marriage.center else '—'
    reg_date  = format_date_ar(marriage.registration_date) if marriage.registration_date else '—'
    story.append(_data_table([
        (marriage.certificate_number,          'رقم العقد / N Acte'),
        (center_ar,                            'مركز الحالة المدنية / Centre'),
        (format_date_ar(marriage.marriage_date), 'تاريخ الزواج / Date du mariage'),
        (marriage.marriage_place,              'مكان الزواج / Lieu du mariage'),
        (reg_date,                             'تاريخ التسجيل / Date enregistrement'),
    ], usable_w * 0.55, usable_w * 0.45, bg=BLUE_LIGHT))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(ar('بيانات الزوج — Informations sur l epoux'), section_s))
    story.append(_data_table([
        (marriage.husband_full_name,                    'الاسم الكامل / Nom complet'),
        (format_date_ar(marriage.husband_birth_date),   'تاريخ الميلاد / Date de naissance'),
        (marriage.husband_birth_place,                  'مكان الميلاد / Lieu de naissance'),
        (marriage.husband_profession,                   'المهنة / Profession'),
        (marriage.husband_nationality,                  'الجنسية / Nationalite'),
        (marriage.husband_id_number,                    'رقم الهوية / N Identite'),
        (marriage.husband_father_name,                  'اسم الاب / Nom du pere'),
        (marriage.husband_mother_name,                  'اسم الام / Nom de la mere'),
    ], usable_w * 0.55, usable_w * 0.45))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(ar('بيانات الزوجة — Informations sur l epouse'), section_s))
    story.append(_data_table([
        (marriage.wife_full_name,                    'الاسم الكامل / Nom complet'),
        (format_date_ar(marriage.wife_birth_date),   'تاريخ الميلاد / Date de naissance'),
        (marriage.wife_birth_place,                  'مكان الميلاد / Lieu de naissance'),
        (marriage.wife_profession,                   'المهنة / Profession'),
        (marriage.wife_nationality,                  'الجنسية / Nationalite'),
        (marriage.wife_id_number,                    'رقم الهوية / N Identite'),
        (marriage.wife_father_name,                  'اسم الاب / Nom du pere'),
        (marriage.wife_mother_name,                  'اسم الام / Nom de la mere'),
    ], usable_w * 0.55, usable_w * 0.45, bg=BLUE_LIGHT))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(ar('تفاصيل العقد — Details du contrat'), section_s))
    m_type_map = {
        'monogamy': 'زواج احادي / Monogamie',
        'polygamy': 'تعدد زوجات / Polygamie',
    }
    m_type_ar = m_type_map.get(marriage.marriage_type, marriage.marriage_type)
    if marriage.dowry_mentioned and marriage.dowry_amount:
        dowry_text = str(int(marriage.dowry_amount)) + ' FCFA'
    elif marriage.dowry_mentioned:
        dowry_text = 'مذكور / Mentionne'
    else:
        dowry_text = '—'
    dispensation = 'نعم / Oui' if marriage.age_dispensation else 'لا / Non'
    story.append(_data_table([
        (m_type_ar,    'نوع الزواج / Type'),
        (dowry_text,   'المهر / Dot'),
        (dispensation, 'اعفاء السن / Dispense d age'),
    ], usable_w * 0.55, usable_w * 0.45))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(ar('الشهود — Temoins'), section_s))
    story.append(_data_table([
        (marriage.witness1_name, 'الشاهد الاول / Temoin 1'),
        (marriage.witness1_id,   'رقم هوية الشاهد الاول / N Identite'),
        (marriage.witness2_name, 'الشاهد الثاني / Temoin 2'),
        (marriage.witness2_id,   'رقم هوية الشاهد الثاني / N Identite'),
    ], usable_w * 0.55, usable_w * 0.45, bg=BLUE_LIGHT))

    _footer_with_qr(story, document.qr_code, marriage.civil_officer,
                    footer_s, small_s, usable_w)
    doc.build(story)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# 3. شهادة الوفاة
# ---------------------------------------------------------------------------
def generate_death_pdf(death, document):
    buffer = BytesIO()
    LM = RM = 1.5 * cm
    TM = BM = 1.5 * cm
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=RM, leftMargin=LM,
        topMargin=TM, bottomMargin=BM
    )
    usable_w = A4[0] - LM - RM
    title_s, subtitle_s, section_s, footer_s, small_s = _make_styles()
    story = []

    _header(story, 'شهادة وفاة', 'Acte de Deces',
            title_s, subtitle_s, usable_w)

    story.append(Paragraph(ar('معلومات التسجيل'), section_s))
    center_ar = death.center.name_ar if death.center else '—'
    story.append(_data_table([
        (death.certificate_number,              'رقم الشهادة / N Acte'),
        (center_ar,                             'مركز الحالة المدنية / Centre'),
        (format_date_ar(death.registration_date), 'تاريخ التسجيل / Date enregistrement'),
    ], usable_w * 0.55, usable_w * 0.45, bg=BLUE_LIGHT))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(ar('بيانات المتوفى — Informations sur le defunt'), section_s))
    gender_ar = 'ذكر / Masculin' if death.deceased_gender == 'M' else 'انثى / Feminin'
    place_type_map = {
        'hospital': 'مستشفى / Hopital',
        'home':     'المنزل / Domicile',
        'other':    'اخرى / Autre',
    }
    place_type_ar = place_type_map.get(death.death_place_type, death.death_place_type)
    dec_bdate  = format_date_ar(death.deceased_birth_date) if death.deceased_birth_date else '—'
    age_text   = (str(death.deceased_age) + ' سنة') if death.deceased_age else '—'
    story.append(_data_table([
        (death.deceased_full_name, 'الاسم الكامل / Nom complet'),
        (gender_ar,                'الجنس / Sexe'),
        (dec_bdate,                'تاريخ الميلاد / Date de naissance'),
        (age_text,                 'العمر / Age'),
        (death.usual_residence,    'محل الاقامة / Lieu de residence'),
    ], usable_w * 0.55, usable_w * 0.45))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(ar('بيانات الوفاة — Informations sur le deces'), section_s))
    story.append(_data_table([
        (format_date_ar(death.death_date), 'تاريخ الوفاة / Date du deces'),
        (death.death_place,                'مكان الوفاة / Lieu du deces'),
        (place_type_ar,                    'نوع المكان / Type de lieu'),
        (death.cause_of_death,             'سبب الوفاة / Cause du deces'),
        (death.certifier_name,             'اسم المصدق / Nom du certificateur'),
    ], usable_w * 0.55, usable_w * 0.45, bg=BLUE_LIGHT))

    if death.notes:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(ar('ملاحظات / Observations'), section_s))
        story.append(Paragraph(ar(death.notes), _cell_style()))

    _footer_with_qr(story, document.qr_code, death.civil_officer,
                    footer_s, small_s, usable_w)
    doc.build(story)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# 4. وثيقة الطلاق
# ---------------------------------------------------------------------------
def generate_divorce_pdf(divorce, document):
    from app.models.center import Center
    buffer = BytesIO()
    LM = RM = 1.5 * cm
    TM = BM = 1.5 * cm
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=RM, leftMargin=LM,
        topMargin=TM, bottomMargin=BM
    )
    usable_w = A4[0] - LM - RM
    title_s, subtitle_s, section_s, footer_s, small_s = _make_styles()
    story = []

    _header(story, 'وثيقة طلاق', 'Acte de Divorce',
            title_s, subtitle_s, usable_w)

    divorce_type_label = {
        'mutual':      'بالتراضي / Consentement mutuel',
        'judicial':    'قضائي / Judiciaire',
        'repudiation': 'طلاق رجعي/بائن / Répudiation',
    }.get(divorce.divorce_type, divorce.divorce_type)

    center = Center.query.get(divorce.center_id)
    center_ar = center.name_ar if center else '—'

    story.append(Paragraph(ar('بيانات وثيقة الطلاق'), section_s))
    doc_rows = [
        (divorce.certificate_number,   'رقم الوثيقة / N Acte'),
        (format_date_ar(divorce.divorce_date), 'تاريخ الطلاق / Date du divorce'),
        (divorce.divorce_place,        'مكان الطلاق / Lieu'),
        (divorce_type_label,           'نوع الطلاق / Type'),
        (center_ar,                    'مركز الحالة المدنية / Centre'),
        (divorce.civil_officer,        'ضابط الحالة المدنية / Officier'),
    ]
    if divorce.marriage_cert_number:
        doc_rows.append((divorce.marriage_cert_number, 'رقم عقد الزواج / N Acte Mariage'))

    story.append(_data_table(doc_rows, usable_w * 0.55, usable_w * 0.45, bg=BLUE_LIGHT))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(ar('بيانات الزوج / المطلِّق'), section_s))
    story.append(_data_table([
        (divorce.husband_full_name,   'الاسم الكامل / Nom complet'),
        (format_date_ar(divorce.husband_birth_date), 'تاريخ الميلاد / Date de naissance'),
        (divorce.husband_id_number,   'رقم الهوية / N Identite'),
    ], usable_w * 0.55, usable_w * 0.45))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(ar('بيانات الزوجة / المطلَّقة'), section_s))
    story.append(_data_table([
        (divorce.wife_full_name,      'الاسم الكامل / Nom complet'),
        (format_date_ar(divorce.wife_birth_date), 'تاريخ الميلاد / Date de naissance'),
        (divorce.wife_id_number,      'رقم الهوية / N Identite'),
    ], usable_w * 0.55, usable_w * 0.45, bg=BLUE_LIGHT))

    _footer_with_qr(story, document.qr_code, divorce.civil_officer,
                    footer_s, small_s, usable_w)
    doc.build(story)
    buffer.seek(0)
    return buffer
