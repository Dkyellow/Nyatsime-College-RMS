from flask import render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from app.student import student_bp
from app.models import db, Student, Report
from app.services.pdf_service import generate_report_card_pdf
from functools import wraps
from datetime import date


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


@student_bp.route('/')
@student_bp.route('/dashboard')
@student_required
def dashboard():
    student = current_student()
    if not student:
        flash('No student profile is linked to your account. Please contact the school office.', 'warning')
        return redirect(url_for('auth.logout'))

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
                           class_size=class_size)


@student_bp.route('/results')
@student_required
def results():
    student = current_student()
    if not student:
        return redirect(url_for('student.dashboard'))

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
                           selected_year=year)


@student_bp.route('/report/<int:report_id>')
@student_required
def view_report(report_id):
    student = current_student()
    if not student:
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
                           class_size=class_size)


@student_bp.route('/report/<int:report_id>/download')
@student_required
def download_report(report_id):
    student = current_student()
    if not student:
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
            'Content-Disposition': f'attachment; filename=nyatsime_report_{student.admission_number}_{report.academic_term}_{report.academic_year}.pdf'
        }
    )
