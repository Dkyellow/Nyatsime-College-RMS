import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import (
    User, Admin, Teacher, Parent, Student, Class, Subject, Report, Mark,
    ClassTeacher, EducationLevel, Grade, GradeSubject, AcademicYear,
    AcademicTerm, GradingScale, ReportTemplate, ECDAssessmentField,
    ECDAssessmentMark
)


def migrate_database():
    app = create_app()
    with app.app_context():
        print("Creating all tables...")
        db.create_all()

        if EducationLevel.query.first():
            print("Migration already done. Skipping.")
            return

        print("Seeding education levels...")
        ecd = EducationLevel(name='ECD', description='Early Childhood Development', display_order=1)
        primary = EducationLevel(name='Primary', description='Primary Education (Grade 1-7)', display_order=2)
        secondary = EducationLevel(name='Secondary', description='Secondary Education (Form 1-4)', display_order=3)
        db.session.add_all([ecd, primary, secondary])
        db.session.flush()

        print("Seeding grades...")
        grades_data = [
            (ecd.id, 'ECD A', 1), (ecd.id, 'ECD B', 2),
            (primary.id, 'Grade 1', 1), (primary.id, 'Grade 2', 2),
            (primary.id, 'Grade 3', 3), (primary.id, 'Grade 4', 4),
            (primary.id, 'Grade 5', 5), (primary.id, 'Grade 6', 6),
            (primary.id, 'Grade 7', 7),
            (secondary.id, 'Form 1', 1), (secondary.id, 'Form 2', 2),
            (secondary.id, 'Form 3', 3), (secondary.id, 'Form 4', 4),
        ]
        grade_objects = {}
        for level_id, name, order in grades_data:
            g = Grade(education_level_id=level_id, name=name, display_order=order)
            db.session.add(g)
            db.session.flush()
            grade_objects[name] = g

        print("Seeding academic years and terms...")
        ay1 = AcademicYear(name='2024/2025', is_current=True)
        ay2 = AcademicYear(name='2025/2026', is_current=False)
        db.session.add_all([ay1, ay2])
        db.session.flush()

        for ay in [ay1, ay2]:
            for i, term_name in enumerate(['Term 1', 'Term 2', 'Term 3'], 1):
                t = AcademicTerm(academic_year_id=ay.id, name=term_name, display_order=i)
                db.session.add(t)

        print("Seeding grading scales...")
        primary_scale = [
            ('A+', 90, 100, 'A+', 'Excellent', 1),
            ('A', 80, 89.99, 'A', 'Very Good', 2),
            ('B+', 70, 79.99, 'B+', 'Good', 3),
            ('B', 60, 69.99, 'B', 'Above Average', 4),
            ('C+', 50, 59.99, 'C+', 'Average', 5),
            ('C', 40, 49.99, 'C', 'Below Average', 6),
            ('D', 30, 39.99, 'D', 'Poor', 7),
            ('F', 0, 29.99, 'F', 'Fail', 8),
        ]
        for level in [primary, secondary]:
            for name, min_s, max_s, letter, desc, order in primary_scale:
                gs = GradingScale(
                    education_level_id=level.id, name=name,
                    min_score=min_s, max_score=max_s, grade_letter=letter,
                    description=desc, display_order=order
                )
                db.session.add(gs)

        ecd_scale = [
            ('Advanced', 85, 100, 'ADV', 'Advanced', 1),
            ('Proficient', 70, 84.99, 'PRO', 'Proficient', 2),
            ('Progressing', 50, 69.99, 'PRG', 'Progressing', 3),
            ('Developing', 0, 49.99, 'DEV', 'Developing', 4),
        ]
        for name, min_s, max_s, letter, desc, order in ecd_scale:
            gs = GradingScale(
                education_level_id=ecd.id, name=name,
                min_score=min_s, max_score=max_s, grade_letter=letter,
                description=desc, display_order=order
            )
            db.session.add(gs)

        print("Seeding subjects...")
        subjects_data = [
            ('Mathematics', 'MATH'), ('English', 'ENG'), ('Science', 'SCI'),
            ('Social Studies', 'SOC'), ('Physical Education', 'PE'), ('Art', 'ART'),
            ('Agriculture', 'AGR'), ('Shona', 'SHO'),
            ('Biology', 'BIO'), ('Chemistry', 'CHE'), ('Physics', 'PHY'),
            ('Geography', 'GEO'), ('History', 'HIS'), ('Computer Science', 'CS'),
        ]
        subjects = {}
        for name, code in subjects_data:
            s = Subject(name=name, code=code, max_score=100)
            db.session.add(s)
            db.session.flush()
            subjects[code] = s

        print("Assigning subjects to grades...")
        primary_subj_codes = ['MATH', 'ENG', 'SCI', 'SOC', 'PE', 'ART']
        primary_upper_codes = ['MATH', 'ENG', 'SCI', 'SOC', 'PE', 'ART', 'AGR', 'SHO']
        secondary_codes = ['MATH', 'ENG', 'BIO', 'CHE', 'PHY', 'GEO', 'HIS', 'CS']

        for grade_name, g_obj in grade_objects.items():
            if grade_name in ['ECD A', 'ECD B']:
                continue
            elif grade_name in ['Grade 1', 'Grade 2', 'Grade 3']:
                codes = primary_subj_codes
            elif grade_name in ['Grade 4', 'Grade 5', 'Grade 6', 'Grade 7']:
                codes = primary_upper_codes
            else:
                codes = secondary_codes
            for code in codes:
                if code in subjects:
                    gs = GradeSubject(grade_id=g_obj.id, subject_id=subjects[code].id)
                    db.session.add(gs)

        print("Seeding ECD assessment fields...")
        ecd_fields = [
            ('Social Skills', 'Interaction with peers and adults', 1),
            ('Motor Skills', 'Physical coordination and movement', 2),
            ('Cognitive Development', 'Problem solving and thinking skills', 3),
            ('Language', 'Communication and literacy skills', 4),
            ('Creative Expression', 'Art, music, and imaginative play', 5),
        ]
        for name, desc, order in ecd_fields:
            f = ECDAssessmentField(name=name, description=desc, display_order=order)
            db.session.add(f)

        print("Seeding report templates...")
        for level, ttype, name in [
            (ecd, 'ecd', 'ECD Developmental Report'),
            (primary, 'primary', 'Primary School Report Card'),
            (secondary, 'secondary', 'Secondary School Report Card'),
        ]:
            rt = ReportTemplate(
                education_level_id=level.id, name=name,
                template_type=ttype, is_default=True
            )
            db.session.add(rt)

        db.session.commit()
        print("Migration completed successfully!")


if __name__ == '__main__':
    migrate_database()
