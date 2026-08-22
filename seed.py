import random
from datetime import datetime
from app import create_app, db
from app.models import (
    User, Admin, Teacher, Parent, Student, Class, Subject, Report, Mark,
    ClassTeacher, EducationLevel, Grade, GradeSubject, AcademicYear,
    AcademicTerm, GradingScale, ReportTemplate, ECDAssessmentField,
    ECDAssessmentMark
)


def calculate_grade(score, education_level_id=None):
    if education_level_id:
        scales = GradingScale.query.filter_by(education_level_id=education_level_id, is_active=True).order_by(GradingScale.display_order).all()
        for scale in scales:
            if scale.min_score <= score <= scale.max_score:
                return scale.grade_letter
    if score >= 90: return 'A+'
    elif score >= 80: return 'A'
    elif score >= 70: return 'B+'
    elif score >= 60: return 'B'
    elif score >= 50: return 'C+'
    elif score >= 40: return 'C'
    elif score >= 30: return 'D'
    else: return 'F'


def get_random_comment():
    comments = [
        "Excellent performance this term. Keep up the great work!",
        "Good progress made. Continue to work hard.",
        "Consistent effort shown. Room for improvement in some areas.",
        "Well done! Your dedication is paying off.",
        "Good attitude towards learning. Keep striving for excellence.",
        "A solid term with good results. Stay focused!",
        "Great improvement this term. Very proud of your progress.",
        "Keep up the good work. You're doing well!",
    ]
    return random.choice(comments)


def seed_database():
    app = create_app()
    with app.app_context():
        db.create_all()

        if User.query.first():
            print("Database already seeded. Skipping.")
            return

        print("Seeding users...")
        admin_user = User(username='admin', email='admin@gillingham.edu', role='admin')
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.flush()
        db.session.add(Admin(user_id=admin_user.id, first_name='John', last_name='Smith', phone='555-0100'))

        teachers = []
        for username, password, email, first, last, emp_id, phone in [
            ('teacher1', 'teacher123', 'sarah.johnson@gillingham.edu', 'Sarah', 'Johnson', 'EMP001', '555-0101'),
            ('teacher2', 'teacher123', 'michael.williams@gillingham.edu', 'Michael', 'Williams', 'EMP002', '555-0102'),
        ]:
            user = User(username=username, email=email, role='teacher')
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            teacher = Teacher(user_id=user.id, first_name=first, last_name=last, phone=phone, employee_id=emp_id)
            db.session.add(teacher)
            teachers.append(teacher)
        db.session.flush()

        parents = []
        for username, password, email, first, last, phone, address in [
            ('parent1', 'parent123', 'james.brown@email.com', 'James', 'Brown', '555-0201', '123 Oak Street'),
            ('parent2', 'parent123', 'emma.davis@email.com', 'Emma', 'Davis', '555-0202', '456 Elm Avenue'),
            ('parent3', 'parent123', 'robert.wilson@email.com', 'Robert', 'Wilson', '555-0203', '789 Pine Road'),
            ('parent4', 'parent123', 'lisa.taylor@email.com', 'Lisa', 'Taylor', '555-0204', '321 Cedar Lane'),
            ('parent5', 'parent123', 'david.martinez@email.com', 'David', 'Martinez', '555-0205', '654 Maple Drive'),
        ]:
            user = User(username=username, email=email, role='parent')
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            parent = Parent(user_id=user.id, first_name=first, last_name=last, phone=phone, address=address)
            db.session.add(parent)
            parents.append(parent)
        db.session.flush()

        print("Seeding classes...")
        grade_objects = {g.name: g for g in Grade.query.all()}
        g1 = grade_objects.get('Grade 1')
        g2 = grade_objects.get('Grade 2')
        g3 = grade_objects.get('Grade 3')
        classes = []
        for name, section, grade in [('Class 1A', 'A', g1), ('Class 2A', 'A', g2), ('Class 3A', 'A', g3)]:
            if grade:
                cls = Class(name=name, section=section, grade_id=grade.id)
                db.session.add(cls)
                classes.append(cls)
        db.session.flush()

        db.session.add(ClassTeacher(class_id=classes[0].id, teacher_id=teachers[0].id))
        db.session.add(ClassTeacher(class_id=classes[1].id, teacher_id=teachers[0].id))
        db.session.add(ClassTeacher(class_id=classes[2].id, teacher_id=teachers[1].id))

        print("Seeding students...")
        student_data = [
            ('Emma', 'Johnson', 'ADM001', '2015-03-15', 'Female', 0, 0),
            ('Liam', 'Smith', 'ADM002', '2015-07-22', 'Male', 0, 1),
            ('Olivia', 'Brown', 'ADM003', '2015-01-10', 'Female', 0, 2),
            ('Noah', 'Davis', 'ADM004', '2015-09-05', 'Male', 0, 3),
            ('Sophia', 'Wilson', 'ADM005', '2015-04-18', 'Female', 0, 4),
            ('William', 'Taylor', 'ADM006', '2015-11-30', 'Male', 1, 0),
            ('Isabella', 'Martinez', 'ADM007', '2015-06-12', 'Female', 1, 1),
            ('James', 'Anderson', 'ADM008', '2015-02-28', 'Male', 1, 2),
            ('Mia', 'Thomas', 'ADM009', '2015-08-17', 'Female', 1, 3),
            ('Benjamin', 'Jackson', 'ADM010', '2015-12-03', 'Male', 1, 4),
            ('Charlotte', 'White', 'ADM011', '2014-05-20', 'Female', 2, 0),
            ('Lucas', 'Harris', 'ADM012', '2014-10-08', 'Male', 2, 1),
            ('Amelia', 'Martin', 'ADM013', '2014-03-25', 'Female', 2, 2),
            ('Henry', 'Thompson', 'ADM014', '2014-07-14', 'Male', 2, 3),
            ('Harper', 'Garcia', 'ADM015', '2014-01-29', 'Female', 2, 4),
            ('Alexander', 'Martinez', 'ADM016', '2014-09-11', 'Male', 2, 0),
            ('Evelyn', 'Robinson', 'ADM017', '2014-04-06', 'Female', 2, 1),
            ('Daniel', 'Clark', 'ADM018', '2014-08-23', 'Male', 2, 2),
            ('Abigail', 'Rodriguez', 'ADM019', '2014-02-17', 'Female', 2, 3),
            ('Michael', 'Lewis', 'ADM020', '2014-11-09', 'Male', 2, 4),
        ]

        students = []
        for first, last, adm, dob, gender, class_idx, parent_idx in student_data:
            cls = classes[class_idx]
            level_id = cls.grade.education_level_id if cls.grade else None
            student = Student(
                first_name=first, last_name=last, admission_number=adm,
                date_of_birth=datetime.strptime(dob, '%Y-%m-%d').date(),
                gender=gender, class_id=cls.id, parent_id=parents[parent_idx].id,
                education_level_id=level_id
            )
            db.session.add(student)
            students.append(student)
        db.session.flush()

        print("Creating reports...")
        for student in students:
            cls = student.class_obj
            grade = cls.grade if cls else None
            level_id = grade.education_level_id if grade else None
            ecd_level = EducationLevel.query.filter_by(name='ECD').first()
            is_ecd = grade and grade.education_level and grade.education_level.name == 'ECD'

            for term in ['Term 1', 'Term 2']:
                report = Report(
                    student_id=student.id, class_id=cls.id,
                    academic_term=term, academic_year='2024/2025',
                    education_level_id=level_id,
                    teacher_comment=get_random_comment(), status='published',
                    submitted_at=datetime.utcnow(), approved_at=datetime.utcnow(), published_at=datetime.utcnow()
                )
                db.session.add(report)
                db.session.flush()

                if is_ecd:
                    ecd_fields = ECDAssessmentField.query.filter_by(is_active=True).all()
                    total = 0
                    for field in ecd_fields:
                        score = random.randint(50, 100)
                        grade_letter = calculate_grade(score, level_id)
                        mark = ECDAssessmentMark(report_id=report.id, assessment_field_id=field.id, score=score, grade=grade_letter)
                        db.session.add(mark)
                        total += score
                    report.total_marks = total
                    report.average = total / len(ecd_fields) if ecd_fields else 0
                    report.overall_grade = calculate_grade(report.average, level_id)
                else:
                    grade_subjects = grade.subjects if grade else Subject.query.all()
                    total = 0
                    for subject in grade_subjects:
                        score = random.randint(45, 98)
                        grade_letter = calculate_grade(score, level_id)
                        mark = Mark(report_id=report.id, subject_id=subject.id, score=score, grade=grade_letter, max_score=subject.max_score)
                        db.session.add(mark)
                        total += score
                    report.total_marks = total
                    report.average = total / len(grade_subjects) if grade_subjects else 0
                    report.overall_grade = calculate_grade(report.average, level_id)

            db.session.commit()

        print("Calculating positions...")
        for cls in classes:
            for term in ['Term 1', 'Term 2']:
                reports = Report.query.filter_by(class_id=cls.id, academic_term=term, academic_year='2024/2025').all()
                reports.sort(key=lambda r: r.average, reverse=True)
                for i, report in enumerate(reports, 1):
                    report.position = i

                if cls.grade:
                    grade_class_ids = [c.id for c in cls.grade.classes]
                    grade_reports = Report.query.filter(
                        Report.class_id.in_(grade_class_ids),
                        Report.academic_term == term,
                        Report.academic_year == '2024/2025'
                    ).all()
                    grade_reports.sort(key=lambda r: r.average, reverse=True)
                    for i, report in enumerate(grade_reports, 1):
                        report.grade_position = i

        db.session.commit()
        print("Database seeded successfully!")


if __name__ == '__main__':
    seed_database()
