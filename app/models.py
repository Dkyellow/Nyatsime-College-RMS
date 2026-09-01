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

    @property
    def classes(self):
        """Get unique classes this teacher is assigned to."""
        from sqlalchemy import distinct
        class_ids = db.session.query(TeacherSubjectClass.class_id).filter_by(teacher_id=self.id).distinct().all()
        if not class_ids:
            return []
        return Class.query.filter(Class.id.in_([c[0] for c in class_ids])).all()

    def get_subjects_for_class(self, class_id):
        """Get subjects this teacher teaches in a specific class."""
        assignments = TeacherSubjectClass.query.filter_by(teacher_id=self.id, class_id=class_id).all()
        return [a.subject for a in assignments]


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

    grade = db.relationship('Grade', back_populates='classes')
    students = db.relationship('Student', back_populates='class_obj')

    @property
    def grade_level(self):
        return self.grade.name if self.grade else None

    @property
    def teachers(self):
        """Get unique teachers assigned to this class via subject assignments."""
        from sqlalchemy import distinct
        teacher_ids = db.session.query(TeacherSubjectClass.teacher_id).filter_by(class_id=self.id).distinct().all()
        if not teacher_ids:
            return []
        return Teacher.query.filter(Teacher.id.in_([t[0] for t in teacher_ids])).all()

    def get_teachers_for_subject(self, subject_id):
        """Get teachers assigned to teach a specific subject in this class."""
        assignments = TeacherSubjectClass.query.filter_by(class_id=self.id, subject_id=subject_id).all()
        return [a.teacher for a in assignments]

    def get_subjects_for_teacher(self, teacher_id):
        """Get subjects a specific teacher teaches in this class."""
        assignments = TeacherSubjectClass.query.filter_by(class_id=self.id, teacher_id=teacher_id).all()
        return [a.subject for a in assignments]


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


class StudentSubject(db.Model):
    """Tracks which subjects a student is enrolled in."""
    __tablename__ = 'student_subjects'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    academic_year = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref=db.backref('student_subjects', cascade='all, delete-orphan'))
    subject = db.relationship('Subject', backref=db.backref('student_enrollments'))

    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', 'academic_year', name='uq_student_subject_year'),
    )


class StudentPromotion(db.Model):
    """Tracks student promotions/transitions between forms."""
    __tablename__ = 'student_promotions'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    from_class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    to_class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    from_grade_id = db.Column(db.Integer, db.ForeignKey('grades.id'))
    to_grade_id = db.Column(db.Integer, db.ForeignKey('grades.id'))
    academic_year = db.Column(db.String(10), nullable=False)
    promotion_type = db.Column(db.String(20), nullable=False)  # auto, manual, graduate
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref=db.backref('promotions'))
    from_class = db.relationship('Class', foreign_keys=[from_class_id])
    to_class = db.relationship('Class', foreign_keys=[to_class_id])
    from_grade = db.relationship('Grade', foreign_keys=[from_grade_id])
    to_grade = db.relationship('Grade', foreign_keys=[to_grade_id])


class TeacherSubjectClass(db.Model):
    """Links a teacher to a specific subject in a specific class."""
    __tablename__ = 'teacher_subject_classes'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teacher = db.relationship('Teacher', backref=db.backref('subject_assignments', cascade='all, delete-orphan'))
    class_obj = db.relationship('Class', backref=db.backref('teacher_subject_assignments', cascade='all, delete-orphan'))
    subject = db.relationship('Subject', backref=db.backref('teacher_assignments', cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'class_id', 'subject_id', name='uq_teacher_class_subject'),
    )


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


class AuditLog(db.Model):
    """Tracks user actions for accountability."""
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))
