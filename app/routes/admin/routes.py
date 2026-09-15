from flask import render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.routes.admin import admin_bp
from app.models.user import User
from app.models.center import Center
from app.models.audit_log import AuditLog
from app.utils.audit import log_action
from app.utils.decorators import role_required


# ==================== لوحة الإدارة ====================
@admin_bp.route('/')
@login_required
@role_required('admin')
def index():
    total_users   = User.query.count()
    total_centers = Center.query.count()
    active_users  = User.query.filter_by(is_active=True).count()
    recent_logs   = AuditLog.query.order_by(
        AuditLog.created_at.desc()
    ).limit(10).all()

    lang = session.get('lang', 'ar')
    return render_template('admin/index.html',
                           total_users=total_users,
                           total_centers=total_centers,
                           active_users=active_users,
                           recent_logs=recent_logs,
                           lang=lang)


# ==================== قائمة المستخدمين ====================
@admin_bp.route('/users')
@login_required
@role_required('admin')
def users():
    page   = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()

    query = User.query
    if search:
        query = query.filter(
            User.username.ilike(f'%{search}%')  |
            User.full_name.ilike(f'%{search}%')
        )

    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    lang = session.get('lang', 'ar')
    return render_template('admin/users.html',
                           users=users, search=search, lang=lang)


# ==================== إضافة مستخدم ====================
@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def new_user():
    centers = Center.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        username  = request.form['username'].strip()
        full_name = request.form['full_name'].strip()
        role      = request.form['role']
        center_id = request.form.get('center_id', type=int)
        password  = request.form['password']
        confirm   = request.form['confirm_password']

        # التحقق من البيانات
        if User.query.filter_by(username=username).first():
            flash('اسم المستخدم موجود مسبقاً', 'danger')
            return render_template('admin/user_form.html', centers=centers)

        if password != confirm:
            flash('كلمة المرور غير متطابقة', 'danger')
            return render_template('admin/user_form.html', centers=centers)

        if len(password) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'danger')
            return render_template('admin/user_form.html', centers=centers)

        if role == 'officer' and not center_id:
            flash('يجب تحديد المركز عند إنشاء حساب موظف', 'danger')
            return render_template('admin/user_form.html', centers=centers, lang=session.get('lang', 'ar'))

        try:
            user = User(
                username  = username,
                full_name = full_name,
                role      = role,
                center_id = center_id if center_id else None,
                is_active = True
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            log_action('CREATE', 'users',
                       record_id=user.id, new_data=user.to_dict())
            flash(f'تم إنشاء المستخدم {username} بنجاح', 'success')
            return redirect(url_for('admin.users'))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

    lang = session.get('lang', 'ar')
    return render_template('admin/user_form.html', centers=centers, lang=lang)


# ==================== تعديل مستخدم ====================
@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(user_id):
    user    = User.query.get_or_404(user_id)
    centers = Center.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        old_data = user.to_dict()
        try:
            user.full_name = request.form['full_name'].strip()
            user.role      = request.form['role']
            user.center_id = request.form.get('center_id', type=int) or None
            user.is_active = 'is_active' in request.form

            if user.role == 'officer' and not user.center_id:
                flash('يجب تحديد المركز عند تعيين الدور موظف', 'danger')
                return render_template('admin/user_form.html',
                                       user=user, centers=centers, edit=True, lang=lang)

            # تغيير كلمة المرور إن أُدخلت
            new_pass = request.form.get('new_password', '').strip()
            if new_pass:
                if len(new_pass) < 6:
                    flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'danger')
                    return render_template('admin/user_form.html',
                                           user=user, centers=centers, edit=True)
                user.set_password(new_pass)

            db.session.commit()
            log_action('UPDATE', 'users', record_id=user.id,
                       old_data=old_data, new_data=user.to_dict())
            flash('تم تحديث بيانات المستخدم بنجاح', 'success')
            return redirect(url_for('admin.users'))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

    lang = session.get('lang', 'ar')
    return render_template('admin/user_form.html',
                           user=user, centers=centers,
                           edit=True, lang=lang)


# ==================== تعليق / تفعيل مستخدم ====================
@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('لا يمكنك تعليق حسابك الخاص', 'danger')
        return redirect(url_for('admin.users'))

    user.is_active = not user.is_active
    db.session.commit()

    status = 'تفعيل' if user.is_active else 'تعليق'
    log_action('UPDATE', 'users', record_id=user.id,
               new_data={'is_active': user.is_active})
    flash(f'تم {status} حساب {user.username} بنجاح', 'success')
    return redirect(url_for('admin.users'))


# ==================== إعادة تعيين كلمة المرور ====================
@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@role_required('admin')
def reset_password(user_id):
    user         = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', '').strip()

    if not new_password or len(new_password) < 6:
        flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'danger')
        return redirect(url_for('admin.users'))

    user.set_password(new_password)
    db.session.commit()
    log_action('UPDATE', 'users', record_id=user.id,
               new_data={'action': 'reset_password'})
    flash(f'تم إعادة تعيين كلمة مرور {user.username} بنجاح', 'success')
    return redirect(url_for('admin.users'))


# ==================== حذف مستخدم ====================
@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # لا يمكن حذف نفسك
    if user.id == current_user.id:
        flash('لا يمكنك حذف حسابك الخاص', 'danger')
        return redirect(url_for('admin.users'))

    # لا يمكن حذف مدير عام آخر (حماية إضافية)
    if user.role == 'admin':
        flash('لا يمكن حذف حساب مدير عام آخر. قم بتغيير دوره أولاً إن أردت حذفه.', 'danger')
        return redirect(url_for('admin.users'))

    # التحقق من كلمة مرور المدير قبل الحذف
    confirm_password = request.form.get('confirm_password', '').strip()
    if not current_user.check_password(confirm_password):
        flash('كلمة المرور غير صحيحة. لم يتم الحذف.', 'danger')
        return redirect(url_for('admin.users'))

    try:
        username  = user.username
        full_name = user.full_name
        old_data  = user.to_dict()

        # فك ارتباط السجلات المرتبطة (births / marriages / deaths / documents / logs)
        from app.models.birth    import Birth
        from app.models.marriage import Marriage
        from app.models.death    import Death
        from app.models.document import Document
        from app.models.audit_log import AuditLog as AL

        Birth.query.filter_by(registered_by=user.id).update({'registered_by': None})
        Marriage.query.filter_by(registered_by=user.id).update({'registered_by': None})
        Death.query.filter_by(registered_by=user.id).update({'registered_by': None})
        Document.query.filter_by(issued_by=user.id).update({'issued_by': None})
        AL.query.filter_by(user_id=user.id).update({'user_id': None})

        db.session.delete(user)
        db.session.commit()

        log_action('DELETE', 'users', record_id=user_id, old_data=old_data)
        flash(f'تم حذف المستخدم "{full_name}" ({username}) نهائياً', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء الحذف: {str(e)}', 'danger')

    return redirect(url_for('admin.users'))


# ==================== قائمة المراكز ====================
@admin_bp.route('/centers')
@login_required
@role_required('admin')
def centers():
    page   = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()

    query = Center.query
    if search:
        query = query.filter(
            Center.name_ar.ilike(f'%{search}%') |
            Center.code.ilike(f'%{search}%')    |
            Center.region.ilike(f'%{search}%')
        )

    centers = query.order_by(Center.name_ar).paginate(
        page=page, per_page=20, error_out=False
    )

    lang = session.get('lang', 'ar')
    return render_template('admin/centers.html',
                           centers=centers, search=search, lang=lang)


# ==================== إضافة مركز ====================
@admin_bp.route('/centers/new', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def new_center():
    if request.method == 'POST':
        code = request.form['code'].strip().upper()

        if Center.query.filter_by(code=code).first():
            flash('رمز المركز موجود مسبقاً', 'danger')
            return render_template('admin/center_form.html')

        try:
            center = Center(
                name_ar    = request.form['name_ar'].strip(),
                name_fr    = request.form['name_fr'].strip(),
                region     = request.form['region'].strip(),
                department = request.form['department'].strip(),
                code       = code,
                is_active  = True
            )
            db.session.add(center)
            db.session.commit()
            log_action('CREATE', 'centers',
                       record_id=center.id, new_data=center.to_dict())
            flash(f'تم إضافة المركز {center.name_ar} بنجاح', 'success')
            return redirect(url_for('admin.centers'))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

    lang = session.get('lang', 'ar')
    return render_template('admin/center_form.html', lang=lang)


# ==================== تعديل مركز ====================
@admin_bp.route('/centers/<int:center_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_center(center_id):
    center = Center.query.get_or_404(center_id)

    if request.method == 'POST':
        old_data = center.to_dict()
        try:
            center.name_ar    = request.form['name_ar'].strip()
            center.name_fr    = request.form['name_fr'].strip()
            center.region     = request.form['region'].strip()
            center.department = request.form['department'].strip()
            center.is_active  = 'is_active' in request.form

            db.session.commit()
            log_action('UPDATE', 'centers', record_id=center.id,
                       old_data=old_data, new_data=center.to_dict())
            flash('تم تحديث بيانات المركز بنجاح', 'success')
            return redirect(url_for('admin.centers'))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

    lang = session.get('lang', 'ar')
    return render_template('admin/center_form.html',
                           center=center, edit=True, lang=lang)

# ==================== حذف مركز ====================
@admin_bp.route('/centers/<int:center_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_center(center_id):
    center = Center.query.get_or_404(center_id)

    # التحقق من كلمة مرور المدير
    confirm_password = request.form.get('confirm_password', '').strip()
    if not current_user.check_password(confirm_password):
        flash('كلمة المرور غير صحيحة. لم يتم الحذف.', 'danger')
        return redirect(url_for('admin.centers'))

    # لا يمكن حذف مركز به موظفون نشطون
    active_officers = User.query.filter_by(center_id=center.id, is_active=True).count()
    if active_officers > 0:
        flash(f'لا يمكن حذف المركز لوجود {active_officers} موظف نشط مرتبط به. قم بنقلهم أو تعليق حساباتهم أولاً.', 'danger')
        return redirect(url_for('admin.centers'))

    try:
        name    = center.name_ar
        old_data = center.to_dict()

        # فك ارتباط الموظفين غير النشطين
        User.query.filter_by(center_id=center.id).update({'center_id': None})

        db.session.delete(center)
        db.session.commit()

        log_action('DELETE', 'centers', record_id=center_id, old_data=old_data)
        flash(f'تم حذف المركز "{name}" نهائياً', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء الحذف: {str(e)}', 'danger')

    return redirect(url_for('admin.centers'))

# ==================== سجل العمليات ====================
@admin_bp.route('/audit-log')
@login_required
@role_required('admin')
def audit_log():
    page      = request.args.get('page', 1, type=int)
    action    = request.args.get('action', '').strip()
    table     = request.args.get('table', '').strip()

    query = AuditLog.query

    if action:
        query = query.filter_by(action=action)
    if table:
        query = query.filter_by(table_name=table)

    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=30, error_out=False
    )

    actions = ['CREATE', 'UPDATE', 'DELETE', 'EXPORT',
               'LOGIN', 'LOGOUT', 'VERIFY', 'INVALIDATE']
    tables  = ['births', 'marriages', 'deaths',
               'users', 'centers', 'documents']

    lang = session.get('lang', 'ar')
    return render_template('admin/audit_log.html',
                           logs=logs, actions=actions,
                           tables=tables, lang=lang,
                           selected_action=action,
                           selected_table=table)
