from flask_mail import Message
from app import mail


def send_reset_email(user, code, lang='ar'):
    """إرسال كود استعادة كلمة المرور (8 أرقام) إلى بريد المستخدم"""

    if lang == 'ar':
        subject = 'كود استعادة كلمة المرور — السجل المدني التشادي'
        body = (
            f"مرحباً {user.full_name}،\n\n"
            "وصلنا طلب لإعادة تعيين كلمة المرور الخاصة بحسابك.\n"
            f"كود التفعيل الخاص بك هو:\n\n{code}\n\n"
            "هذا الكود صالح لمدة 15 دقيقة، ولا تشاركه مع أي شخص.\n"
            "إذا لم تطلب هذا، تجاهل هذه الرسالة ولن يتغيّر شيء.\n\n"
            "— نظام السجل المدني، جمهورية تشاد"
        )
    else:
        subject = 'Code de réinitialisation — État Civil Tchadien'
        body = (
            f"Bonjour {user.full_name},\n\n"
            "Une demande de réinitialisation de mot de passe a été reçue pour votre compte.\n"
            f"Votre code de vérification est :\n\n{code}\n\n"
            "Ce code est valable 15 minutes. Ne le partagez avec personne.\n"
            "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.\n\n"
            "— Système de l'État Civil, République du Tchad"
        )

    msg = Message(subject=subject, recipients=[user.email], body=body)
    mail.send(msg)
