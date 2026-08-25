"""Migrate the school reports database to a white-label secondary-school system.

Changes applied:
  - Adds Student.user_id column if missing
  - Adds AcademicTerm.start_date / end_date columns if missing
  - Normalizes academic year values ("2026/2027" -> "2026")
  - Creates user accounts for students that lack them
  - Removes parent user accounts
  - Drops grading_scales table if present
  - Ensures fixed secondary school forms exist
  - Seeds default subjects, grade-subject mappings, academic year/terms
  - Seeds all SchoolSetting defaults (Nyatsime College) if not yet configured

Run:  python migrate_database.py
"""
import os
import re
import sqlite3
from datetime import datetime

from app import create_app, db
from app.models import (
    Grade, GradeSubject, Subject, AcademicYear, AcademicTerm,
    ReportTemplate, SchoolSetting, User, Student, Admin, Teacher,
)
from app.academic import generate_username, FIXED_FORMS

BASEDIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.environ.get('DATABASE_URL') or os.path.join(BASEDIR, 'school_reports.db')
if DB_PATH.startswith('sqlite:///'):
    DB_PATH = DB_PATH.replace('sqlite:///', '')
if not os.path.isabs(DB_PATH):
    DB_PATH = os.path.join(BASEDIR, DB_PATH)

DEFAULT_SUBJECTS = [
    ('English Language', 'ENG', 100), ('Mathematics', 'MATH', 100),
    ('Combined Science', 'SCI', 100), ('Biology', 'BIO', 100),
    ('Chemistry', 'CHEM', 100), ('Physics', 'PHY', 100),
    ('Geography', 'GEO', 100), ('History', 'HIST', 100),
    ('Shona', 'SHONA', 100), ('Ndebele', 'NDE', 100),
    ('Principles of Accounts', 'POA', 100), ('Commerce', 'COM', 100),
    ('Computer Science', 'CS', 100), ('Literature in English', 'LIT', 100),
    ('Heritage Studies', 'HER', 100), ('Physical Education', 'PE', 100),
]


def table_exists(cur, name):
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def column_exists(cur, table, column):
    return any(col[1] == column for col in cur.execute(f'PRAGMA table_info({table})').fetchall())


def migrate_schema(conn):
    cur = conn.cursor()

    # --- Drop obsolete tables ---
    for t in ('ecd_assessment_marks', 'ecd_assessment_fields', 'education_levels',
              'grading_scales', 'parents'):
        if table_exists(cur, t):
            cur.execute(f'DROP TABLE IF EXISTS "{t}"')
            print(f'  dropped table {t}')

    # --- Remove education_level_id columns where they linger ---
    for table in ['grades', 'report_templates', 'students', 'reports']:
        if table_exists(cur, table) and column_exists(cur, table, 'education_level_id'):
            sql = cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()[0]
            try:
                cur.execute(f'ALTER TABLE {table} DROP COLUMN education_level_id')
                print(f'  dropped column {table}.education_level_id')
                continue
            except sqlite3.OperationalError:
                pass
            new_sql = re.sub(
                r',\s*["\']?education_level_id["\']?\s+INTEGER[^,\)]*', '', sql,
                count=1, flags=re.IGNORECASE)
            old, tmp = f'{table}__old', f'{table}__new'
            cur.execute(f'ALTER TABLE "{table}" RENAME TO "{old}"')
            cur.execute(new_sql.replace(f'CREATE TABLE "{table}"', f'CREATE TABLE "{tmp}"', 1)
                              .replace(f'CREATE TABLE {table}', f'CREATE TABLE {tmp}', 1))
            col_list = ', '.join(c[1] for c in cur.execute(f'PRAGMA table_info("{tmp}")').fetchall())
            cur.execute(f'INSERT INTO main."{tmp}" ({col_list}) SELECT {col_list} FROM main."{old}"')
            cur.execute(f'DROP TABLE "{old}"')
            cur.execute(f'ALTER TABLE "{tmp}" RENAME TO "{table}"')
            print(f'  rebuilt {table} without education_level_id')

    # --- Add Student.user_id column if missing ---
    if table_exists(cur, 'students') and not column_exists(cur, 'students', 'user_id'):
        cur.execute('ALTER TABLE students ADD COLUMN user_id INTEGER REFERENCES users(id)')
        print('  added students.user_id column')

    # --- Add AcademicTerm.start_date / end_date if missing ---
    if table_exists(cur, 'academic_terms'):
        if not column_exists(cur, 'academic_terms', 'start_date'):
            cur.execute('ALTER TABLE academic_terms ADD COLUMN start_date DATE')
            print('  added academic_terms.start_date column')
        if not column_exists(cur, 'academic_terms', 'end_date'):
            cur.execute('ALTER TABLE academic_terms ADD COLUMN end_date DATE')
            print('  added academic_terms.end_date column')

    # --- Normalize academic year values ---
    for table_name in ['reports', 'academic_terms', 'academic_years']:
        if not table_exists(cur, table_name):
            continue
        year_col = 'name' if table_name == 'academic_years' else 'academic_year'
        if not column_exists(cur, table_name, year_col):
            continue
        rows = cur.execute(f'SELECT id, {year_col} FROM {table_name}').fetchall()
        for rid, val in rows:
            if val and '/' in str(val):
                new_val = re.match(r'(\d{4})', str(val))
                if new_val:
                    cur.execute(f'UPDATE {table_name} SET {year_col} = ? WHERE id = ?',
                                (new_val.group(1), rid))
                    print(f'  normalized {table_name} id={rid}: "{val}" -> "{new_val.group(1)}"')

    # --- Remove parent user accounts ---
    if table_exists(cur, 'users'):
        cur.execute("DELETE FROM users WHERE role = 'parent'")
        print('  removed parent user accounts')

    # --- Remove parent_id from students if column exists ---
    if table_exists(cur, 'students') and column_exists(cur, 'students', 'parent_id'):
        cur.execute('ALTER TABLE students DROP COLUMN parent_id')
        print('  dropped students.parent_id column')

    conn.commit()


def seed_structure(app):
    with app.app_context():
        db.create_all()

        # Forms
        existing = {g.name for g in Grade.query.all()}
        for name, order in FIXED_FORMS:
            if name not in existing:
                db.session.add(Grade(name=name, display_order=order))
        db.session.flush()

        # Subjects
        if Subject.query.count() == 0:
            for name, code, mx in DEFAULT_SUBJECTS:
                db.session.add(Subject(name=name, code=code, max_score=mx))
            print('Default subjects seeded.')

        # Assign subjects to forms
        if GradeSubject.query.count() == 0:
            all_subjects = Subject.query.all()
            for grade in Grade.query.all():
                for subj in all_subjects:
                    db.session.add(GradeSubject(grade_id=grade.id, subject_id=subj.id))
            print('Subjects assigned to all forms.')

        # Academic year + terms with dates
        if AcademicYear.query.count() == 0:
            from app.services import periods
            year = AcademicYear(name='2026', is_active=True)
            db.session.add(year)
            db.session.flush()
            term_dates = periods.default_term_dates('2026')
            for i, term_name in enumerate(['Term 1', 'Term 2', 'Term 3'], start=1):
                sd, ed = term_dates[term_name]
                db.session.add(AcademicTerm(
                    academic_year_id=year.id, name=term_name,
                    display_order=i, start_date=sd, end_date=ed,
                    is_active=(i == 1)))
            print('Academic year 2026 with dated terms seeded.')

        # Default report template
        if ReportTemplate.query.count() == 0:
            db.session.add(ReportTemplate(
                name='Nyatsime College Secondary Report Card',
                template_type='secondary',
                description='Official academic report card for all forms',
                is_default=True))
            print('Report template seeded.')

        # Brand defaults
        defaults = {
            'school_name': 'NYATSIME COLLEGE',
            'school_motto': 'Knowledge | Integrity | Excellence',
            'school_address': 'P.O. Box Nyatsime, Zimbabwe',
            'school_phone': '',
            'school_email': '',
        }
        for k, v in defaults.items():
            if not SchoolSetting.query.get(k):
                db.session.add(SchoolSetting(key=k, value=v))

        # Create student user accounts for students missing them
        used_usernames = set(u.username for u in User.query.all())
        def username_exists(u):
            return u in used_usernames

        students_without_users = Student.query.filter(Student.user_id.is_(None)).all()
        if students_without_users:
            for s in students_without_users:
                uname = generate_username(s.first_name, s.last_name, username_exists)
                used_usernames.add(uname)
                user = User(username=uname, email=f'{uname}@student.nyatsime.ac.zw', role='student')
                user.set_password('student123')
                db.session.add(user)
                db.session.flush()
                s.user_id = user.id
            print(f'Created {len(students_without_users)} student user accounts.')

        db.session.commit()


def seed_school_settings(app):
    """Populate SchoolSetting with Nyatsime College defaults for any keys not yet set."""
    defaults = {
        'school_name':       'NYATSIME COLLEGE',
        'school_short_name': 'Secondary School',
        'school_motto':      'Knowledge | Integrity | Excellence',
        'school_address':    'P.O. Box Nyatsime, Zimbabwe',
        'school_city':       'Harare',
        'school_country':    'Zimbabwe',
        'school_phone':      '',
        'school_email':      '',
        'school_website':    '',
        'primary_color':     '#0370b1',
        'accent_color':      '#F0B429',
        'report_footer':     '',
        'logo_filename':     '',
    }
    with app.app_context():
        changed = False
        for key, value in defaults.items():
            existing = SchoolSetting.get(key, None)
            if existing is None or existing == '':
                # Only set if completely absent or empty — never overwrite admin's choices
                existing_row = db.session.get(SchoolSetting, key)
                if existing_row is None:
                    SchoolSetting.set(key, value)
                    changed = True
        if changed:
            db.session.commit()
            print('Seeded default school settings.')
        else:
            print('School settings already configured — skipped.')


def main():
    print(f'Migrating database: {DB_PATH}')
    if not os.path.exists(DB_PATH):
        print('Database file not found - nothing to migrate. Run seed.py instead.')
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        migrate_schema(conn)
    finally:
        conn.close()

    app = create_app()
    seed_structure(app)
    seed_school_settings(app)
    print('Migration complete.')


if __name__ == '__main__':
    main()
