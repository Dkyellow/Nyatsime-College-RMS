import csv
import io
from flask import render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from datetime import datetime
from app.teacher import teacher_bp
from app.models import (
    db, User, Teacher, Student, Class, Subject, Report, Mark,
    Grade, GradeSubject, AcademicYear, AcademicTerm,
    GradingScale
)
from functools import wraps
from app.services.pdf_service import invalidate_report_cache


def teacher_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'teacher':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def calculate_grade(score):
    scales = GradingScale.query.filter_by(is_active=True).order_by(GradingScale.display_order).all()
    for scale in scales:
        if scale.min_score <= score <= scale.max_score:
            return scale.grade_letter
    if score >= 80: return 'A'
    elif score >= 70: return 'B'
    elif score >= 60: return 'C'
    elif score >= 50: return 'D'
    elif score >= 40: return 'E'
    else: return 'U'


def get_grading_scale():
    scales = GradingScale.query.filter_by(is_active=True).order_by(GradingScale.display_order).all()
    return [{'min_score': s.min_score, 'max_score': s.max_score,
             'grade_letter': s.grade_letter, 'description': s.description} for s in scales]


def get_subjects_for_grade(grade_id):
    grade = Grade.query.get(grade_id)
    if grade:
        return grade.subjects
    return Subject.query.all()


def calculate_positions(class_id, term, year):
    reports = Report.query.filter_by(
        class_id=class_id,
        academic_term=term,
        academic_year=year
    ).filter(Report.status.in_(['submitted', 'approved', 'published'])).all()

    reports.sort(key=lambda r: r.average, reverse=True)
    for i, report in enumerate(reports, 1):
        report.position = i


def calculate_grade_positions(grade_id, term, year):
    grade = Grade.query.get(grade_id)
    if not grade:
        return

    class_ids = [c.id for c in grade.classes]
    if not class_ids:
        return

    reports = Report.query.filter(
        Report.class_id.in_(class_ids),
        Report.academic_term == term,
        Report.academic_year == year,
        Report.status.in_(['submitted', 'approved', 'published'])
    ).all()

    reports.sort(key=lambda r: r.average, reverse=True)
    for i, report in enumerate(reports, 1):
        report.grade_position = i


@teacher_bp.route('/')
@teacher_bp.route('/dashboard')
@teacher_required
def dashboard():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    classes = teacher.classes
    total_students = sum(len([s for s in c.students if s.is_active]) for c in classes)
    drafts = 0
    submitted = 0
    published = 0
    for c in classes:
        drafts += Report.query.filter_by(class_id=c.id, status='draft').count()
        submitted += Report.query.filter_by(class_id=c.id, status='submitted').count()
        published += Report.query.filter_by(class_id=c.id, status='published').count()

    current_year = AcademicYear.query.filter_by(is_current=True).first()
    active_term = None
    if current_year:
        active_term = AcademicTerm.query.filter_by(
            academic_year_id=current_year.id, is_active=True).first() or \
            AcademicTerm.query.filter_by(academic_year_id=current_year.id)\
            .order_by(AcademicTerm.display_order.desc()).first()

    recent_results = []
    class_ids = [c.id for c in classes]
    if class_ids:
        recent_results = Report.query.filter(
            Report.class_id.in_(class_ids), Report.status != 'draft'
        ).order_by(Report.updated_at.desc()).limit(8).all()

    return render_template('teacher_dashboard.html',
                           teacher=teacher,
                           classes=classes,
                           total_students=total_students,
                           drafts=drafts,
                           submitted=submitted,
                           published=published,
                           current_year=current_year,
                           active_term=active_term,
                           recent_results=recent_results)


@teacher_bp.route('/class/<int:class_id>')
@teacher_required
def view_class(class_id):
    class_obj = Class.query.get_or_404(class_id)
    students = Student.query.filter_by(class_id=class_id, is_active=True).order_by(Student.admission_number).all()

    grade = class_obj.grade
    subjects = get_subjects_for_grade(grade.id) if grade else Subject.query.all()

    current_year = AcademicYear.query.filter_by(is_current=True).first()
    academic_years = AcademicYear.query.filter_by(is_active=True).order_by(AcademicYear.name.desc()).all()

    terms = []
    if current_year:
        terms = AcademicTerm.query.filter_by(academic_year_id=current_year.id, is_active=True)\
            .order_by(AcademicTerm.display_order).all()

    academic_term = request.args.get('term', terms[0].name if terms else 'Term 1')
    academic_year = request.args.get('year', current_year.name if current_year else '2026')

    # Preload existing reports for the grid
    reports = {r.student_id: r for r in Report.query.filter_by(
        class_id=class_id, academic_term=academic_term, academic_year=academic_year).all()}

    return render_template('view_class.html',
                           class_obj=class_obj,
                           students=students,
                           subjects=subjects,
                           reports=reports,
                           academic_term=academic_term,
                           academic_year=academic_year,
                           grade=grade,
                           academic_years=academic_years,
                           terms=terms)


@teacher_bp.route('/report/<int:student_id>/<int:class_id>')
@teacher_required
def view_report(student_id, class_id):
    student = Student.query.get_or_404(student_id)
    class_obj = Class.query.get_or_404(class_id)

    grade = class_obj.grade

    academic_term = request.args.get('term', 'Term 1')
    academic_year = request.args.get('year', '2026')

    report = Report.query.filter_by(
        student_id=student_id,
        class_id=class_id,
        academic_term=academic_term,
        academic_year=academic_year
    ).first()

    if not report:
        report = Report(
            student_id=student_id,
            class_id=class_id,
            academic_term=academic_term,
            academic_year=academic_year,
            status='draft'
        )
        db.session.add(report)
        db.session.flush()

        subjects = get_subjects_for_grade(grade.id) if grade else Subject.query.all()
        for subject in subjects:
            mark = Mark(report_id=report.id, subject_id=subject.id, score=0, max_score=subject.max_score)
            db.session.add(mark)
        db.session.commit()

    subjects = get_subjects_for_grade(grade.id) if grade else Subject.query.all()
    grading_scale = get_grading_scale()

    current_year = AcademicYear.query.filter_by(is_current=True).first()
    academic_years = AcademicYear.query.filter_by(is_active=True).order_by(AcademicYear.name.desc()).all()
    terms = []
    if current_year:
        terms = AcademicTerm.query.filter_by(academic_year_id=current_year.id, is_active=True)\
            .order_by(AcademicTerm.display_order).all()

    return render_template('view_report.html',
                           student=student,
                           class_obj=class_obj,
                           report=report,
                           subjects=subjects,
                           grading_scale=grading_scale,
                           grade=grade,
                           academic_years=academic_years,
                           terms=terms)


@teacher_bp.route('/class/<int:class_id>/subject-marks')
@teacher_required
def subject_marks(class_id):
    """Fast bulk marks entry: one subject, whole class on a single screen."""
    class_obj = Class.query.get_or_404(class_id)
    students = Student.query.filter_by(class_id=class_id, is_active=True).order_by(Student.admission_number).all()
    grade = class_obj.grade
    subjects = get_subjects_for_grade(grade.id) if grade else Subject.query.all()

    current_year = AcademicYear.query.filter_by(is_current=True).first()
    terms = []
    if current_year:
        terms = AcademicTerm.query.filter_by(academic_year_id=current_year.id, is_active=True)\
            .order_by(AcademicTerm.display_order).all()

    academic_term = request.args.get('term', terms[0].name if terms else 'Term 1')
    academic_year = request.args.get('year', current_year.name if current_year else '2026')
    subject = Subject.query.get(request.args.get('subject_id', type=int)) if subjects else None

    # Existing scores keyed by student
    existing = {}
    if subject:
        reports = Report.query.filter_by(
            class_id=class_id, academic_term=academic_term, academic_year=academic_year).all()
        for r in reports:
            mark = next((m for m in r.marks if m.subject_id == subject.id), None)
            if mark:
                existing[r.student_id] = {'score': mark.score, 'status': r.status}

    return render_template('subject_marks.html',
                           class_obj=class_obj,
                           students=students,
                           subjects=subjects,
                           subject=subject,
                           existing=existing,
                           academic_term=academic_term,
                           academic_year=academic_year,
                           terms=terms,
                           grading_scale=get_grading_scale(),
                           academic_years=AcademicYear.query.filter_by(is_active=True).order_by(AcademicYear.name.desc()).all())


@teacher_bp.route('/class/<int:class_id>/subject-marks/save', methods=['POST'])
@teacher_required
def save_subject_marks(class_id):
    class_obj = Class.query.get_or_404(class_id)
    grade = class_obj.grade

    academic_term = request.form.get('term', 'Term 1')
    academic_year = request.form.get('year', '2026')
    subject_id = request.form.get('subject_id', type=int)

    subject = Subject.query.get_or_404(subject_id) if subject_id else None
    if not subject:
        flash('Select a subject first.', 'danger')
        return redirect(url_for('teacher.subject_marks', class_id=class_id))

    students = Student.query.filter_by(class_id=class_id, is_active=True).all()

    saved = 0
    for student in students:
        raw = request.form.get(f'score_{student.id}', '').strip()
        if raw == '':
            continue
        try:
            score = max(0.0, min(float(raw), float(subject.max_score or 100)))
        except ValueError:
            continue

        report = Report.query.filter_by(
            student_id=student.id,
            class_id=class_id,
            academic_term=academic_term,
            academic_year=academic_year
        ).first()

        if not report:
            report = Report(
                student_id=student.id, class_id=class_id,
                academic_term=academic_term, academic_year=academic_year,
                status='draft'
            )
            db.session.add(report)
            db.session.flush()
            for s in (get_subjects_for_grade(grade.id) if grade else Subject.query.all()):
                db.session.add(Mark(report_id=report.id, subject_id=s.id, score=0, max_score=s.max_score))
            db.session.flush()

        if report.status in ['approved', 'published']:
            continue

        mark = Mark.query.filter_by(report_id=report.id, subject_id=subject.id).first()
        if not mark:
            mark = Mark(report_id=report.id, subject_id=subject.id, max_score=subject.max_score)
            db.session.add(mark)
        mark.score = score
        mark.grade = calculate_grade((score / (mark.max_score or 100)) * 100)
        saved += 1

        scores = [m.score for m in report.marks]
        report.total_marks = sum(scores)
        report.average = sum(scores) / len(scores) if scores else 0
        report.overall_grade = calculate_grade(report.average)

    calculate_positions(class_id, academic_term, academic_year)
    if grade:
        calculate_grade_positions(grade.id, academic_term, academic_year)

    db.session.commit()
    invalidate_report_cache_for_class(class_id)
    flash(f'{saved} mark{"" if saved == 1 else "s"} saved for {subject.name}.', 'success')
    return redirect(url_for('teacher.subject_marks', class_id=class_id,
                            term=academic_term, year=academic_year, subject_id=subject.id))


def invalidate_report_cache_for_class(class_id):
    ids = [r[0] for r in Report.query.with_entities(Report.id).filter_by(class_id=class_id).all()]
    for rid in ids:
        invalidate_report_cache(rid)


@teacher_bp.route('/report/update/<int:report_id>', methods=['POST'])
@teacher_required
def update_report(report_id):
    report = Report.query.get_or_404(report_id)
    if report.status in ['approved', 'published']:
        flash('Cannot edit a report that has been approved or published.', 'danger')
        return redirect(url_for('teacher.view_report',
                                student_id=report.student_id,
                                class_id=report.class_id,
                                term=report.academic_term,
                                year=report.academic_year))

    for mark in report.marks:
        score_key = f'score_{mark.subject_id}'
        score = request.form.get(score_key, 0, type=float)
        max_score = mark.max_score or 100
        score = max(0, min(score, max_score))
        mark.score = score
        mark.grade = calculate_grade((score / max_score) * 100 if max_score else 0)

    scores = [m.score for m in report.marks]
    total = sum(scores)
    report.total_marks = total
    report.average = total / len(scores) if scores else 0
    report.overall_grade = calculate_grade(report.average)
    report.teacher_comment = request.form.get('teacher_comment', '')

    db.session.commit()
    invalidate_report_cache(report.id)
    flash('Marks saved successfully!', 'success')
    return redirect(url_for('teacher.view_report',
                            student_id=report.student_id,
                            class_id=report.class_id,
                            term=report.academic_term,
                            year=report.academic_year))


@teacher_bp.route('/report/submit/<int:report_id>', methods=['POST'])
@teacher_required
def submit_report(report_id):
    report = Report.query.get_or_404(report_id)
    if report.status in ['approved', 'published']:
        flash('Report is already approved or published.', 'danger')
        return redirect(url_for('teacher.view_report',
                                student_id=report.student_id,
                                class_id=report.class_id,
                                term=report.academic_term,
                                year=report.academic_year))

    report.teacher_comment = request.form.get('teacher_comment', '') or report.teacher_comment

    total = sum(m.score for m in report.marks)
    report.total_marks = total
    report.average = total / len(report.marks) if report.marks else 0
    report.overall_grade = calculate_grade(report.average)

    report.status = 'submitted'
    report.submitted_at = datetime.utcnow()

    calculate_positions(report.class_id, report.academic_term, report.academic_year)

    if report.class_obj and report.class_obj.grade:
        calculate_grade_positions(report.class_obj.grade.id, report.academic_term, report.academic_year)

    db.session.commit()
    invalidate_report_cache(report.id)
    flash('Report submitted for approval!', 'success')
    return redirect(url_for('teacher.view_class', class_id=report.class_id))


@teacher_bp.route('/upload-marks/<int:class_id>', methods=['POST'])
@teacher_required
def upload_marks(class_id):
    class_obj = Class.query.get_or_404(class_id)
    academic_term = request.form.get('term', 'Term 1')
    academic_year = request.form.get('year', '2026')

    grade = class_obj.grade

    if 'file' not in request.files or request.files['file'].filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('teacher.view_class', class_id=class_id, term=academic_term, year=academic_year))

    file = request.files['file']

    try:
        if file.filename.endswith('.csv'):
            content = file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
        elif file.filename.endswith(('.xlsx', '.xls')):
            import openpyxl
            wb = openpyxl.load_workbook(file)
            ws = wb.active
            headers = [cell.value for cell in ws[1]]
            reader = []
            for row in ws.iter_rows(min_row=2, values_only=True):
                reader.append(dict(zip(headers, row)))
        else:
            flash('Unsupported file format. Please use CSV or Excel.', 'danger')
            return redirect(url_for('teacher.view_class', class_id=class_id, term=academic_term, year=academic_year))

        subjects = get_subjects_for_grade(grade.id) if grade else Subject.query.all()
        subject_map = {s.code.upper(): s.id for s in subjects}
        subject_map.update({s.name.upper(): s.id for s in subjects})

        count = 0
        for row in reader:
            admission_number = str(row.get('admission_number', '')).strip()
            student = Student.query.filter_by(admission_number=admission_number, class_id=class_id).first()
            if not student:
                continue

            report = Report.query.filter_by(
                student_id=student.id,
                class_id=class_id,
                academic_term=academic_term,
                academic_year=academic_year
            ).first()

            if not report:
                report = Report(
                    student_id=student.id,
                    class_id=class_id,
                    academic_term=academic_term,
                    academic_year=academic_year,
                    status='draft'
                )
                db.session.add(report)
                db.session.flush()

                for subject in subjects:
                    mark = Mark(report_id=report.id, subject_id=subject.id, score=0, max_score=subject.max_score)
                    db.session.add(mark)
                db.session.flush()

            if report.status in ['approved', 'published']:
                continue

            for key, value in row.items():
                if key and key.strip().upper() in ['ADMISSION_NUMBER', 'STUDENT']:
                    continue
                if key and value is not None:
                    subject_id = subject_map.get(key.strip().upper())
                    if subject_id:
                        try:
                            score = float(value)
                            score = max(0, min(100, score))
                            mark = Mark.query.filter_by(report_id=report.id, subject_id=subject_id).first()
                            if mark:
                                mark.score = score
                                mark.grade = calculate_grade(score)
                                count += 1
                        except (ValueError, TypeError):
                            continue

            total = sum(m.score for m in report.marks)
            report.total_marks = total
            report.average = total / len(report.marks) if report.marks else 0
            report.overall_grade = calculate_grade(report.average)

        calculate_positions(class_id, academic_term, academic_year)
        if grade:
            calculate_grade_positions(grade.id, academic_term, academic_year)
        db.session.commit()
        flash(f'Marks uploaded successfully! {count} marks updated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error uploading marks: {str(e)}', 'danger')

    return redirect(url_for('teacher.view_class', class_id=class_id, term=academic_term, year=academic_year))


@teacher_bp.route('/export-marks/<int:class_id>')
@teacher_required
def export_marks(class_id):
    class_obj = Class.query.get_or_404(class_id)
    academic_term = request.args.get('term', 'Term 1')
    academic_year = request.args.get('year', '2026')

    grade = class_obj.grade
    subjects = get_subjects_for_grade(grade.id) if grade else Subject.query.all()
    students = Student.query.filter_by(class_id=class_id, is_active=True).order_by(Student.admission_number).all()

    output = io.StringIO()
    writer = csv.writer(output)
    headers = ['admission_number', 'first_name', 'last_name']
    for subject in subjects:
        headers.append(subject.code)
    writer.writerow(headers)

    for student in students:
        report = Report.query.filter_by(
            student_id=student.id,
            class_id=class_id,
            academic_term=academic_term,
            academic_year=academic_year
        ).first()

        row = [student.admission_number, student.first_name, student.last_name]
        for subject in subjects:
            score = ''
            if report:
                mark = Mark.query.filter_by(report_id=report.id, subject_id=subject.id).first()
                if mark:
                    score = mark.score
            row.append(score)
        writer.writerow(row)

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=marks_{class_obj.name}_{academic_term}_{academic_year}.csv'}
    )
