from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin | teacher | student
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))

    user = db.relationship('User', backref=db.backref('admin_profile', uselist=False))


class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    employee_id = db.Column(db.String(20), unique=True)

    user = db.relationship('User', backref=db.backref('teacher_profile', uselist=False))
    classes = db.relationship('Class', secondary='class_teachers', back_populates='teachers')


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    admission_number = db.Column(db.String(20), unique=True, nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('student_profile', uselist=False))
    class_obj = db.relationship('Class', back_populates='students')
    reports = db.relationship('Report', back_populates='student')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'


class Grade(db.Model):
    """Fixed secondary school forms (Form 1 ... Upper 6).

    Reference data maintained by the application - there is no CRUD interface.
    """
    __tablename__ = 'grades'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    classes = db.relationship('Class', back_populates='grade')
    grade_subjects = db.relationship('GradeSubject', back_populates='grade', cascade='all, delete-orphan', viewonly=False)

    subjects = db.relationship('Subject', secondary='grade_subjects', back_populates='grades', viewonly=True)

    @property
    def level_group(self):
        from app.academic import level_group
        return level_group(self.name)


class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    section = db.Column(db.String(10))
    grade_id = db.Column(db.Integer, db.ForeignKey('grades.id'))
    class_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'))

    grade = db.relationship('Grade', back_populates='classes')
    class_teacher = db.relationship('Teacher', foreign_keys=[class_teacher_id])
    teachers = db.relationship('Teacher', secondary='class_teachers', back_populates='classes')
    students = db.relationship('Student', back_populates='class_obj')

    @property
    def grade_level(self):
        return self.grade.name if self.grade else None


class ClassTeacher(db.Model):
    __tablename__ = 'class_teachers'
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), primary_key=True)


class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    code = db.Column(db.String(10), unique=True)
    max_score = db.Column(db.Integer, default=100)

    grades = db.relationship('Grade', secondary='grade_subjects', back_populates='subjects', viewonly=True)


class GradeSubject(db.Model):
    __tablename__ = 'grade_subjects'
    grade_id = db.Column(db.Integer, db.ForeignKey('grades.id'), primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), primary_key=True)

    grade = db.relationship('Grade', back_populates='grade_subjects')
    subject = db.relationship('Subject', backref=db.backref('grade_associations', overlaps='grades'))


class AcademicYear(db.Model):
    __tablename__ = 'academic_years'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)  # single year e.g. "2026"
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    terms = db.relationship('AcademicTerm', back_populates='academic_year',
                            order_by='AcademicTerm.display_order', cascade='all, delete-orphan')


class AcademicTerm(db.Model):
    """The three fixed terms with editable start/end dates per academic year."""
    __tablename__ = 'academic_terms'
    id = db.Column(db.Integer, primary_key=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'), nullable=False)
    name = db.Column(db.String(20), nullable=False)   # fixed: Term 1 / Term 2 / Term 3
    display_order = db.Column(db.Integer, default=0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    academic_year = db.relationship('AcademicYear', back_populates='terms')

    @property
    def label(self):
        return f'{self.name} {self.academic_year.name}' if self.academic_year else self.name


class ReportTemplate(db.Model):
    __tablename__ = 'report_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    template_type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Report(db.Model):
    __tablename__ = 'reports'
    __table_args__ = (
        db.Index('idx_report_student_term_year', 'student_id', 'academic_term', 'academic_year'),
        db.Index('idx_report_class_status', 'class_id', 'status'),
        db.Index('idx_report_class_term_year', 'class_id', 'academic_term', 'academic_year'),
        db.Index('idx_report_status', 'status'),
    )
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    academic_term = db.Column(db.String(20), nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)  # single year e.g. "2026"
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_years.id'))
    academic_term_id = db.Column(db.Integer, db.ForeignKey('academic_terms.id'))
    total_marks = db.Column(db.Float, default=0)
    average = db.Column(db.Float, default=0)
    overall_grade = db.Column(db.String(5))
    position = db.Column(db.Integer)
    grade_position = db.Column(db.Integer)
    teacher_comment = db.Column(db.Text)
    admin_comment = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')
    submitted_at = db.Column(db.DateTime)
    approved_at = db.Column(db.DateTime)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = db.relationship('Student', back_populates='reports')
    class_obj = db.relationship('Class')
    academic_year_rel = db.relationship('AcademicYear', foreign_keys=[academic_year_id])
    academic_term_rel = db.relationship('AcademicTerm', foreign_keys=[academic_term_id])
    marks = db.relationship('Mark', back_populates='report', cascade='all, delete-orphan')

    @property
    def period_label(self):
        return f'{self.academic_term} {self.academic_year}'


class Mark(db.Model):
    __tablename__ = 'marks'
    __table_args__ = (
        db.Index('idx_mark_report_subject', 'report_id', 'subject_id'),
    )
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    score = db.Column(db.Float, default=0)
    grade = db.Column(db.String(5))  # calculated automatically on save
    max_score = db.Column(db.Integer, default=100)

    report = db.relationship('Report', back_populates='marks')
    subject = db.relationship('Subject')

    @property
    def percent(self):
        if not self.max_score:
            return 0
        return (self.score or 0) / self.max_score * 100


class SchoolSetting(db.Model):
    __tablename__ = 'school_settings'
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text)

    @classmethod
    def get(cls, key, default=''):
        row = db.session.get(cls, key)
        return row.value if row and row.value is not None else default

    @classmethod
    def set(cls, key, value):
        row = db.session.get(cls, key)
        if row:
            row.value = value
        else:
            db.session.add(cls(key=key, value=value))
