"""Migrate the school reports database to a secondary-school-only Nyatsime College system.

- Removes ECD and Primary School data (education levels, ECD assessment tables/columns,
  grades, classes, students, reports belonging to those levels).
- Removes obsolete education_level_id columns.
- Ensures the Zimbabwean secondary school structure exists:
  Form 1, Form 2 (Junior Secondary), Form 3, Form 4 (O-Level), Lower 6, Upper 6 (A-Level).
- Seeds default subjects, grading scale, report template and academic year/terms.

Run:  python migrate_database.py
"""
import os
import sqlite3

from app import create_app, db
from app.models import (
    Grade, GradeSubject, Subject, GradingScale, AcademicYear,
    AcademicTerm, ReportTemplate, SchoolSetting,
)

BASEDIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.environ.get('DATABASE_URL') or os.path.join(BASEDIR, 'school_reports.db')
if DB_PATH.startswith('sqlite:///'):
    DB_PATH = DB_PATH.replace('sqlite:///', '')
if not os.path.isabs(DB_PATH):
    DB_PATH = os.path.join(BASEDIR, DB_PATH)

SECONDARY_FORMS = [
    ('Form 1', 1), ('Form 2', 2), ('Form 3', 3),
    ('Form 4', 4), ('Lower 6', 5), ('Upper 6', 6),
]

DEFAULT_SUBJECTS = [
    ('English Language', 'ENG', 100), ('Mathematics', 'MATH', 100),
    ('Combined Science', 'SCI', 100), ('Biology', 'BIO', 100),
    ('Chemistry', 'CHEM', 100), ('Physics', 'PHY', 100),
    ('Geography', 'GEO', 100), ('History', 'HIST', 100),
    ('Shona', 'SHONA', 100), ('Ndebele', 'NDEBELE', 100),
    ('Principles of Accounts', 'POA', 100), ('Commerce', 'COMM', 100),
    ('Computer Science', 'CS', 100), ('Literature in English', 'LIT', 100),
    ('Heritage Studies', 'HER', 100), ('Physical Education', 'PE', 100),
]

# O-Level / A-Level style grade bands
DEFAULT_GRADING_SCALE = [
    ('Distinction 1', 80, 100, 'A', 'Very Good', 1),
    ('Distinction 2', 70, 79.99, 'B', 'Good', 2),
    ('Credit 1', 60, 69.99, 'C', 'Fairly Good', 3),
    ('Credit 2', 50, 59.99, 'D', 'Satisfactory', 4),
    ('Pass', 40, 49.99, 'E', 'Pass', 5),
    ('Fail', 0, 39.99, 'U', 'Unsatisfactory', 6),
]


def table_exists(cur, name):
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def column_exists(cur, table, column):
    return any(col[1] == column for col in cur.execute(f'PRAGMA table_info({table})').fetchall())


def migrate_schema(conn):
    cur = conn.cursor()
    print('Removing ECD / Primary structures...')

    # Drop ECD assessment tables entirely
    for t in ('ecd_assessment_marks', 'ecd_assessment_fields'):
        if table_exists(cur, t):
            cur.execute(f'DROP TABLE {t}')
            print(f'  dropped table {t}')

    # Drop education_levels after collecting ids to purge
    level_ids = []
    if table_exists(cur, 'education_levels'):
        rows = cur.execute('SELECT id, name FROM education_levels').fetchall()
        level_ids = [r[0] for r in rows if (r[1] or '').lower() != 'secondary']
        cur.execute('DROP TABLE education_levels')
        print('  dropped table education_levels')

    # Delete grades (and dependent data) that belonged to non-secondary levels
    if level_ids:
        placeholders = ','.join('?' * len(level_ids))
        grade_rows = cur.execute(
            f'SELECT id FROM grades WHERE education_level_id IN ({placeholders})',
            level_ids).fetchall()
        gids = [g[0] for g in grade_rows]
        if gids:
            ph = ','.join('?' * len(gids))
            class_ids = []
            if table_exists(cur, 'classes'):
                class_ids = [r[0] for r in cur.execute(
                    f'SELECT id FROM classes WHERE grade_id IN ({ph})', gids).fetchall()]
            if class_ids:
                cph = ','.join('?' * len(class_ids))
                if table_exists(cur, 'reports'):
                    report_ids = [r[0] for r in cur.execute(
                        f'SELECT id FROM reports WHERE class_id IN ({cph})', class_ids).fetchall()]
                    if report_ids:
                        rph = ','.join('?' * len(report_ids))
                        cur.execute(f'DELETE FROM marks WHERE report_id IN ({rph})', report_ids)
                        cur.execute(f'DELETE FROM reports WHERE id IN ({rph})', report_ids)
                cur.execute(f'DELETE FROM students WHERE class_id IN ({cph})', class_ids)
                if table_exists(cur, 'class_teachers'):
                    cur.execute(f'DELETE FROM class_teachers WHERE class_id IN ({cph})', class_ids)
                cur.execute(f'DELETE FROM classes WHERE id IN ({cph})', class_ids)
            if table_exists(cur, 'grade_subjects'):
                cur.execute(f'DELETE FROM grade_subjects WHERE grade_id IN ({ph})', gids)
            cur.execute(f'DELETE FROM grades WHERE id IN ({ph})', gids)
            print(f'  removed {len(gids)} non-secondary grade(s) with their classes/students/reports')

    # Remove now-obsolete columns. SQLite cannot drop a column when it appears
    # in the table's own FK definition, so affected tables are rebuilt from
    # their original CREATE statement (preserving keys, constraints, defaults).
    for table in ['grades', 'grading_scales', 'report_templates', 'students', 'reports']:
        if not (table_exists(cur, table) and column_exists(cur, table, 'education_level_id')):
            continue

        sql = cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()[0]

        try:
            cur.execute(f'ALTER TABLE {table} DROP COLUMN education_level_id')
            print(f'  dropped column {table}.education_level_id')
            continue
        except sqlite3.OperationalError:
            pass

        # Rebuild from original schema minus the obsolete column definition
        import re
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

    # Clean grading scales / templates that referenced old levels
    if table_exists(cur, 'grading_scales'):
        cur.execute('DELETE FROM grading_scales')
    if table_exists(cur, 'report_templates'):
        cur.execute("DELETE FROM report_templates WHERE template_type IN ('ecd', 'primary')")
    conn.commit()


def seed_secondary_structure(app):
    with app.app_context():
        db.create_all()

        # Forms
        existing = {g.name for g in Grade.query.all()}
        for name, order in SECONDARY_FORMS:
            if name not in existing:
                db.session.add(Grade(name=name, display_order=order))
        db.session.flush()
        print('Secondary forms ensured:', ', '.join(g.name for g in Grade.query.order_by(Grade.display_order)))

        # Subjects
        if Subject.query.count() == 0:
            for name, code, mx in DEFAULT_SUBJECTS:
                db.session.add(Subject(name=name, code=code, max_score=mx))
            print('Default secondary subjects seeded.')

        # Assign core subjects to every form if none assigned yet
        if GradeSubject.query.count() == 0:
            core_codes = ['ENG', 'MATH', 'SCI', 'GEO', 'HIST', 'SHONA', 'HER', 'PE', 'CS', 'POA', 'COMM', 'BIO', 'CHEM', 'PHY', 'LIT', 'NDEBELE']
            core = {s.code: s for s in Subject.query.filter(Subject.code.in_(core_codes))}
            for grade in Grade.query.all():
                for code, subj in core.items():
                    db.session.add(GradeSubject(grade_id=grade.id, subject_id=subj.id))
            print('Subjects assigned to all forms.')

        # Grading scale (single, school-wide)
        if GradingScale.query.count() == 0:
            for name, mn, mx, letter, desc, order in DEFAULT_GRADING_SCALE:
                db.session.add(GradingScale(
                    name=name, min_score=mn, max_score=mx, grade_letter=letter,
                    description=desc, display_order=order))
            print('Grading scale seeded.')

        # Default report template
        if ReportTemplate.query.count() == 0:
            db.session.add(ReportTemplate(
                name='Nyatsime College Secondary Report Card',
                template_type='secondary',
                description='Official academic report card for all forms',
                is_default=True))
            print('Report template seeded.')

        # Current academic year + terms
        if AcademicYear.query.count() == 0:
            year = AcademicYear(name='2026', is_current=True)
            db.session.add(year)
            db.session.flush()
            for i, term in enumerate(['Term 1', 'Term 2', 'Term 3'], start=1):
                db.session.add(AcademicTerm(academic_year_id=year.id, name=term, display_order=i))
            print('Academic year 2026 with Terms 1-3 seeded.')

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

        db.session.commit()


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
    seed_secondary_structure(app)
    print('Migration complete.')


if __name__ == '__main__':
    main()
