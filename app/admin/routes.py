import csv
import io
from flask import render_template, redirect, url_for, flash, request, Response, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.admin import admin_bp
from app.models import (
    db, User, Admin, Teacher, Parent, Student, Class, Subject, Report, Mark,
    ClassTeacher, Grade, GradeSubject, AcademicYear,
    AcademicTerm, GradingScale, ReportTemplate, SchoolSetting
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
    total_classes = Class.query.count()
    total_subjects = Subject.query.count()
    pending_reports = Report.query.filter_by(status='submitted').count()
    generated_reports = Report.query.filter(Report.status.in_(['approved', 'published'])).count()

    recent_results = Report.query.filter(
        Report.marks.any(), Report.status != 'draft'
    ).order_by(Report.updated_at.desc()).limit(6).all()

    recent_activity = Report.query.order_by(Report.created_at.desc()).limit(6).all()

    attention_reports = Report.query.filter(
        Report.status.in_(['submitted', 'approved', 'published'])
    ).order_by(Report.average.asc()).limit(40).all()

    attention, seen = [], set()
    for r in attention_reports:
        if r.student_id not in seen:
            seen.add(r.student_id)
            attention.append((r.student, r.average))
        if len(attention) >= 5:
            break

    current_year = AcademicYear.query.filter_by(is_current=True).first()
    current_terms = []
    active_term = None
    if current_year:
        current_terms = AcademicTerm.query.filter_by(
            academic_year_id=current_year.id).order_by(AcademicTerm.display_order).all()
        active_term = next((t for t in current_terms if t.is_active), None)

    quick_stats = {
        'draft': Report.query.filter_by(status='draft').count(),
        'approved': Report.query.filter_by(status='approved').count(),
    }

    return render_template('dashboard.html',
                           total_students=total_students,
                           total_teachers=total_teachers,
                           total_classes=total_classes,
                           total_subjects=total_subjects,
                           pending_reports=pending_reports,
                           generated_reports=generated_reports,
                           recent_results=recent_results,
                           recent_activity=recent_activity,
                           attention=attention,
                           current_year=current_year,
                           current_terms=current_terms,
                           active_term=active_term,
                           quick_stats=quick_stats)


# ==================== API ENDPOINTS ====================

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


@admin_bp.route('/api/grading-scale')
@admin_required
def api_grading_scale():
    scales = GradingScale.query.filter_by(is_active=True).order_by(GradingScale.display_order).all()
    return jsonify([{
        'grade_letter': s.grade_letter,
        'min_score': s.min_score,
        'max_score': s.max_score,
        'description': s.description
    } for s in scales])


# ==================== FORMS / LEVELS ====================

@admin_bp.route('/grades')
@admin_required
def grades():
    grades_list = Grade.query.filter_by(is_active=True).order_by(Grade.display_order).all()
    return render_template('grades.html', grades=grades_list)


@admin_bp.route('/grades/add', methods=['POST'])
@admin_required
def add_grade():
    name = request.form.get('name')
    display_order = request.form.get('display_order', 0, type=int)

    grade = Grade(name=name, display_order=display_order)
    db.session.add(grade)
    db.session.commit()
    flash('Form added successfully!', 'success')
    return redirect(url_for('admin.grades'))


@admin_bp.route('/grades/edit/<int:id>', methods=['POST'])
@admin_required
def edit_grade(id):
    grade = Grade.query.get_or_404(id)
    grade.name = request.form.get('name')
    grade.display_order = request.form.get('display_order', 0, type=int)
    db.session.commit()
    flash('Form updated successfully!', 'success')
    return redirect(url_for('admin.grades'))


@admin_bp.route('/grades/delete/<int:id>', methods=['POST'])
@admin_required
def delete_grade(id):
    grade = Grade.query.get_or_404(id)
    grade.is_active = False
    db.session.commit()
    flash('Form deleted successfully!', 'success')
    return redirect(url_for('admin.grades'))


# ==================== FORM SUBJECTS ====================

@admin_bp.route('/grade-subjects')
@admin_required
def grade_subjects():
    grade_id = request.args.get('grade_id', type=int)
    grades_list = Grade.query.filter_by(is_active=True).order_by(Grade.display_order).all()
    all_subjects = Subject.query.order_by(Subject.name).all()

    selected_grade = None
    assigned_subject_ids = []
    if grade_id:
        selected_grade = Grade.query.get_or_404(grade_id)
        assigned_subject_ids = [s.id for s in selected_grade.subjects]

    return render_template('grade_subjects.html',
                           grades=grades_list,
                           all_subjects=all_subjects,
                           selected_grade=selected_grade,
                           assigned_subject_ids=assigned_subject_ids)


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
    flash('Subjects for this form updated successfully!', 'success')
    return redirect(url_for('admin.grade_subjects', grade_id=grade_id))


# ==================== ACADEMIC YEARS & TERMS ====================

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


@admin_bp.route('/academic-terms/toggle-active/<int:id>', methods=['POST'])
@admin_required
def toggle_academic_term(id):
    term = AcademicTerm.query.get_or_404(id)
    term.is_active = not term.is_active
    if term.is_active:
        AcademicTerm.query.filter(
            AcademicTerm.id != term.id,
            AcademicTerm.academic_year_id == term.academic_year_id
        ).update({AcademicTerm.is_active: False})
    db.session.commit()
    flash(f'{term.name} is now the active term.', 'success')
    return redirect(url_for('admin.academic_years'))


# ==================== GRADING SCALES ====================

@admin_bp.route('/grading-scales')
@admin_required
def grading_scales():
    scales = GradingScale.query.order_by(GradingScale.display_order).all()
    return render_template('grading_scales.html', grading_scales=scales)


@admin_bp.route('/grading-scales/add', methods=['POST'])
@admin_required
def add_grading_scale():
    scale = GradingScale(
        name=request.form.get('name'),
        min_score=request.form.get('min_score', type=float),
        max_score=request.form.get('max_score', type=float),
        grade_letter=request.form.get('grade_letter'),
        description=request.form.get('description'),
        display_order=request.form.get('display_order', 0, type=int)
    )
    db.session.add(scale)
    db.session.commit()
    flash('Grade band added successfully!', 'success')
    return redirect(url_for('admin.grading_scales'))


@admin_bp.route('/grading-scales/edit/<int:id>', methods=['POST'])
@admin_required
def edit_grading_scale(id):
    scale = GradingScale.query.get_or_404(id)
    scale.name = request.form.get('name')
    scale.min_score = request.form.get('min_score', type=float)
    scale.max_score = request.form.get('max_score', type=float)
    scale.grade_letter = request.form.get('grade_letter')
    scale.description = request.form.get('description')
    scale.display_order = request.form.get('display_order', 0, type=int)
    db.session.commit()
    flash('Grade band updated successfully!', 'success')
    return redirect(url_for('admin.grading_scales'))


@admin_bp.route('/grading-scales/delete/<int:id>', methods=['POST'])
@admin_required
def delete_grading_scale(id):
    scale = GradingScale.query.get_or_404(id)
    db.session.delete(scale)
    db.session.commit()
    flash('Grade band deleted successfully!', 'success')
    return redirect(url_for('admin.grading_scales'))


# ==================== REPORT TEMPLATES ====================

@admin_bp.route('/report-templates')
@admin_required
def report_templates():
    templates = ReportTemplate.query.all()
    return render_template('report_templates.html', report_templates=templates)


@admin_bp.route('/report-templates/add', methods=['POST'])
@admin_required
def add_report_template():
    template = ReportTemplate(
        name=request.form.get('name'),
        template_type='secondary',
        description=request.form.get('description')
    )
    db.session.add(template)
    db.session.commit()
    flash('Report template added successfully!', 'success')
    return redirect(url_for('admin.report_templates'))


@admin_bp.route('/report-templates/edit/<int:id>', methods=['POST'])
@admin_required
def edit_report_template(id):
    template = ReportTemplate.query.get_or_404(id)
    template.name = request.form.get('name')
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


# ==================== STUDENT MANAGEMENT ====================

@admin_bp.route('/students')
@admin_required
def students():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    grade_id = request.args.get('grade_id', type=int)
    class_id = request.args.get('class_id', type=int)

    query = Student.query.filter_by(is_active=True)
    if search:
        query = query.filter(
            db.or_(
                Student.first_name.ilike(f'%{search}%'),
                Student.last_name.ilike(f'%{search}%'),
                Student.admission_number.ilike(f'%{search}%')
            )
        )
    if class_id:
        query = query.filter(Student.class_id == class_id)
    elif grade_id:
        query = query.join(Class, Student.class_id == Class.id).filter(Class.grade_id == grade_id)

    students_list = query.order_by(Student.admission_number).paginate(page=page, per_page=10)
    grades_list = Grade.query.filter_by(is_active=True).order_by(Grade.display_order).all()
    classes = Class.query.all()
    parents = Parent.query.all()
    return render_template('students.html', students=students_list, classes=classes,
                           parents=parents, search=search,
                           grades=grades_list, selected_grade=grade_id,
                           selected_class=class_id)


@admin_bp.route('/students/<int:id>')
@admin_required
def student_profile(id):
    student = Student.query.get_or_404(id)
    reports = Report.query.filter_by(student_id=id).order_by(
        Report.academic_year.desc(), Report.academic_term).all()
    parents = Parent.query.order_by(Parent.first_name).all()
    return render_template('student_profile.html', student=student, reports=reports, parents_all=parents)


@admin_bp.route('/students/add', methods=['POST'])
@admin_required
def add_student():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    admission_number = request.form.get('admission_number')

    if Student.query.filter_by(admission_number=admission_number).first():
        flash('A student with that admission number already exists.', 'danger')
        return redirect(url_for('admin.students'))

    date_of_birth = request.form.get('date_of_birth')
    gender = request.form.get('gender')
    class_id = request.form.get('class_id')
    parent_id = request.form.get('parent_id')

    student = Student(
        first_name=first_name,
        last_name=last_name,
        admission_number=admission_number,
        date_of_birth=datetime.strptime(date_of_birth, '%Y-%m-%d').date() if date_of_birth else None,
        gender=gender,
        class_id=int(class_id) if class_id else None,
        parent_id=int(parent_id) if parent_id else None
    )
    db.session.add(student)
    db.session.commit()
    flash('Student enrolled successfully!', 'success')
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
    dob = request.form.get('date_of_birth')
    if dob:
        student.date_of_birth = datetime.strptime(dob, '%Y-%m-%d').date()

    db.session.commit()
    flash('Student updated successfully!', 'success')
    return redirect(request.referrer or url_for('admin.students'))


@admin_bp.route('/students/delete/<int:id>', methods=['POST'])
@admin_required
def delete_student(id):
    student = Student.query.get_or_404(id)
    student.is_active = False
    db.session.commit()
    flash('Student removed from the roll.', 'success')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/upload', methods=['POST'])
@admin_required
def upload_students():
    if 'file' not in request.files or request.files['file'].filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('admin.students'))

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
            return redirect(url_for('admin.students'))

        count = 0
        for row in reader:
            first_name = (row.get('first_name') or '').strip()
            last_name = (row.get('last_name') or '').strip()
            admission_number = (row.get('admission_number') or '').strip()
            gender = (row.get('gender') or '').strip()
            class_name = (row.get('class') or '').strip()
            dob = (row.get('date_of_birth') or '').strip()

            if not first_name or not last_name or not admission_number:
                continue
            if Student.query.filter_by(admission_number=admission_number).first():
                continue

            class_obj = Class.query.filter_by(name=class_name).first() if class_name else None

            student = Student(
                first_name=first_name,
                last_name=last_name,
                admission_number=admission_number,
                gender=gender if gender in ['Male', 'Female'] else None,
                class_id=class_obj.id if class_obj else None,
                date_of_birth=datetime.strptime(dob, '%Y-%m-%d').date() if dob else None
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
    writer.writerow(['first_name', 'last_name', 'admission_number', 'gender', 'form', 'class', 'date_of_birth'])

    for student in students:
        writer.writerow([
            student.first_name,
            student.last_name,
            student.admission_number,
            student.gender or '',
            student.class_obj.grade.name if student.class_obj and student.class_obj.grade else '',
            student.class_obj.name if student.class_obj else '',
            student.date_of_birth.strftime('%Y-%m-%d') if student.date_of_birth else ''
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=nyatsime_students_export.csv'}
    )


@admin_bp.route('/reports/export')
@admin_required
def export_reports():
    class_id = request.args.get('class_id', type=int)
    term = request.args.get('term', 'Term 1')
    year = request.args.get('year', '2026')

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
        headers={'Content-Disposition': f'attachment; filename=nyatsime_reports_{term}_{year}.csv'}
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
    username = request.form.get('username')
    email = request.form.get('email')
    if User.query.filter_by(username=username).first():
        flash('Username already taken.', 'danger')
        return redirect(url_for('admin.teachers'))
    if User.query.filter_by(email=email).first():
        flash('Email already in use.', 'danger')
        return redirect(url_for('admin.teachers'))

    user = User(username=username, email=email, role='teacher')
    user.set_password(request.form.get('password'))
    db.session.add(user)
    db.session.flush()

    teacher = Teacher(
        user_id=user.id,
        first_name=request.form.get('first_name'),
        last_name=request.form.get('last_name'),
        phone=request.form.get('phone'),
        employee_id=request.form.get('employee_id')
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
    flash('Teacher removed successfully!', 'success')
    return redirect(url_for('admin.teachers'))


# ==================== USERS & ROLES ====================

@admin_bp.route('/users')
@admin_required
def users():
    role = request.args.get('role', '')
    query = User.query
    if role:
        query = query.filter_by(role=role)
    users_list = query.order_by(User.role, User.username).all()
    return render_template('users.html', users=users_list, selected_role=role)


@admin_bp.route('/users/toggle/<int:id>', methods=['POST'])
@admin_required
def toggle_user(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'warning')
        return redirect(url_for('admin.users'))
    user.is_active = not user.is_active
    db.session.commit()
    flash(f"Account '{user.username}' {'activated' if user.is_active else 'deactivated'}.", 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/reset-password/<int:id>', methods=['POST'])
@admin_required
def reset_user_password(id):
    user = User.query.get_or_404(id)
    password = request.form.get('password')
    if password and len(password) >= 6:
        user.set_password(password)
        db.session.commit()
        flash(f"Password reset for '{user.username}'.", 'success')
    else:
        flash('Password must be at least 6 characters.', 'danger')
    return redirect(url_for('admin.users'))


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
    username = request.form.get('username')
    email = request.form.get('email')
    if User.query.filter_by(username=username).first():
        flash('Username already taken.', 'danger')
        return redirect(url_for('admin.parents'))
    if User.query.filter_by(email=email).first():
        flash('Email already in use.', 'danger')
        return redirect(url_for('admin.parents'))

    user = User(username=username, email=email, role='parent')
    user.set_password(request.form.get('password'))
    db.session.add(user)
    db.session.flush()

    parent = Parent(
        user_id=user.id,
        first_name=request.form.get('first_name'),
        last_name=request.form.get('last_name'),
        phone=request.form.get('phone'),
        address=request.form.get('address')
    )
    db.session.add(parent)
    db.session.flush()

    for child_id in request.form.getlist('child_ids'):
        student = Student.query.get(int(child_id))
        if student:
            student.parent_id = parent.id

    db.session.commit()
    flash('Parent/guardian added successfully!', 'success')
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
    flash('Parent/guardian updated successfully!', 'success')
    return redirect(url_for('admin.parents'))


@admin_bp.route('/parents/delete/<int:id>', methods=['POST'])
@admin_required
def delete_parent(id):
    parent = Parent.query.get_or_404(id)
    user = parent.user
    db.session.delete(parent)
    db.session.delete(user)
    db.session.commit()
    flash('Parent/guardian removed successfully!', 'success')
    return redirect(url_for('admin.parents'))


# ==================== CLASS MANAGEMENT ====================

@admin_bp.route('/classes')
@admin_required
def classes():
    grade_id = request.args.get('grade_id', type=int)
    grades_list = Grade.query.filter_by(is_active=True).order_by(Grade.display_order).all()

    query = Class.query
    if grade_id:
        query = query.filter_by(grade_id=grade_id)
    classes_list = query.order_by(Class.name).all()

    teachers = Teacher.query.all()
    return render_template('classes.html', classes=classes_list, teachers=teachers,
                           grades=grades_list, selected_grade=grade_id)


@admin_bp.route('/classes/add', methods=['POST'])
@admin_required
def add_class():
    name = request.form.get('name')
    section = request.form.get('section')
    grade_id = request.form.get('grade_id', type=int)
    teacher_ids = request.form.getlist('teacher_ids')
    class_teacher_id = request.form.get('class_teacher_id', type=int)

    class_obj = Class(name=name, section=section, grade_id=grade_id, class_teacher_id=class_teacher_id or None)
    db.session.add(class_obj)
    db.session.flush()

    for teacher_id in teacher_ids:
        teacher = Teacher.query.get(int(teacher_id))
        if teacher:
            class_obj.teachers.append(teacher)

    db.session.commit()
    flash('Class/stream created successfully!', 'success')
    return redirect(url_for('admin.classes'))


@admin_bp.route('/classes/edit/<int:id>', methods=['POST'])
@admin_required
def edit_class(id):
    class_obj = Class.query.get_or_404(id)
    class_obj.name = request.form.get('name')
    class_obj.section = request.form.get('section')
    class_obj.grade_id = request.form.get('grade_id', type=int)
    ctid = request.form.get('class_teacher_id', type=int)
    class_obj.class_teacher_id = ctid or None
    teacher_ids = request.form.getlist('teacher_ids')

    class_obj.teachers.clear()
    for teacher_id in teacher_ids:
        teacher = Teacher.query.get(int(teacher_id))
        if teacher:
            class_obj.teachers.append(teacher)

    db.session.commit()
    flash('Class/stream updated successfully!', 'success')
    return redirect(url_for('admin.classes'))


@admin_bp.route('/classes/delete/<int:id>', methods=['POST'])
@admin_required
def delete_class(id):
    class_obj = Class.query.get_or_404(id)
    if class_obj.students:
        flash('Cannot delete a class that still has students assigned.', 'danger')
        return redirect(url_for('admin.classes'))
    db.session.delete(class_obj)
    db.session.commit()
    flash('Class/stream deleted successfully!', 'success')
    return redirect(url_for('admin.classes'))


# ==================== SUBJECT MANAGEMENT ====================

@admin_bp.route('/subjects')
@admin_required
def subjects():
    subjects = Subject.query.order_by(Subject.name).all()
    grades_list = Grade.query.filter_by(is_active=True).order_by(Grade.display_order).all()
    return render_template('subjects.html', subjects=subjects, grades=grades_list)


@admin_bp.route('/subjects/add', methods=['POST'])
@admin_required
def add_subject():
    subject = Subject(
        name=request.form.get('name'),
        code=request.form.get('code'),
        max_score=request.form.get('max_score', 100, type=int)
    )
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
    grade_id = request.args.get('grade_id', type=int)
    class_id = request.args.get('class_id', type=int)

    query = Report.query
    if status:
        query = query.filter_by(status=status)
    if class_id:
        query = query.filter(Report.class_id == class_id)
    elif grade_id:
        query = query.join(Class, Report.class_id == Class.id).filter(Class.grade_id == grade_id)

    reports_list = query.order_by(Report.updated_at.desc()).paginate(page=page, per_page=12)
    grades_list = Grade.query.filter_by(is_active=True).order_by(Grade.display_order).all()
    classes = Class.query.order_by(Class.name).all()
    return render_template('reports.html', reports=reports_list, current_status=status,
                           grades=grades_list, classes=classes,
                           selected_grade=grade_id, selected_class=class_id)


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
    return redirect(request.referrer or url_for('admin.reports'))


@admin_bp.route('/reports/publish/<int:id>', methods=['POST'])
@admin_required
def publish_report(id):
    report = Report.query.get_or_404(id)
    report.status = 'published'
    report.published_at = datetime.utcnow()
    db.session.commit()
    invalidate_report_cache(report.id)
    flash('Report published - now visible to parents.', 'success')
    return redirect(request.referrer or url_for('admin.reports'))


# ==================== SCHOOL SETTINGS ====================

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    setting_keys = ['school_name', 'school_motto', 'school_address', 'school_phone', 'school_email']
    if request.method == 'POST':
        for key in setting_keys:
            SchoolSetting.set(key, request.form.get(key, '').strip())
        db.session.commit()
        invalidate_all_caches()
        flash('School settings saved.', 'success')
        return redirect(url_for('admin.settings'))

    values = {key: SchoolSetting.get(key) for key in setting_keys}
    return render_template('settings.html', values=values)


def invalidate_all_caches():
    from app.services.pdf_service import invalidate_report_cache
    ids = [r[0] for r in Report.query.with_entities(Report.id).all()]
    for rid in ids:
        invalidate_report_cache(rid)
