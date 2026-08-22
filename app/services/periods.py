"""Academic period helpers backed by the database.

Current term is determined automatically from today's date and the configured
term date ranges. Terms are fixed (Term 1/2/3) - only their dates are editable.
"""
from datetime import date, datetime

from app import db
from app.models import AcademicYear, AcademicTerm, SchoolSetting
from app.academic import (
    TERM_NAMES, DEFAULT_TERM_RANGES, default_term_dates, normalize_year,
)


def ensure_year(name):
    """Return the AcademicYear for `name`, creating it (with the three fixed,
    default-dated terms) when it does not exist yet."""
    name = normalize_year(name) or str(datetime.now().year)
    year = AcademicYear.query.filter_by(name=name).first()
    if not year:
        year = AcademicYear(name=name)
        db.session.add(year)
        db.session.flush()
        defaults = default_term_dates(name)
        for order, term_name in enumerate(TERM_NAMES, start=1):
            start_d, end_d = defaults[term_name]
            db.session.add(AcademicTerm(
                academic_year_id=year.id, name=term_name,
                display_order=order, start_date=start_d, end_date=end_d))
        db.session.flush()
    else:
        # Guarantee the three fixed terms exist with sane ordering
        existing = {t.name: t for t in year.terms}
        defaults = default_term_dates(name)
        created = False
        for order, term_name in enumerate(TERM_NAMES, start=1):
            term = existing.get(term_name)
            if not term:
                start_d, end_d = defaults[term_name]
                db.session.add(AcademicTerm(
                    academic_year_id=year.id, name=term_name,
                    display_order=order, start_date=start_d, end_date=end_d))
                created = True
            elif term.start_date is None or term.end_date is None:
                start_d, end_d = defaults[term_name]
                term.start_date = term.start_date or start_d
                term.end_date = term.end_date or end_d
                created = True
        if created:
            db.session.flush()
    return year


def ensure_fixed_grades(grade_model):
    """Make sure the six fixed form rows exist (reference data)."""
    from app.academic import FIXED_FORMS
    changed = False
    existing = {g.name: g for g in grade_model.query.all()}
    for name, order in FIXED_FORMS:
        if name not in existing:
            db.session.add(grade_model(name=name, display_order=order))
            changed = True
    if changed:
        db.session.commit()


def get_current_year():
    """The academic year matching today's calendar year (auto-created)."""
    today = date.today()
    return ensure_year(str(today.year))


def get_current_term(year=None):
    """Return the AcademicTerm whose date range contains today, or None.

    Never guesses: outside all ranges (holidays) returns None.
    """
    today = date.today()
    year = year or get_current_year()
    for term in year.terms:
        if term.start_date and term.end_date and term.start_date <= today <= term.end_date:
            return term
    return None


def is_on_break(year=None):
    return get_current_term(year) is None


def get_default_period():
    """Default (term_name, year_name) for entering/viewing results.

    Inside a term  -> that term.
    On break       -> the most recently ended term of the current year
                      (falls back to the last ordered term).
    """
    year = get_current_year()
    term = get_current_term(year)
    if term:
        return term.name, year.name

    today = date.today()
    dated = [t for t in year.terms if t.end_date]
    past = [t for t in dated if t.end_date < today]
    chosen = max(past, key=lambda t: t.end_date) if past else \
        (min([t for t in year.terms], key=lambda t: t.display_order) if year.terms else None)
    return (chosen.name if chosen else 'Term 1'), year.name


def available_years():
    years = AcademicYear.query.order_by(AcademicYear.name.desc()).all()
    names = [y.name for y in years]
    current = str(date.today().year)
    if current not in names:
        names.insert(0, current)
    return names


def prepare_next_years():
    """Ensure current calendar year exists as an academic year."""
    get_current_year()
    db.session.commit()
