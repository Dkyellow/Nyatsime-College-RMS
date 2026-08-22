"""Seed the Nyatsime College secondary school database with demonstration data.

Run:  python seed.py
"""
import random
from datetime import datetime

from app import create_app, db
from app.models import (
    User, Admin, Teacher, Parent, Student, Class, Subject, Report, Mark,
    ClassTeacher, Grade, GradeSubject, AcademicYear,
    AcademicTerm, GradingScale,
)

CURRENT_YEAR = '2026'


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

        print("Seeding academic structure...")
        if AcademicYear.query.count() == 0:
            year = AcademicYear(name=CURRENT_YEAR, is_current=True)
            db.session.add(year)
            db.session.flush()
            for i, term in enumerate(['Term 1', 'Term 2', 'Term 3'], start=1):
                db.session.add(AcademicTerm(academic_year_id=year.id, name=term, display_order=i))

        if Grade.query.count() == 0:
            for name, order in [('Form 1', 1), ('Form 2', 2), ('Form 3', 3),
                                ('Form 4', 4), ('Lower 6', 5), ('Upper 6', 6)]:
                db.session.add(Grade(name=name, display_order=order))
        if Subject.query.count() == 0:
            for name, code in [('English Language', 'ENG'), ('Mathematics', 'MATH'),
                               ('Combined Science', 'SCI'), ('Geography', 'GEO'),
                               ('History', 'HIST'), ('Shona', 'SHONA'),
                               ('Computer Science', 'CS'), ('Principles of Accounts', 'POA')]:
                db.session.add(Subject(name=name, code=code, max_score=100))
        db.session.flush()

        grades = {g.name: g for g in Grade.query.all()}
        subjects = Subject.query.order_by(Subject.name).all()
        for grade in Grade.query.all():
            if not grade.subjects:
                grade.subjects = subjects
        db.session.flush()

        print("Seeding users...")
        admin_user = User(username='admin', email='admin@nyatsime.ac.zw', role='admin')
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.flush()
        db.session.add(Admin(user_id=admin_user.id, first_name='Tendai', last_name='Moyo', phone='+263 772 000 001'))

        teachers = []
        teacher_data = [
            ('teacher1', 'teacher123', 'r.chikwanha@nyatsime.ac.zw', 'Rudo', 'Chikwanha', 'NYT-T01', '+263 772 000 011'),
            ('teacher2', 'teacher123', 'b.ndlovu@nyatsime.ac.zw', 'Blessing', 'Ndlovu', 'NYT-T02', '+263 772 000 012'),
            ('teacher3', 'teacher123', 'f.mhike@nyatsime.ac.zw', 'Farai', 'Mhike', 'NYT-T03', '+263 772 000 013'),
            ('teacher4', 'teacher123', 's.mutasa@nyatsime.ac.zw', 'Sarudzai', 'Mutasa', 'NYT-T04', '+263 772 000 014'),
        ]
        for username, password, email, first, last, emp_id, phone in teacher_data:
            user = User(username=username, email=email, role='teacher')
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            teacher = Teacher(user_id=user.id, first_name=first, last_name=last, phone=phone, employee_id=emp_id)
            db.session.add(teacher)
            teachers.append(teacher)
        db.session.flush()

        parents = []
        parent_data = [
            ('parent1', 'parent123', 'j.mbeki@email.com', 'Joseph', 'Mbeki', '+263 771 111 201', '12 Chitungwiza Road, Harare'),
            ('parent2', 'parent123', 'm.dube@email.com', 'Mercy', 'Dube', '+263 771 111 202', '45 Seke Road, Chitungwiza'),
            ('parent3', 'parent123', 't.ncube@email.com', 'Themba', 'Ncube', '+263 771 111 203', '8 Josiah Tongogara St, Harare'),
            ('parent4', 'parent123', 'l.chirwa@email.com', 'Loveness', 'Chirwa', '+263 771 111 204', '23 Highfield Crescent, Harare'),
            ('parent5', 'parent123', 'd.marange@email.com', 'Dumisani', 'Marange', '+263 771 111 205', '7 Ruwa Drive, Ruwa'),
        ]
        for username, password, email, first, last, phone, address in parent_data:
            user = User(username=username, email=email, role='parent')
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            parent = Parent(user_id=user.id, first_name=first, last_name=last, phone=phone, address=address)
            db.session.add(parent)
            parents.append(parent)
        db.session.flush()

        print("Seeding classes and streams...")
        class_plan = [
            ('Form 1A', 'A', 'Form 1'), ('Form 1B', 'B', 'Form 1'),
            ('Form 2A', 'A', 'Form 2'), ('Form 3 Science', 'Science', 'Form 3'),
            ('Form 4A', 'A', 'Form 4'), ('Lower 6 Arts', 'Arts', 'Lower 6'),
            ('Upper 6 Science', 'Science', 'Upper 6'),
        ]
        classes = []
        for name, section, grade_name in class_plan:
            grade = grades.get(grade_name)
            cls = Class(name=name, section=section, grade_id=grade.id if grade else None)
            db.session.add(cls)
            classes.append(cls)
        db.session.flush()

        db.session.add(ClassTeacher(class_id=classes[0].id, teacher_id=teachers[0].id))
        db.session.add(ClassTeacher(class_id=classes[1].id, teacher_id=teachers[1].id))
        db.session.add(ClassTeacher(class_id=classes[2].id, teacher_id=teachers[2].id))
        db.session.add(ClassTeacher(class_id=classes[3].id, teacher_id=teachers[3].id))
        db.session.add(ClassTeacher(class_id=classes[4].id, teacher_id=teachers[0].id))

        print("Seeding students...")
        student_data = [
            ('Tanaka', 'Mbeki', 'NYS26001', '2012-03-15', 'Male', 0, 0),
            ('Rutendo', 'Dube', 'NYS26002', '2012-07-22', 'Female', 0, 1),
            ('Kudzai', 'Ncube', 'NYS26003', '2012-01-10', 'Female', 0, 2),
            ('Tinashe', 'Chirwa', 'NYS26004', '2012-09-05', 'Male', 0, 3),
            ('Nyasha', 'Marange', 'NYS26005', '2012-04-18', 'Female', 0, 4),
            ('Blessing', 'Mhlanga', 'NYS26006', '2012-11-30', 'Male', 0, 0),
            ('Chiedza', 'Gava', 'NYS26007', '2012-06-12', 'Female', 0, 1),
            ('Takudzwa', 'Sibanda', 'NYS26008', '2012-02-28', 'Male', 1, 2),
            ('Ruvarashe', 'Mhike', 'NYS26009', '2012-08-17', 'Female', 1, 3),
            ('Panashe', 'Zhou', 'NYS26010', '2012-12-03', 'Male', 1, 4),
            ('Anesu', 'Chibanda', 'NYS25011', '2011-05-20', 'Female', 2, 0),
            ('Munashe', 'Kanyemba', 'NYS25012', '2011-10-08', 'Male', 2, 1),
            ('Shamiso', 'Bere', 'NYS25013', '2011-03-25', 'Female', 2, 2),
            ('Simba', 'Nyathi', 'NYS25014', '2011-07-14', 'Male', 3, 3),
            ('Vimbai', 'Masuku', 'NYS25015', '2011-01-29', 'Female', 3, 4),
            ('Tadiwa', 'Hungwe', 'NYS24016', '2010-09-11', 'Male', 4, 0),
            ('Melissa', 'Rwodzi', 'NYS24017', '2010-04-06', 'Female', 4, 1),
            ('Gilbert', 'Manyika', 'NYS23018', '2009-08-23', 'Male', 5, 2),
            ('Precious', 'Chieza', 'NYS23019', '2009-02-17', 'Female', 5, 3),
            ('Keith', 'Madziva', 'NYS23020', '2009-11-09', 'Male', 6, 4),
        ]

        students = []
        for first, last, adm, dob, gender, class_idx, parent_idx in student_data:
            cls = classes[class_idx]
            student = Student(
                first_name=first, last_name=last, admission_number=adm,
                date_of_birth=datetime.strptime(dob, '%Y-%m-%d').date(),
                gender=gender, class_id=cls.id, parent_id=parents[parent_idx].id,
            )
            db.session.add(student)
            students.append(student)
        db.session.flush()

        print("Creating reports...")
        terms = ['Term 1', 'Term 2']
        for student in students:
            cls = student.class_obj
            grade = cls.grade if cls else None
            grade_subjects = list(grade.subjects) if grade else subjects

            for term in terms:
                report = Report(
                    student_id=student.id, class_id=cls.id,
                    academic_term=term, academic_year=CURRENT_YEAR,
                    teacher_comment=get_random_comment(), status='published',
                    submitted_at=datetime.utcnow(), approved_at=datetime.utcnow(),
                    published_at=datetime.utcnow(),
                )
                db.session.add(report)
                db.session.flush()

                total = 0
                for subject in grade_subjects:
                    score = random.randint(32, 97)
                    mark = Mark(report_id=report.id, subject_id=subject.id, score=score,
                                grade=calculate_grade(score), max_score=subject.max_score)
                    db.session.add(mark)
                    total += score
                report.total_marks = total
                report.average = total / len(grade_subjects) if grade_subjects else 0
                report.overall_grade = calculate_grade(report.average)

            db.session.commit()

        print("Calculating positions...")
        for cls in classes:
            for term in terms:
                reports = Report.query.filter_by(
                    class_id=cls.id, academic_term=term, academic_year=CURRENT_YEAR).all()
                reports.sort(key=lambda r: r.average, reverse=True)
                for i, report in enumerate(reports, 1):
                    report.position = i

                if cls.grade:
                    grade_class_ids = [c.id for c in cls.grade.classes]
                    grade_reports = Report.query.filter(
                        Report.class_id.in_(grade_class_ids),
                        Report.academic_term == term,
                        Report.academic_year == CURRENT_YEAR,
                    ).all()
                    grade_reports.sort(key=lambda r: r.average, reverse=True)
                    for i, report in enumerate(grade_reports, 1):
                        report.grade_position = i

        db.session.commit()
        print("Nyatsime College database seeded successfully!")


if __name__ == '__main__':
    seed_database()
