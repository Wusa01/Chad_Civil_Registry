import qrcode
import uuid
import os
from io import BytesIO
import base64


def generate_qr_token():
    """
    توليد رمز فريد للوثيقة
    """
    return str(uuid.uuid4()).replace('-', '').upper()[:16]


def _get_base_url():
    """
    قراءة عنوان الخادم من إعدادات Flask
    مع fallback لمتغير البيئة أو localhost للتطوير
    """
    try:
        from flask import current_app, request
        # إذا كنا داخل request context نستخدم عنوان الخادم الفعلي
        if request:
            return request.host_url.rstrip('/')
    except RuntimeError:
        pass

    # قراءة من متغير البيئة
    base_url = os.environ.get('APP_BASE_URL', '').strip().rstrip('/')
    if base_url:
        return base_url

    # fallback للتطوير فقط
    return 'http://localhost:5000'


def generate_qr_image(token, base_url=None):
    """
    توليد صورة QR Code بصيغة base64
    لتضمينها مباشرة في PDF أو HTML
    """
    if base_url is None:
        base_url = _get_base_url()

    verify_url = f'{base_url}/documents/verify/{token}'

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=6,
        border=2
    )
    qr.add_data(verify_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return img_base64, verify_url


def save_qr_image(token, save_dir='app/static/qrcodes', base_url=None):
    """
    حفظ صورة QR Code على القرص
    """
    if base_url is None:
        base_url = _get_base_url()

    os.makedirs(save_dir, exist_ok=True)
    verify_url = f'{base_url}/documents/verify/{token}'

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=6,
        border=2
    )
    qr.add_data(verify_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')
    file_path = os.path.join(save_dir, f'{token}.png')
    img.save(file_path)

    return file_path

