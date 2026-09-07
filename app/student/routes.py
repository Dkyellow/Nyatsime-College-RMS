from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, Response, session
from flask_login import login_required, current_user, logout_user
from app.student import student_bp
from app.models import db, Student, Report, Payment, CalendarEvent
from app.services.pdf_service import generate_report_card_pdf
from app.services import periods
from functools import wraps


def student_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'student':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def current_student():
    """Resolve the authenticated user's own student record server-side.

    Student identity is ALWAYS derived from the session - never from a
    student id supplied by the client - so a student can only ever access
    their own academic records.
    """
    return Student.query.filter_by(user_id=current_user.id, is_active=True).first()


def check_student_payment():
    """Check if the current student has paid fees for the current term.

    Returns (is_paid, payment_object) tuple.
    """
    student = current_student()
    if not student:
        return True, None

    default_term, default_year = periods.get_default_period()
    if not default_term or not default_year:
        return True, None

    payment = Payment.query.filter_by(
        student_id=student.id,
        academic_year=default_year,
        academic_term=default_term
    ).first()

    if payment and payment.is_paid:
        return True, payment
    return False, payment


@student_bp.before_request
def check_session_timeout():
    """Auto-logout students after 3 minutes of inactivity."""
    if request.endpoint == 'student.ping':
        return
    user_id = session.get('_user_id')
    if not user_id:
        return
    last = session.get('last_activity')
    if last:
        elapsed = datetime.utcnow().timestamp() - last
        if elapsed > 180:
            logout_user()
            session.clear()
            flash('Session expired due to inactivity. Please log in again.', 'info')
            return redirect(url_for('auth.login'))
    session['last_activity'] = datetime.utcnow().timestamp()


@student_bp.route('/ping', methods=['POST'])
@student_required
def ping():
    """Heartbeat endpoint to keep student session alive."""
    session['last_activity'] = datetime.utcnow().timestamp()
    return '', 204


@student_bp.route('/')
@student_bp.route('/dashboard')
@student_required
def dashboard():
    student = current_student()
    if not student:
        flash('No student profile is linked to your account. Please contact the school office.', 'warning')
        return redirect(url_for('auth.logout'))

    is_paid, payment = check_student_payment()

    reports = Report.query.filter_by(student_id=student.id).order_by(
        Report.academic_year.desc(), Report.academic_term).all()
    latest = next((r for r in reports if r.status == 'published'), None)

    class_size = 0
    if student.class_id:
        from app.models import Student as S
        class_size = S.query.filter_by(class_id=student.class_id, is_active=True).count()

    return render_template('student/dashboard.html',
                           student=student,
                           reports=reports,
                           latest=latest,
                           class_size=class_size,
                           is_paid=is_paid)


@student_bp.route('/results')
@student_required
def results():
    student = current_student()
    if not student:
        return redirect(url_for('student.dashboard'))

    is_paid, payment = check_student_payment()

    year = request.args.get('year', '', type=str)
    query = Report.query.filter_by(student_id=student.id)
    if year:
        query = query.filter(Report.academic_year == year)
    reports = query.order_by(Report.academic_year.desc(), Report.academic_term).all()

    years = sorted({r.academic_year for r in Report.query.filter_by(
        student_id=student.id).with_entities(Report.academic_year).all()}, reverse=True)

    return render_template('student/results.html',
                           student=student,
                           reports=reports,
                           years=years,
                           selected_year=year,
                           is_paid=is_paid)


@student_bp.route('/report/<int:report_id>')
@student_required
def view_report(report_id):
    student = current_student()
    if not student:
        return redirect(url_for('student.dashboard'))

    is_paid, payment = check_student_payment()

    if not is_paid:
        flash('Your fees for the current term have not been settled. Report cards are unavailable.', 'warning')
        return redirect(url_for('student.dashboard'))

    # Ownership enforced against the session-derived student record
    report = Report.query.filter_by(id=report_id, student_id=student.id).first()
    if not report:
        flash('Report not found in your records.', 'danger')
        return redirect(url_for('student.results'))

    marks = report.marks
    class_size = 0
    if report.class_id:
        from app.models import Student as S
        class_size = S.query.filter_by(class_id=report.class_id, is_active=True).count()

    return render_template('student/report.html',
                           student=student,
                           report=report,
                           marks=marks,
                           class_size=class_size,
                           is_paid=is_paid)


@student_bp.route('/report/<int:report_id>/download')
@student_required
def download_report(report_id):
    student = current_student()
    if not student:
        return redirect(url_for('student.dashboard'))

    is_paid, payment = check_student_payment()

    if not is_paid:
        flash('Your fees for the current term have not been settled. Report cards are unavailable.', 'warning')
        return redirect(url_for('student.dashboard'))

    report = Report.query.filter_by(
        id=report_id, student_id=student.id, status='published').first()
    if not report:
        flash('Only published reports can be downloaded.', 'info')
        return redirect(url_for('student.results'))

    pdf_content = generate_report_card_pdf(report)
    return Response(
        pdf_content,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename=report_{student.admission_number}_{report.academic_term}_{report.academic_year}.pdf'
        }
    )


@student_bp.route('/calendar')
@student_required
def calendar():
    student = current_student()
    if not student:
        return redirect(url_for('student.dashboard'))

    import calendar as cal
    from datetime import date, timedelta

    today = date.today()
    month = request.args.get('month', today.month, type=int)
    year = request.args.get('year', today.year, type=int)

    month = max(1, min(12, month))
    year = max(2020, min(2099, year))

    cal_month = cal.monthcalendar(year, month)
    month_name = cal.month_name[month]

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    events = CalendarEvent.query.filter_by(is_active=True).order_by(CalendarEvent.start_date).all()

    events_by_date = {}
    for e in events:
        d = e.start_date.isoformat()
        events_by_date.setdefault(d, []).append(e)
        if e.end_date and e.end_date != e.start_date:
            current = e.start_date + timedelta(days=1)
            while current <= e.end_date:
                events_by_date.setdefault(current.isoformat(), []).append(e)
                current += timedelta(days=1)

    return render_template('student/calendar.html',
                           student=student,
                           events=events,
                           cal_month=cal_month,
                           month=month,
                           year=year,
                           month_name=month_name,
                           today=today,
                           events_by_date=events_by_date,
                           prev_month=prev_month,
                           prev_year=prev_year,
                           next_month=next_month,
                           next_year=next_year)
