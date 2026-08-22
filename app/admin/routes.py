import csv
import io
import json
from flask import render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from datetime import datetime
from app.admin import admin_bp
from app.models import (
    db, User, Admin, Teacher, Parent, Student, Class, Subject, Report, Mark,
    ClassTeacher, EducationLevel, Grade, GradeSubject, AcademicYear,
    AcademicTerm, GradingScale, ReportTemplate, ECDAssessmentField
)
from functools import wraps
from app.services.pdf_service import invalidate_report_cache


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== DASHBOARD ====================

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_students = Student.query.filter_by(is_active=True).count()
    total_teachers = Teacher.query.count()
    total_parents = Parent.query.count()
    total_reports = Report.query.count()
    pending_reports = Report.query.filter_by(status='submitted').count()
    published_reports = Report.query.filter_by(status='published').count()

    ecd_count = Student.query.filter_by(is_active=True).join(Class, Student.class_id == Class.id).join(Grade, Class.grade_id == Grade.id).join(EducationLevel, Grade.education_level_id == EducationLevel.id).filter(EducationLevel.name == 'ECD').count()
    primary_count = Student.query.filter_by(is_active=True).join(Class, Student.class_id == Class.id).join(Grade, Class.grade_id == Grade.id).join(EducationLevel, Grade.education_level_id == EducationLevel.id).filter(EducationLevel.name == 'Primary').count()
    secondary_count = Student.query.filter_by(is_active=True).join(Class, Student.class_id == Class.id).join(Grade, Class.grade_id == Grade.id).join(EducationLevel, Grade.education_level_id == EducationLevel.id).filter(EducationLevel.name == 'Secondary').count()

    recent_reports = Report.query.order_by(Report.created_at.desc()).limit(5).all()
    education_levels = EducationLevel.query.filter_by(is_active=True).order_by(EducationLevel.display_order).all()

    return render_template('dashboard.html',
                         total_students=total_students,
                         total_teachers=total_teachers,
                         total_parents=total_parents,
                         total_reports=total_reports,
                         pending_reports=pending_reports,
                         published_reports=published_reports,
                         ecd_count=ecd_count,
                         primary_count=primary_count,
                         secondary_count=secondary_count,
                         recent_reports=recent_reports,
                         education_levels=education_levels)


# ==================== API ENDPOINTS ====================

@admin_bp.route('/api/grades-by-level/<int:level_id>')
@admin_required
def api_grades_by_level(level_id):
    grades = Grade.query.filter_by(education_level_id=level_id, is_active=True).order_by(Grade.display_order).all()
    return jsonify([{'id': g.id, 'name': g.name} for g in grades])


@admin_bp.route('/api/classes-by-grade/<int:grade_id>')
@admin_required
def api_classes_by_grade(grade_id):
    classes = Class.query.filter_by(grade_id=grade_id).all()
    return jsonify([{'id': c.id, 'name': c.name} for c in classes])


@admin_bp.route('/api/subjects-by-grade/<int:grade_id>')
@admin_required
def api_subjects_by_grade(grade_id):
    grade = Grade.query.get_or_404(grade_id)
    subjects = grade.subjects
    return jsonify([{'id': s.id, 'name': s.name, 'code': s.code, 'max_score': s.max_score} for s in subjects])


@admin_bp.route('/api/grading-scale/<int:level_id>')
@admin_required
def api_grading_scale(level_id):
    scales = GradingScale.query.filter_by(education_level_id=level_id, is_active=True).order_by(GradingScale.display_order).all()
    return jsonify([{
        'grade_letter': s.grade_letter,
        'min_score': s.min_score,
        'max_score': s.max_score,
        'description': s.description
    } for s in scales])


from flask import jsonify


# ==================== EDUCATION LEVELS ====================

@admin_bp.route('/education-levels')
@admin_required
def education_levels():
    levels = EducationLevel.query.order_by(EducationLevel.display_order).all()
    return render_template('education_levels.html', education_levels=levels)


@admin_bp.route('/education-levels/add', methods=['POST'])
@admin_required
def add_education_level():
    name = request.form.get('name')
    description = request.form.get('description')
    display_order = request.form.get('display_order', 0, type=int)

    level = EducationLevel(name=name, description=description, display_order=display_order)
    db.session.add(level)
    db.session.commit()
    flash('Education level added successfully!', 'success')
    return redirect(url_for('admin.education_levels'))


@admin_bp.route('/education-levels/edit/<int:id>', methods=['POST'])
@admin_required
def edit_education_level(id):
    level = EducationLevel.query.get_or_404(id)
    level.name = request.form.get('name')
    level.description = request.form.get('description')
    level.display_order = request.form.get('display_order', 0, type=int)
    db.session.commit()
    flash('Education level updated successfully!', 'success')
    return redirect(url_for('admin.education_levels'))


@admin_bp.route('/education-levels/delete/<int:id>', methods=['POST'])
@admin_required
def delete_education_level(id):
    level = EducationLevel.query.get_or_404(id)
    level.is_active = False
    db.session.commit()
    flash('Education level deleted successfully!', 'success')
    return redirect(url_for('admin.education_levels'))


# ==================== GRADES ====================

@admin_bp.route('/grades')
@admin_required
def grades():
    level_id = request.args.get('level_id', type=int)
    levels = EducationLevel.query.filter_by(is_active=True).order_by(EducationLevel.display_order).all()
    query = Grade.query
    if level_id:
        query = query.filter_by(education_level_id=level_id)
    grades_list = query.order_by(Grade.display_order).all()
    return render_template('grades.html', grades=grades_list, education_levels=levels, selected_level=level_id)


@admin_bp.route('/grades/add', methods=['POST'])
@admin_required
def add_grade():
    education_level_id = request.form.get('education_level_id', type=int)
    name = request.form.get('name')
    display_order = request.form.get('display_order', 0, type=int)

    grade = Grade(education_level_id=education_level_id, name=name, display_order=display_order)
    db.session.add(grade)
    db.session.commit()
    flash('Grade added successfully!', 'success')
    return redirect(url_for('admin.grades'))


@admin_bp.route('/grades/edit/<int:id>', methods=['POST'])
@admin_required
def edit_grade(id):
    grade = Grade.query.get_or_404(id)
    grade.education_level_id = request.form.get('education_level_id', type=int)
    grade.name = request.form.get('name')
    grade.display_order = request.form.get('display_order', 0, type=int)
    db.session.commit()
    flash('Grade updated successfully!', 'success')
    return redirect(url_for('admin.grades'))


@admin_bp.route('/grades/delete/<int:id>', methods=['POST'])
@admin_required
def delete_grade(id):
    grade = Grade.query.get_or_404(id)
    grade.is_active = False
    db.session.commit()
    flash('Grade deleted successfully!', 'success')
    return redirect(url_for('admin.grades'))


# ==================== GRADE SUBJECTS ====================

@admin_bp.route('/grade-subjects')
@admin_required
def grade_subjects():
    level_id = request.args.get('level_id', type=int)
    grade_id = request.args.get('grade_id', type=int)
    levels = EducationLevel.query.filter_by(is_active=True).order_by(EducationLevel.display_order).all()
    grades_list = Grade.query.filter_by(is_active=True).order_by(Grade.display_order).all()
    all_subjects = Subject.query.order_by(Subject.name).all()

    selected_grade = None
    assigned_subject_ids = []
    if grade_id:
        selected_grade = Grade.query.get_or_404(grade_id)
        assigned_subject_ids = [s.id for s in selected_grade.subjects]

    return render_template('grade_subjects.html',
                         education_levels=levels,
                         grades=grades_list,
                         all_subjects=all_subjects,
                         selected_grade=selected_grade,
                         assigned_subject_ids=assigned_subject_ids,
                         selected_level=level_id)


@admin_bp.route('/grade-subjects/update/<int:grade_id>', methods=['POST'])
@admin_required
def update_grade_subjects(grade_id):
    grade = Grade.query.get_or_404(grade_id)
    subject_ids = request.form.getlist('subject_ids')

    grade.grade_subjects.clear()
    for sid in subject_ids:
        gs = GradeSubject(grade_id=grade.id, subject_id=int(sid))
        db.session.add(gs)

    db.session.commit()
    flash('Grade subjects updated successfully!', 'success')
    return redirect(url_for('admin.grade_subjects', grade_id=grade_id))


# ==================== ACADEMIC YEARS ====================

@admin_bp.route('/academic-years')
@admin_required
def academic_years():
    years = AcademicYear.query.order_by(AcademicYear.name.desc()).all()
    return render_template('academic_years.html', academic_years=years)


@admin_bp.route('/academic-years/add', methods=['POST'])
@admin_required
def add_academic_year():
    name = request.form.get('name')
    year = AcademicYear(name=name)
    db.session.add(year)
    db.session.commit()
    flash('Academic year added successfully!', 'success')
    return redirect(url_for('admin.academic_years'))


@admin_bp.route('/academic-years/edit/<int:id>', methods=['POST'])
@admin_required
def edit_academic_year(id):
    year = AcademicYear.query.get_or_404(id)
    year.name = request.form.get('name')
    db.session.commit()
    flash('Academic year updated successfully!', 'success')
    return redirect(url_for('admin.academic_years'))


@admin_bp.route('/academic-years/delete/<int:id>', methods=['POST'])
@admin_required
def delete_academic_year(id):
    year = AcademicYear.query.get_or_404(id)
    year.is_active = False
    db.session.commit()
    flash('Academic year deleted successfully!', 'success')
    return redirect(url_for('admin.academic_years'))


@admin_bp.route('/academic-years/set-current/<int:id>', methods=['POST'])
@admin_required
def set_current_year(id):
    AcademicYear.query.update({AcademicYear.is_current: False})
    year = AcademicYear.query.get_or_404(id)
    year.is_current = True
    db.session.commit()
    flash(f'{year.name} set as current academic year!', 'success')
    return redirect(url_for('admin.academic_years'))


@admin_bp.route('/academic-terms/add/<int:year_id>', methods=['POST'])
@admin_required
def add_academic_term(year_id):
    name = request.form.get('name')
    display_order = request.form.get('display_order', 0, type=int)
    term = AcademicTerm(academic_year_id=year_id, name=name, display_order=display_order)
    db.session.add(term)
    db.session.commit()
    flash('Term added successfully!', 'success')
    return redirect(url_for('admin.academic_years'))


@admin_bp.route('/academic-terms/delete/<int:id>', methods=['POST'])
@admin_required
def delete_academic_term(id):
    term = AcademicTerm.query.get_or_404(id)
    db.session.delete(term)
    db.session.commit()
    flash('Term deleted successfully!', 'success')
    return redirect(url_for('admin.academic_years'))


# ==================== GRADING SCALES ====================

@admin_bp.route('/grading-scales')
@admin_required
def grading_scales():
    level_id = request.args.get('level_id', type=int)
    levels = EducationLevel.query.filter_by(is_active=True).order_by(EducationLevel.display_order).all()
    query = GradingScale.query
    if level_id:
        query = query.filter_by(education_level_id=level_id)
    scales = query.order_by(GradingScale.education_level_id, GradingScale.display_order).all()
    return render_template('grading_scales.html', grading_scales=scales, education_levels=levels, selected_level=level_id)


@admin_bp.route('/grading-scales/add', methods=['POST'])
@admin_required
def add_grading_scale():
    education_level_id = request.form.get('education_level_id', type=int)
    name = request.form.get('name')
    min_score = request.form.get('min_score', type=float)
    max_score = request.form.get('max_score', type=float)
    grade_letter = request.form.get('grade_letter')
    description = request.form.get('description')
    display_order = request.form.get('display_order', 0, type=int)

    scale = GradingScale(
        education_level_id=education_level_id, name=name,
        min_score=min_score, max_score=max_score,
        grade_letter=grade_letter, description=description,
        display_order=display_order
    )
    db.session.add(scale)
    db.session.commit()
    flash('Grading scale entry added successfully!', 'success')
    return redirect(url_for('admin.grading_scales'))


@admin_bp.route('/grading-scales/edit/<int:id>', methods=['POST'])
@admin_required
def edit_grading_scale(id):
    scale = GradingScale.query.get_or_404(id)
    scale.education_level_id = request.form.get('education_level_id', type=int)
    scale.name = request.form.get('name')
    scale.min_score = request.form.get('min_score', type=float)
    scale.max_score = request.form.get('max_score', type=float)
    scale.grade_letter = request.form.get('grade_letter')
    scale.description = request.form.get('description')
    scale.display_order = request.form.get('display_order', 0, type=int)
    db.session.commit()
    flash('Grading scale updated successfully!', 'success')
    return redirect(url_for('admin.grading_scales'))


@admin_bp.route('/grading-scales/delete/<int:id>', methods=['POST'])
@admin_required
def delete_grading_scale(id):
    scale = GradingScale.query.get_or_404(id)
    db.session.delete(scale)
    db.session.commit()
    flash('Grading scale entry deleted successfully!', 'success')
    return redirect(url_for('admin.grading_scales'))


# ==================== REPORT TEMPLATES ====================

@admin_bp.route('/report-templates')
@admin_required
def report_templates():
    templates = ReportTemplate.query.all()
    levels = EducationLevel.query.filter_by(is_active=True).all()
    return render_template('report_templates.html', report_templates=templates, education_levels=levels)


@admin_bp.route('/report-templates/add', methods=['POST'])
@admin_required
def add_report_template():
    education_level_id = request.form.get('education_level_id', type=int)
    name = request.form.get('name')
    template_type = request.form.get('template_type')
    description = request.form.get('description')

    template = ReportTemplate(
        education_level_id=education_level_id, name=name,
        template_type=template_type, description=description
    )
    db.session.add(template)
    db.session.commit()
    flash('Report template added successfully!', 'success')
    return redirect(url_for('admin.report_templates'))


@admin_bp.route('/report-templates/edit/<int:id>', methods=['POST'])
@admin_required
def edit_report_template(id):
    template = ReportTemplate.query.get_or_404(id)
    template.education_level_id = request.form.get('education_level_id', type=int)
    template.name = request.form.get('name')
    template.template_type = request.form.get('template_type')
    template.description = request.form.get('description')
    db.session.commit()
    flash('Report template updated successfully!', 'success')
    return redirect(url_for('admin.report_templates'))


@admin_bp.route('/report-templates/delete/<int:id>', methods=['POST'])
@admin_required
def delete_report_template(id):
    template = ReportTemplate.query.get_or_404(id)
    db.session.delete(template)
    db.session.commit()
    flash('Report template deleted successfully!', 'success')
    return redirect(url_for('admin.report_templates'))


# ==================== ECD ASSESSMENT FIELDS ====================

@admin_bp.route('/ecd-fields')
@admin_required
def ecd_fields():
    fields = ECDAssessmentField.query.order_by(ECDAssessmentField.display_order).all()
    return render_template('ecd_fields.html', ecd_fields=fields)


@admin_bp.route('/ecd-fields/add', methods=['POST'])
@admin_required
def add_ecd_field():
    name = request.form.get('name')
    description = request.form.get('description')
    display_order = request.form.get('display_order', 0, type=int)

    field = ECDAssessmentField(name=name, description=description, display_order=display_order)
    db.session.add(field)
    db.session.commit()
    flash('ECD assessment field added successfully!', 'success')
    return redirect(url_for('admin.ecd_fields'))


@admin_bp.route('/ecd-fields/edit/<int:id>', methods=['POST'])
@admin_required
def edit_ecd_field(id):
    field = ECDAssessmentField.query.get_or_404(id)
    field.name = request.form.get('name')
    field.description = request.form.get('description')
    field.display_order = request.form.get('display_order', 0, type=int)
    db.session.commit()
    flash('ECD assessment field updated successfully!', 'success')
    return redirect(url_for('admin.ecd_fields'))


@admin_bp.route('/ecd-fields/delete/<int:id>', methods=['POST'])
@admin_required
def delete_ecd_field(id):
    field = ECDAssessmentField.query.get_or_404(id)
    field.is_active = False
    db.session.commit()
    flash('ECD assessment field deleted successfully!', 'success')
    return redirect(url_for('admin.ecd_fields'))


# ==================== STUDENT MANAGEMENT ====================

@admin_bp.route('/students')
@admin_required
def students():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    level_id = request.args.get('level_id', type=int)
    grade_id = request.args.get('grade_id', type=int)

    query = Student.query.filter_by(is_active=True)
    if search:
        query = query.filter(
            db.or_(
                Student.first_name.ilike(f'%{search}%'),
                Student.last_name.ilike(f'%{search}%'),
                Student.admission_number.ilike(f'%{search}%')
            )
        )
    if level_id and grade_id:
        query = query.join(Class, Student.class_id == Class.id).join(Grade, Class.grade_id == Grade.id).filter(Grade.education_level_id == level_id, Class.grade_id == grade_id)
    elif level_id:
        query = query.join(Class, Student.class_id == Class.id).join(Grade, Class.grade_id == Grade.id).filter(Grade.education_level_id == level_id)
    elif grade_id:
        query = query.join(Class, Student.class_id == Class.id).filter(Class.grade_id == grade_id)

    students_list = query.paginate(page=page, per_page=10)
    levels = EducationLevel.query.filter_by(is_active=True).order_by(EducationLevel.display_order).all()
    grades_list = Grade.query.filter_by(is_active=True).order_by(Grade.display_order).all()
    classes = Class.query.all()
    parents = Parent.query.all()
    return render_template('students.html', students=students_list, classes=classes,
                         parents=parents, search=search, education_levels=levels,
                         grades=grades_list, selected_level=level_id, selected_grade=grade_id)


@admin_bp.route('/students/add', methods=['POST'])
@admin_required
def add_student():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    admission_number = request.form.get('admission_number')
    date_of_birth = request.form.get('date_of_birth')
    gender = request.form.get('gender')
    class_id = request.form.get('class_id')
    parent_id = request.form.get('parent_id')

    education_level_id = None
    if class_id:
        class_obj = Class.query.get(int(class_id))
        if class_obj and class_obj.grade:
            education_level_id = class_obj.grade.education_level_id

    student = Student(
        first_name=first_name,
        last_name=last_name,
        admission_number=admission_number,
        date_of_birth=datetime.strptime(date_of_birth, '%Y-%m-%d').date() if date_of_birth else None,
        gender=gender,
        class_id=int(class_id) if class_id else None,
        parent_id=int(parent_id) if parent_id else None,
        education_level_id=education_level_id
    )
    db.session.add(student)
    db.session.commit()
    flash('Student added successfully!', 'success')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/edit/<int:id>', methods=['POST'])
@admin_required
def edit_student(id):
    student = Student.query.get_or_404(id)
    student.first_name = request.form.get('first_name')
    student.last_name = request.form.get('last_name')
    student.admission_number = request.form.get('admission_number')
    student.gender = request.form.get('gender')
    student.class_id = int(request.form.get('class_id')) if request.form.get('class_id') else None
    student.parent_id = int(request.form.get('parent_id')) if request.form.get('parent_id') else None

    if student.class_id:
        class_obj = Class.query.get(student.class_id)
        if class_obj and class_obj.grade:
            student.education_level_id = class_obj.grade.education_level_id

    db.session.commit()
    flash('Student updated successfully!', 'success')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/delete/<int:id>', methods=['POST'])
@admin_required
def delete_student(id):
    student = Student.query.get_or_404(id)
    student.is_active = False
    db.session.commit()
    flash('Student deleted successfully!', 'success')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/upload', methods=['POST'])
@admin_required
def upload_students():
    if 'file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('admin.students'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('admin.students'))

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
                row_dict = dict(zip(headers, row))
                reader.append(row_dict)
        else:
            flash('Unsupported file format. Please use CSV or Excel.', 'danger')
            return redirect(url_for('admin.students'))

        count = 0
        for row in reader:
            first_name = row.get('first_name', '').strip()
            last_name = row.get('last_name', '').strip()
            admission_number = row.get('admission_number', '').strip()
            gender = row.get('gender', '').strip()
            class_name = row.get('class', '').strip()
            dob = row.get('date_of_birth', '').strip()

            if not first_name or not last_name or not admission_number:
                continue

            existing = Student.query.filter_by(admission_number=admission_number).first()
            if existing:
                continue

            class_obj = Class.query.filter_by(name=class_name).first() if class_name else None

            education_level_id = None
            if class_obj and class_obj.grade:
                education_level_id = class_obj.grade.education_level_id

            student = Student(
                first_name=first_name,
                last_name=last_name,
                admission_number=admission_number,
                gender=gender if gender in ['Male', 'Female'] else None,
                class_id=class_obj.id if class_obj else None,
                date_of_birth=datetime.strptime(dob, '%Y-%m-%d').date() if dob else None,
                education_level_id=education_level_id
            )
            db.session.add(student)
            count += 1

        db.session.commit()
        flash(f'{count} students imported successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error importing students: {str(e)}', 'danger')

    return redirect(url_for('admin.students'))


@admin_bp.route('/students/export')
@admin_required
def export_students():
    students = Student.query.filter_by(is_active=True).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['first_name', 'last_name', 'admission_number', 'gender', 'class', 'date_of_birth'])

    for student in students:
        writer.writerow([
            student.first_name,
            student.last_name,
            student.admission_number,
            student.gender or '',
            student.class_obj.name if student.class_obj else '',
            student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else ''
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=students_export.csv'}
    )


@admin_bp.route('/reports/export')
@admin_required
def export_reports():
    class_id = request.args.get('class_id', type=int)
    term = request.args.get('term', 'Term 1')
    year = request.args.get('year', '2024/2025')

    query = Report.query.filter_by(academic_term=term, academic_year=year)
    if class_id:
        query = query.filter_by(class_id=class_id)
    reports = query.all()

    subjects = Subject.query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    headers = ['admission_number', 'student_name', 'class', 'term', 'year', 'total', 'average', 'grade', 'position', 'status']
    for subject in subjects:
        headers.append(subject.code)
    writer.writerow(headers)

    for report in reports:
        student = report.student
        row = [
            student.admission_number,
            f'{student.first_name} {student.last_name}',
            report.class_obj.name if report.class_obj else '',
            report.academic_term,
            report.academic_year,
            report.total_marks,
            round(report.average, 1),
            report.overall_grade,
            report.position or '',
            report.status
        ]
        for subject in subjects:
            mark = Mark.query.filter_by(report_id=report.id, subject_id=subject.id).first()
            row.append(mark.score if mark else '')
        writer.writerow(row)

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=reports_export_{term}_{year}.csv'}
    )


# ==================== TEACHER MANAGEMENT ====================

@admin_bp.route('/teachers')
@admin_required
def teachers():
    page = request.args.get('page', 1, type=int)
    teachers = Teacher.query.paginate(page=page, per_page=10)
    return render_template('teachers.html', teachers=teachers)


@admin_bp.route('/teachers/add', methods=['POST'])
@admin_required
def add_teacher():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    employee_id = request.form.get('employee_id')
    username = request.form.get('username')
    password = request.form.get('password')

    user = User(username=username, email=email, role='teacher')
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    teacher = Teacher(
        user_id=user.id,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        employee_id=employee_id
    )
    db.session.add(teacher)
    db.session.commit()
    flash('Teacher added successfully!', 'success')
    return redirect(url_for('admin.teachers'))


@admin_bp.route('/teachers/edit/<int:id>', methods=['POST'])
@admin_required
def edit_teacher(id):
    teacher = Teacher.query.get_or_404(id)
    new_username = request.form.get('username')
    if new_username != teacher.user.username:
        existing = User.query.filter_by(username=new_username).first()
        if existing:
            flash('Username already taken.', 'danger')
            return redirect(url_for('admin.teachers'))
        teacher.user.username = new_username
    teacher.first_name = request.form.get('first_name')
    teacher.last_name = request.form.get('last_name')
    teacher.phone = request.form.get('phone')
    teacher.employee_id = request.form.get('employee_id')
    password = request.form.get('password')
    if password:
        teacher.user.set_password(password)
    db.session.commit()
    flash('Teacher updated successfully!', 'success')
    return redirect(url_for('admin.teachers'))


@admin_bp.route('/teachers/delete/<int:id>', methods=['POST'])
@admin_required
def delete_teacher(id):
    teacher = Teacher.query.get_or_404(id)
    user = teacher.user
    db.session.delete(teacher)
    db.session.delete(user)
    db.session.commit()
    flash('Teacher deleted successfully!', 'success')
    return redirect(url_for('admin.teachers'))


# ==================== PARENT MANAGEMENT ====================

@admin_bp.route('/parents')
@admin_required
def parents():
    page = request.args.get('page', 1, type=int)
    parents = Parent.query.paginate(page=page, per_page=10)
    students = Student.query.filter_by(is_active=True).all()
    return render_template('parents.html', parents=parents, students=students)


@admin_bp.route('/parents/add', methods=['POST'])
@admin_required
def add_parent():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    address = request.form.get('address')
    username = request.form.get('username')
    password = request.form.get('password')
    child_ids = request.form.getlist('child_ids')

    user = User(username=username, email=email, role='parent')
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    parent = Parent(
        user_id=user.id,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        address=address
    )
    db.session.add(parent)
    db.session.flush()

    for child_id in child_ids:
        student = Student.query.get(int(child_id))
        if student:
            student.parent_id = parent.id

    db.session.commit()
    flash('Parent added successfully!', 'success')
    return redirect(url_for('admin.parents'))


@admin_bp.route('/parents/edit/<int:id>', methods=['POST'])
@admin_required
def edit_parent(id):
    parent = Parent.query.get_or_404(id)
    new_username = request.form.get('username')
    if new_username != parent.user.username:
        existing = User.query.filter_by(username=new_username).first()
        if existing:
            flash('Username already taken.', 'danger')
            return redirect(url_for('admin.parents'))
        parent.user.username = new_username
    parent.first_name = request.form.get('first_name')
    parent.last_name = request.form.get('last_name')
    parent.phone = request.form.get('phone')
    parent.address = request.form.get('address')
    child_ids = request.form.getlist('child_ids')
    password = request.form.get('password')
    if password:
        parent.user.set_password(password)

    for child in parent.children:
        child.parent_id = None

    for child_id in child_ids:
        student = Student.query.get(int(child_id))
        if student:
            student.parent_id = parent.id

    db.session.commit()
    flash('Parent updated successfully!', 'success')
    return redirect(url_for('admin.parents'))


@admin_bp.route('/parents/delete/<int:id>', methods=['POST'])
@admin_required
def delete_parent(id):
    parent = Parent.query.get_or_404(id)
    user = parent.user
    db.session.delete(parent)
    db.session.delete(user)
    db.session.commit()
    flash('Parent deleted successfully!', 'success')
    return redirect(url_for('admin.parents'))


# ==================== CLASS MANAGEMENT ====================

@admin_bp.route('/classes')
@admin_required
def classes():
    level_id = request.args.get('level_id', type=int)
    grade_id = request.args.get('grade_id', type=int)
    levels = EducationLevel.query.filter_by(is_active=True).order_by(EducationLevel.display_order).all()
    grades_list = Grade.query.filter_by(is_active=True).order_by(Grade.display_order).all()

    query = Class.query
    if grade_id:
        query = query.filter_by(grade_id=grade_id)
    elif level_id:
        query = query.join(Grade, Class.grade_id == Grade.id).filter(Grade.education_level_id == level_id)
    classes_list = query.all()

    teachers = Teacher.query.all()
    return render_template('classes.html', classes=classes_list, teachers=teachers,
                         education_levels=levels, grades=grades_list,
                         selected_level=level_id, selected_grade=grade_id)


@admin_bp.route('/classes/add', methods=['POST'])
@admin_required
def add_class():
    name = request.form.get('name')
    section = request.form.get('section')
    grade_id = request.form.get('grade_id', type=int)
    teacher_ids = request.form.getlist('teacher_ids')
    class_teacher_id = request.form.get('class_teacher_id', type=int)

    class_obj = Class(name=name, section=section, grade_id=grade_id, class_teacher_id=class_teacher_id)
    db.session.add(class_obj)
    db.session.flush()

    for teacher_id in teacher_ids:
        teacher = Teacher.query.get(int(teacher_id))
        if teacher:
            class_obj.teachers.append(teacher)

    db.session.commit()
    flash('Class added successfully!', 'success')
    return redirect(url_for('admin.classes'))


@admin_bp.route('/classes/edit/<int:id>', methods=['POST'])
@admin_required
def edit_class(id):
    class_obj = Class.query.get_or_404(id)
    class_obj.name = request.form.get('name')
    class_obj.section = request.form.get('section')
    class_obj.grade_id = request.form.get('grade_id', type=int)
    class_obj.class_teacher_id = request.form.get('class_teacher_id', type=int)
    teacher_ids = request.form.getlist('teacher_ids')

    class_obj.teachers.clear()
    for teacher_id in teacher_ids:
        teacher = Teacher.query.get(int(teacher_id))
        if teacher:
            class_obj.teachers.append(teacher)

    db.session.commit()
    flash('Class updated successfully!', 'success')
    return redirect(url_for('admin.classes'))


@admin_bp.route('/classes/delete/<int:id>', methods=['POST'])
@admin_required
def delete_class(id):
    class_obj = Class.query.get_or_404(id)
    db.session.delete(class_obj)
    db.session.commit()
    flash('Class deleted successfully!', 'success')
    return redirect(url_for('admin.classes'))


# ==================== SUBJECT MANAGEMENT ====================

@admin_bp.route('/subjects')
@admin_required
def subjects():
    subjects = Subject.query.all()
    grades_list = Grade.query.filter_by(is_active=True).order_by(Grade.display_order).all()
    return render_template('subjects.html', subjects=subjects, grades=grades_list)


@admin_bp.route('/subjects/add', methods=['POST'])
@admin_required
def add_subject():
    name = request.form.get('name')
    code = request.form.get('code')
    max_score = request.form.get('max_score', 100, type=int)

    subject = Subject(name=name, code=code, max_score=max_score)
    db.session.add(subject)
    db.session.commit()
    flash('Subject added successfully!', 'success')
    return redirect(url_for('admin.subjects'))


@admin_bp.route('/subjects/edit/<int:id>', methods=['POST'])
@admin_required
def edit_subject(id):
    subject = Subject.query.get_or_404(id)
    subject.name = request.form.get('name')
    subject.code = request.form.get('code')
    subject.max_score = request.form.get('max_score', 100, type=int)
    db.session.commit()
    flash('Subject updated successfully!', 'success')
    return redirect(url_for('admin.subjects'))


@admin_bp.route('/subjects/delete/<int:id>', methods=['POST'])
@admin_required
def delete_subject(id):
    subject = Subject.query.get_or_404(id)
    db.session.delete(subject)
    db.session.commit()
    flash('Subject deleted successfully!', 'success')
    return redirect(url_for('admin.subjects'))


# ==================== REPORT MANAGEMENT ====================

@admin_bp.route('/reports')
@admin_required
def reports():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    level_id = request.args.get('level_id', type=int)
    grade_id = request.args.get('grade_id', type=int)

    query = Report.query
    if status:
        query = query.filter_by(status=status)
    if level_id and grade_id:
        query = query.join(Class, Report.class_id == Class.id).join(Grade, Class.grade_id == Grade.id).filter(Grade.education_level_id == level_id, Class.grade_id == grade_id)
    elif level_id:
        query = query.join(Class, Report.class_id == Class.id).join(Grade, Class.grade_id == Grade.id).filter(Grade.education_level_id == level_id)
    elif grade_id:
        query = query.join(Class, Report.class_id == Class.id).filter(Class.grade_id == grade_id)

    reports_list = query.order_by(Report.created_at.desc()).paginate(page=page, per_page=10)
    levels = EducationLevel.query.filter_by(is_active=True).order_by(EducationLevel.display_order).all()
    grades_list = Grade.query.filter_by(is_active=True).order_by(Grade.display_order).all()
    return render_template('reports.html', reports=reports_list, current_status=status,
                         education_levels=levels, grades=grades_list,
                         selected_level=level_id, selected_grade=grade_id)


@admin_bp.route('/reports/approve/<int:id>', methods=['POST'])
@admin_required
def approve_report(id):
    report = Report.query.get_or_404(id)
    report.status = 'approved'
    report.approved_at = datetime.utcnow()
    admin_comment = request.form.get('admin_comment')
    if admin_comment:
        report.admin_comment = admin_comment
    db.session.commit()
    invalidate_report_cache(report.id)
    flash('Report approved successfully!', 'success')
    return redirect(url_for('admin.reports'))


@admin_bp.route('/reports/publish/<int:id>', methods=['POST'])
@admin_required
def publish_report(id):
    report = Report.query.get_or_404(id)
    report.status = 'published'
    report.published_at = datetime.utcnow()
    db.session.commit()
    invalidate_report_cache(report.id)
    flash('Report published successfully!', 'success')
    return redirect(url_for('admin.reports'))
