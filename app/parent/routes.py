from flask import render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from app.parent import parent_bp
from app.models import (
    db, User, Parent, Student, Report, Mark, Subject,
    Class, Grade, EducationLevel, AcademicYear, AcademicTerm,
    ECDAssessmentMark
)
from app.services.pdf_service import generate_report_card_pdf
from functools import wraps


def parent_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'parent':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@parent_bp.route('/')
@parent_bp.route('/dashboard')
@parent_required
def dashboard():
    parent = Parent.query.filter_by(user_id=current_user.id).first()
    children = parent.children

    current_year = AcademicYear.query.filter_by(is_current=True).first()
    current_term = None
    if current_year:
        current_term = AcademicTerm.query.filter_by(
            academic_year_id=current_year.id, is_active=True
        ).order_by(AcademicTerm.display_order.desc()).first()

    return render_template('parent_dashboard.html',
                         parent=parent,
                         children=children,
                         current_year=current_year,
                         current_term=current_term)


@parent_bp.route('/report/<int:student_id>')
@parent_required
def view_report(student_id):
    student = Student.query.get_or_404(student_id)
    parent = Parent.query.filter_by(user_id=current_user.id).first()

    if student.parent_id != parent.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('parent.dashboard'))

    current_year = AcademicYear.query.filter_by(is_current=True).first()
    current_term = None
    if current_year:
        current_term = AcademicTerm.query.filter_by(
            academic_year_id=current_year.id, is_active=True
        ).order_by(AcademicTerm.display_order.desc()).first()
        if not current_term:
            current_term = AcademicTerm.query.filter_by(
                academic_year_id=current_year.id, is_active=True
            ).order_by(AcademicTerm.display_order.desc()).first()

    academic_term = request.args.get('term', current_term.name if current_term else 'Term 1')
    academic_year = request.args.get('year', current_year.name if current_year else '2024/2025')

    report = Report.query.filter_by(
        student_id=student_id,
        academic_term=academic_term,
        academic_year=academic_year,
        status='published'
    ).first()

    if not report:
        flash('No published report found for this period.', 'info')
        return redirect(url_for('parent.dashboard'))

    is_ecd = False
    if report.class_obj and report.class_obj.grade and report.class_obj.grade.education_level:
        is_ecd = report.class_obj.grade.education_level.name == 'ECD'

    if is_ecd:
        ecd_marks = report.ecd_marks
        subjects = []
    else:
        ecd_marks = []
        subjects = report.marks

    academic_years = AcademicYear.query.filter_by(is_active=True).order_by(AcademicYear.name.desc()).all()
    terms = []
    if current_year:
        terms = AcademicTerm.query.filter_by(academic_year_id=current_year.id, is_active=True).order_by(AcademicTerm.display_order).all()

    return render_template('parent_view_report.html',
                         student=student,
                         report=report,
                         is_ecd=is_ecd,
                         ecd_marks=ecd_marks,
                         subjects=subjects,
                         academic_years=academic_years,
                         terms=terms,
                         selected_term=academic_term,
                         selected_year=academic_year)


@parent_bp.route('/report/<int:student_id>/download')
@parent_required
def download_report(student_id):
    student = Student.query.get_or_404(student_id)
    parent = Parent.query.filter_by(user_id=current_user.id).first()

    if student.parent_id != parent.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('parent.dashboard'))

    current_year = AcademicYear.query.filter_by(is_current=True).first()
    current_term = None
    if current_year:
        current_term = AcademicTerm.query.filter_by(
            academic_year_id=current_year.id, is_active=True
        ).order_by(AcademicTerm.display_order.desc()).first()
        if not current_term:
            current_term = AcademicTerm.query.filter_by(
                academic_year_id=current_year.id, is_active=True
            ).order_by(AcademicTerm.display_order.desc()).first()

    academic_term = request.args.get('term', current_term.name if current_term else 'Term 1')
    academic_year = request.args.get('year', current_year.name if current_year else '2024/2025')

    report = Report.query.filter_by(
        student_id=student_id,
        academic_term=academic_term,
        academic_year=academic_year,
        status='published'
    ).first()

    if not report:
        flash('No published report found for this period.', 'info')
        return redirect(url_for('parent.dashboard'))

    pdf_content = generate_report_card_pdf(report)

    return Response(
        pdf_content,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename=report_card_{student.admission_number}_{academic_term}_{academic_year}.pdf'
        }
    )
