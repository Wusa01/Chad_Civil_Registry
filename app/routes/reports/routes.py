from flask import render_template, request, session, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from datetime import datetime, date
from app import db
from app.routes.reports import reports_bp
from app.models.birth import Birth
from app.models.marriage import Marriage
from app.models.death import Death
from app.models.center import Center
from app.utils.decorators import role_required


# ==================== لوحة الإحصاءات ====================
@reports_bp.route('/')
@login_required
@role_required('admin', 'region_mgr')
def index():
    year = request.args.get('year', datetime.utcnow().year, type=int)

    # --- إحصاءات سنوية ---
    def yearly_count(model, year):
        return model.query.filter(
            extract('year', model.created_at) == year
        ).count()

    # تصفية حسب الدور
    def filtered_query(model):
        q = model.query
        if current_user.role == 'region_mgr' and current_user.center:
            center_ids = [c.id for c in Center.query.filter_by(
                region=current_user.center.region
            ).all()]
            q = q.filter(model.center_id.in_(center_ids))
        return q

    # إجماليات
    total_births    = filtered_query(Birth).count()
    total_marriages = filtered_query(Marriage).count()
    total_deaths    = filtered_query(Death).count()

    # إحصاءات هذه السنة
    births_this_year    = filtered_query(Birth).filter(
        extract('year', Birth.created_at) == year
    ).count()
    marriages_this_year = filtered_query(Marriage).filter(
        extract('year', Marriage.created_at) == year
    ).count()
    deaths_this_year    = filtered_query(Death).filter(
        extract('year', Death.created_at) == year
    ).count()

    # --- توزيع شهري ---
    monthly_births = []
    monthly_marriages = []
    monthly_deaths = []

    for month in range(1, 13):
        monthly_births.append(
            filtered_query(Birth).filter(
                extract('year',  Birth.created_at) == year,
                extract('month', Birth.created_at) == month
            ).count()
        )
        monthly_marriages.append(
            filtered_query(Marriage).filter(
                extract('year',  Marriage.created_at) == year,
                extract('month', Marriage.created_at) == month
            ).count()
        )
        monthly_deaths.append(
            filtered_query(Death).filter(
                extract('year',  Death.created_at) == year,
                extract('month', Death.created_at) == month
            ).count()
        )

    # --- توزيع جغرافي (أعلى 10 مراكز) ---
    top_centers_births = db.session.query(
        Center.name_ar,
        func.count(Birth.id).label('total')
    ).join(Birth, Birth.center_id == Center.id)\
     .group_by(Center.id)\
     .order_by(func.count(Birth.id).desc())\
     .limit(10).all()

    # --- توزيع الجنس في المواليد ---
    male_births   = filtered_query(Birth).filter_by(child_gender='M').count()
    female_births = filtered_query(Birth).filter_by(child_gender='F').count()

    # --- أنواع الزواج ---
    monogamy_count  = filtered_query(Marriage).filter_by(marriage_type='monogamy').count()
    polygamy_count  = filtered_query(Marriage).filter_by(marriage_type='polygamy').count()

    # --- أسباب الوفاة الأكثر شيوعاً ---
    top_death_causes = db.session.query(
        Death.cause_of_death,
        func.count(Death.id).label('total')
    ).group_by(Death.cause_of_death)\
     .order_by(func.count(Death.id).desc())\
     .limit(5).all()

    stats = {
        'total_births':       total_births,
        'total_marriages':    total_marriages,
        'total_deaths':       total_deaths,
        'births_this_year':   births_this_year,
        'marriages_this_year':marriages_this_year,
        'deaths_this_year':   deaths_this_year,
        'monthly_births':     monthly_births,
        'monthly_marriages':  monthly_marriages,
        'monthly_deaths':     monthly_deaths,
        'top_centers_births': top_centers_births,
        'male_births':        male_births,
        'female_births':      female_births,
        'monogamy_count':     monogamy_count,
        'polygamy_count':     polygamy_count,
        'top_death_causes':   top_death_causes,
        'year':               year,
    }

    lang = session.get('lang', 'ar')
    return render_template('reports/dashboard.html', stats=stats, lang=lang)


# ==================== تقرير المواليد ====================
@reports_bp.route('/births')
@login_required
@role_required('admin', 'region_mgr')
def births_report():
    year  = request.args.get('year',  datetime.utcnow().year, type=int)
    month = request.args.get('month', 0, type=int)

    query = Birth.query.filter(
        extract('year', Birth.created_at) == year
    )
    if month:
        query = query.filter(extract('month', Birth.created_at) == month)

    if current_user.role == 'region_mgr' and current_user.center:
        center_ids = [c.id for c in Center.query.filter_by(
            region=current_user.center.region
        ).all()]
        query = query.filter(Birth.center_id.in_(center_ids))

    births = query.order_by(Birth.registration_date.desc()).all()
    lang   = session.get('lang', 'ar')

    return render_template('reports/births_report.html',
                           births=births, year=year, month=month, lang=lang)


# ==================== تقرير الوفيات ====================
@reports_bp.route('/deaths')
@login_required
@role_required('admin', 'region_mgr')
def deaths_report():
    year  = request.args.get('year',  datetime.utcnow().year, type=int)
    month = request.args.get('month', 0, type=int)

    query = Death.query.filter(
        extract('year', Death.created_at) == year
    )
    if month:
        query = query.filter(extract('month', Death.created_at) == month)

    if current_user.role == 'region_mgr' and current_user.center:
        center_ids = [c.id for c in Center.query.filter_by(
            region=current_user.center.region
        ).all()]
        query = query.filter(Death.center_id.in_(center_ids))

    deaths = query.order_by(Death.registration_date.desc()).all()
    lang   = session.get('lang', 'ar')

    return render_template('reports/deaths_report.html',
                           deaths=deaths, year=year, month=month, lang=lang)


# ==================== API: بيانات الرسوم البيانية ====================
@reports_bp.route('/api/chart-data')
@login_required
@role_required('admin', 'region_mgr')
def chart_data():
    year = request.args.get('year', datetime.utcnow().year, type=int)

    monthly_data = {'births': [], 'marriages': [], 'deaths': []}

    for month in range(1, 13):
        monthly_data['births'].append(
            Birth.query.filter(
                extract('year',  Birth.created_at) == year,
                extract('month', Birth.created_at) == month
            ).count()
        )
        monthly_data['marriages'].append(
            Marriage.query.filter(
                extract('year',  Marriage.created_at) == year,
                extract('month', Marriage.created_at) == month
            ).count()
        )
        monthly_data['deaths'].append(
            Death.query.filter(
                extract('year',  Death.created_at) == year,
                extract('month', Death.created_at) == month
            ).count()
        )

    return jsonify(monthly_data)
