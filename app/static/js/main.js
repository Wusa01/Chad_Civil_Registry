/* ============================================================
   نظام السجل المدني التشادي — main.js
   ============================================================ */

'use strict';

/* ===== 1. مؤشر التحميل ===== */
function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.classList.add('show');
}
function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.classList.remove('show');
}

/* ===== 2. تأكيد العمليات الحساسة ===== */
function confirmAction(message) {
    return window.confirm(message || 'هل أنت متأكد من هذه العملية؟');
}

/* ===== 3. إغلاق التنبيهات تلقائياً ===== */
function autoCloseAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });
}

/* ===== 4. البحث الفوري ===== */
function setupInstantSearch() {
    const searchInput = document.getElementById('instantSearch');
    if (!searchInput) return;

    let timeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            const form = searchInput.closest('form');
            if (form) form.submit();
        }, 600);
    });
}

/* ===== 5. معاينة PDF في نافذة جديدة ===== */
function openPDF(url) {
    window.open(url, '_blank', 'width=900,height=700,scrollbars=yes');
}

/* ===== 6. نسخ النص ===== */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast(
            document.documentElement.lang === 'ar'
                ? 'تم النسخ!'
                : 'Copié!',
            'success'
        );
    }).catch(() => {
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
        showToast('Copié!', 'success');
    });
}

/* ===== 7. إشعار Toast ===== */
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer')
        || createToastContainer();

    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-bg-${type} border-0 show`;
    toastEl.setAttribute('role', 'alert');
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body fw-semibold">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto"
                    data-bs-dismiss="toast"></button>
        </div>`;

    toastContainer.appendChild(toastEl);

    setTimeout(() => {
        toastEl.classList.remove('show');
        setTimeout(() => toastEl.remove(), 300);
    }, 3000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

/* ===== 8. التحقق من النماذج ===== */
function setupFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

/* ===== 9. التحقق من تطابق كلمة المرور ===== */
function setupPasswordMatch() {
    const newPass     = document.getElementById('newPassword');
    const confirmPass = document.getElementById('confirmPassword');
    if (!newPass || !confirmPass) return;

    function checkMatch() {
        if (newPass.value && confirmPass.value) {
            if (newPass.value !== confirmPass.value) {
                confirmPass.setCustomValidity(
                    document.documentElement.lang === 'ar'
                        ? 'كلمة المرور غير متطابقة'
                        : 'Les mots de passe ne correspondent pas'
                );
                confirmPass.classList.add('is-invalid');
            } else {
                confirmPass.setCustomValidity('');
                confirmPass.classList.remove('is-invalid');
                confirmPass.classList.add('is-valid');
            }
        }
    }
    newPass.addEventListener('input',     checkMatch);
    confirmPass.addEventListener('input', checkMatch);
}

/* ===== 10. إظهار/إخفاء حقل المهر ===== */
function setupDowryToggle() {
    const dowryCheckbox = document.getElementById('dowryMentioned');
    const dowryAmount   = document.getElementById('dowryAmountGroup');
    if (!dowryCheckbox || !dowryAmount) return;

    function toggle() {
        dowryAmount.style.display = dowryCheckbox.checked ? 'block' : 'none';
    }
    dowryCheckbox.addEventListener('change', toggle);
    toggle();
}

/* ===== 11. حساب العمر تلقائياً ===== */
function setupAgeCalculator() {
    const birthDateInput = document.getElementById('deceasedBirthDate');
    const deathDateInput = document.getElementById('deathDate');
    const ageInput       = document.getElementById('deceasedAge');

    if (!birthDateInput || !deathDateInput || !ageInput) return;

    function calculateAge() {
        if (birthDateInput.value && deathDateInput.value) {
            const birth = new Date(birthDateInput.value);
            const death = new Date(deathDateInput.value);
            let age = death.getFullYear() - birth.getFullYear();
            const m = death.getMonth() - birth.getMonth();
            if (m < 0 || (m === 0 && death.getDate() < birth.getDate())) age--;
            if (age >= 0) ageInput.value = age;
        }
    }
    birthDateInput.addEventListener('change', calculateAge);
    deathDateInput.addEventListener('change', calculateAge);
}

/* ===== 12. تأكيد التعليق والحذف ===== */
function setupDangerForms() {
    const dangerForms = document.querySelectorAll('form[data-confirm]');
    dangerForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const message = form.dataset.confirm ||
                (document.documentElement.lang === 'ar'
                    ? 'هل أنت متأكد؟'
                    : 'Êtes-vous sûr?');
            if (!window.confirm(message)) {
                e.preventDefault();
            }
        });
    });
}

/* ===== 13. أزرار النسخ ===== */
function setupCopyButtons() {
    document.querySelectorAll('[data-copy]').forEach(btn => {
        btn.addEventListener('click', () => {
            copyToClipboard(btn.dataset.copy);
        });
    });
}

/* ===== 14. تفعيل Tooltips ===== */
function setupTooltips() {
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(el => new bootstrap.Tooltip(el));
}

/* ===== 15. مؤشر التحميل عند إرسال النماذج ===== */
function setupLoadingOnSubmit() {
    const forms = document.querySelectorAll('form:not([data-no-loading])');
    forms.forEach(form => {
        form.addEventListener('submit', () => {
            const submitBtn = form.querySelector('[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML =
                    `<span class="spinner-border spinner-border-sm me-2"></span>
                     ${document.documentElement.lang === 'ar' ? 'جاري الحفظ...' : 'Enregistrement...'}`;
            }
        });
    });
}
/* ===== تهيئة كل شيء عند تحميل الصفحة ===== */
document.addEventListener('DOMContentLoaded', () => {
    autoCloseAlerts();
    setupInstantSearch();
    setupFormValidation();
    setupPasswordMatch();
    setupDowryToggle();
    setupAgeCalculator();
    setupDangerForms();
    setupCopyButtons();
    setupTooltips();
    setupLoadingOnSubmit();

    // إضافة مؤشر التحميل للصفحة
    /*const overlay = document.createElement('div');
    overlay.id        = 'loadingOverlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="spinner-chad"></div>
        <p class="text-chad-blue fw-semibold">
            ${document.documentElement.lang === 'ar' ? 'جاري التحميل...' : 'Chargement...'}
        </p>`;
    document.body.appendChild(overlay);*/
});
