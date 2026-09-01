"""Seed the Nyatsime College secondary school database with demonstration data.

Run:  python seed.py
"""
import random
from datetime import datetime, date

from app import create_app, db
from app.models import (
    User, Admin, Teacher, Student, Class, Subject, Report, Mark,
    Grade, GradeSubject, AcademicYear, AcademicTerm, TeacherSubjectClass,
)
from app.academic import calculate_grade, generate_username, slugify_name
from app.services import periods

CURRENT_YEAR = '2026'


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
        # Academic year with dated terms
        year = AcademicYear(name=CURRENT_YEAR, is_active=True)
        db.session.add(year)
        db.session.flush()

        term_dates = periods.default_term_dates(CURRENT_YEAR)
        for i, term_name in enumerate(['Term 1', 'Term 2', 'Term 3'], start=1):
            sd, ed = term_dates[term_name]
            db.session.add(AcademicTerm(
                academic_year_id=year.id, name=term_name,
                display_order=i, start_date=sd, end_date=ed,
            ))
        db.session.flush()

        # Fixed grades
        for name, order in [('Form 1', 1), ('Form 2', 2), ('Form 3', 3),
                            ('Form 4', 4), ('Lower 6', 5), ('Upper 6', 6)]:
            db.session.add(Grade(name=name, display_order=order))

        # Subjects
        subject_list = [
            ('English Language', 'ENG'), ('Mathematics', 'MATH'),
            ('Combined Science', 'SCI'), ('Biology', 'BIO'),
            ('Chemistry', 'CHEM'), ('Physics', 'PHY'),
            ('Geography', 'GEO'), ('History', 'HIST'),
            ('Shona', 'SHONA'), ('Ndebele', 'NDE'),
            ('Principles of Accounts', 'POA'), ('Commerce', 'COM'),
            ('Computer Science', 'CS'), ('Literature', 'LIT'),
            ('Heritage Studies', 'HER'), ('Physical Education', 'PE'),
        ]
        for name, code in subject_list:
            db.session.add(Subject(name=name, code=code, max_score=100))
        db.session.flush()

        grades = {g.name: g for g in Grade.query.all()}
        subjects = Subject.query.order_by(Subject.name).all()
        for grade in Grade.query.all():
            if not grade.subjects:
                grade.subjects = subjects
        db.session.flush()

        print("Seeding users...")
        # Admin
        admin_user = User(username='admin', email='admin@nyatsime.ac.zw', role='admin')
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.flush()
        db.session.add(Admin(user_id=admin_user.id, first_name='Tendai', last_name='Moyo',
                             phone='+263 772 000 001'))

        # Teachers
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

        # Classes
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

        # Teacher-subject assignments
        # Each teacher teaches specific subjects in specific classes
        subjects_dict = {s.code: s for s in Subject.query.all()}
        teacher_subject_assignments = [
            (teachers[0], classes[0], [subjects_dict['ENG'], subjects_dict['MATH']]),
            (teachers[1], classes[1], [subjects_dict['BIO'], subjects_dict['CHEM']]),
            (teachers[2], classes[2], [subjects_dict['PHY'], subjects_dict['MATH']]),
            (teachers[3], classes[3], [subjects_dict['GEO'], subjects_dict['HIST']]),
            (teachers[0], classes[4], [subjects_dict['ENG'], subjects_dict['LIT']]),
        ]
        for teacher, cls, subj_list in teacher_subject_assignments:
            for subj in subj_list:
                db.session.add(TeacherSubjectClass(
                    teacher_id=teacher.id, class_id=cls.id, subject_id=subj.id
                ))

        print("Seeding students with user accounts...")
        student_data = [
            ('Tanaka', 'Mbeki', 'NYS26001', '2012-03-15', 'Male', 0),
            ('Rutendo', 'Dube', 'NYS26002', '2012-07-22', 'Female', 0),
            ('Kudzai', 'Ncube', 'NYS26003', '2012-01-10', 'Female', 0),
            ('Tinashe', 'Chirwa', 'NYS26004', '2012-09-05', 'Male', 0),
            ('Nyasha', 'Marange', 'NYS26005', '2012-04-18', 'Female', 0),
            ('Blessing', 'Mhlanga', 'NYS26006', '2012-11-30', 'Male', 0),
            ('Chiedza', 'Gava', 'NYS26007', '2012-06-12', 'Female', 1),
            ('Takudzwa', 'Sibanda', 'NYS26008', '2012-02-28', 'Male', 1),
            ('Ruvarashe', 'Mhike', 'NYS26009', '2012-08-17', 'Female', 1),
            ('Panashe', 'Zhou', 'NYS26010', '2012-12-03', 'Male', 1),
            ('Anesu', 'Chibanda', 'NYS25011', '2011-05-20', 'Female', 2),
            ('Munashe', 'Kanyemba', 'NYS25012', '2011-10-08', 'Male', 2),
            ('Shamiso', 'Bere', 'NYS25013', '2011-03-25', 'Female', 2),
            ('Simba', 'Nyathi', 'NYS25014', '2011-07-14', 'Male', 3),
            ('Vimbai', 'Masuku', 'NYS25015', '2011-01-29', 'Female', 3),
            ('Tadiwa', 'Hungwe', 'NYS24016', '2010-09-11', 'Male', 4),
            ('Melissa', 'Rwodzi', 'NYS24017', '2010-04-06', 'Female', 4),
            ('Gilbert', 'Manyika', 'NYS23018', '2009-08-23', 'Male', 5),
            ('Precious', 'Chieza', 'NYS23019', '2009-02-17', 'Female', 5),
            ('Keith', 'Madziva', 'NYS23020', '2009-11-09', 'Male', 6),
        ]

        used_usernames = set()

        def username_exists(u):
            return u in used_usernames or User.query.filter_by(username=u).first() is not None

        students = []
        for idx, (first, last, adm, dob, gender, class_idx) in enumerate(student_data):
            # Create user account - first student gets "student1" for easy demo access
            if idx == 0:
                uname = 'student1'
                while username_exists(uname):
                    uname = f'student1{idx}'
            else:
                uname = generate_username(first, last, username_exists)
            used_usernames.add(uname)
            user = User(username=uname, email=f'{uname}@student.nyatsime.ac.zw', role='student')
            user.set_password('student123')
            db.session.add(user)
            db.session.flush()

            cls = classes[class_idx]
            student = Student(
                user_id=user.id,
                first_name=first, last_name=last, admission_number=adm,
                date_of_birth=datetime.strptime(dob, '%Y-%m-%d').date(),
                gender=gender, class_id=cls.id,
            )
            db.session.add(student)
            students.append(student)
        db.session.flush()

        print("Creating reports...")
        for student in students:
            cls = student.class_obj
            grade = cls.grade if cls else None
            grade_subjects = list(grade.subjects) if grade else subjects

            for term_name in ['Term 1', 'Term 2']:
                report = Report(
                    student_id=student.id, class_id=cls.id,
                    academic_term=term_name, academic_year=CURRENT_YEAR,
                    teacher_comment=get_random_comment(), status='published',
                    submitted_at=datetime.utcnow(), approved_at=datetime.utcnow(),
                    published_at=datetime.utcnow(),
                )
                db.session.add(report)
                db.session.flush()

                total = 0
                for subject in grade_subjects:
                    score = random.randint(32, 97)
                    pct = (score / (subject.max_score or 100)) * 100
                    mark = Mark(report_id=report.id, subject_id=subject.id, score=score,
                                grade=calculate_grade(pct), max_score=subject.max_score)
                    db.session.add(mark)
                    total += score
                report.total_marks = total
                report.average = total / len(grade_subjects) if grade_subjects else 0
                report.overall_grade = calculate_grade(report.average)

            db.session.commit()

        print("Calculating positions...")
        for cls in classes:
            for term_name in ['Term 1', 'Term 2']:
                reports = Report.query.filter_by(
                    class_id=cls.id, academic_term=term_name, academic_year=CURRENT_YEAR).all()
                reports.sort(key=lambda r: r.average, reverse=True)
                for i, report in enumerate(reports, 1):
                    report.position = i

                if cls.grade:
                    grade_class_ids = [c.id for c in cls.grade.classes]
                    grade_reports = Report.query.filter(
                        Report.class_id.in_(grade_class_ids),
                        Report.academic_term == term_name,
                        Report.academic_year == CURRENT_YEAR,
                    ).all()
                    grade_reports.sort(key=lambda r: r.average, reverse=True)
                    for i, report in enumerate(grade_reports, 1):
                        report.grade_position = i

        db.session.commit()
        print("Nyatsime College database seeded successfully!")
        print(f"Demo login: student1 / student123 (any student)")


if __name__ == '__main__':
    seed_database()
