"""Nyatsime College academic configuration and helpers.

The school's academic structure is FIXED in code (secondary school only):
  - Forms: Form 1, Form 2, Form 3, Form 4, Lower 6, Upper 6
  - Terms: Term 1, Term 2, Term 3 with editable start/end dates per year
  - Academic years: a single calendar year, e.g. "2026" (never "2026/2027")
  - Grading: predefined scale, applied automatically - never configured in the UI
"""
import re
from datetime import date, datetime

# ---------------------------------------------------------------- forms ----

FIXED_FORMS = [
    ('Form 1', 1),
    ('Form 2', 2),
    ('Form 3', 3),
    ('Form 4', 4),
    ('Lower 6', 5),
    ('Upper 6', 6),
]

FORM_NAMES = [name for name, _ in FIXED_FORMS]

LEVEL_GROUP_LABELS = {
    'Form 1': 'Junior Secondary',
    'Form 2': 'Junior Secondary',
    'Form 3': 'O-Level',
    'Form 4': 'O-Level',
    'Lower 6': 'A-Level',
    'Upper 6': 'A-Level',
}


def level_group(form_name):
    return LEVEL_GROUP_LABELS.get((form_name or '').strip(), 'Secondary')


# --------------------------------------------------------------- grading ----

GRADE_SCALE = [
    # (band name, min %, max % inclusive, letter, description, display order)
    ('Distinction 1', 80, 100, 'A', 'Very good', 1),
    ('Distinction 2', 70, 79.99, 'B', 'Good', 2),
    ('Credit 1',      60, 69.99, 'C', 'Fairly good', 3),
    ('Credit 2',      50, 59.99, 'D', 'Satisfactory', 4),
    ('Pass',          40, 49.99, 'E', 'Pass', 5),
    ('Fail',           0, 39.99, 'U', 'Unsatisfactory', 6),
]


def calculate_grade(percent):
    """Return the grade letter for a percentage. Marks are graded automatically."""
    if percent is None:
        return None
    try:
        percent = float(percent)
    except (TypeError, ValueError):
        return None
    for _, mn, mx, letter, _, _ in GRADE_SCALE:
        if mn <= percent <= mx:
            return letter
    return 'U'


def grade_scale_public():
    return [{'name': n, 'min_score': mn, 'max_score': mx,
             'grade_letter': l, 'description': d}
            for n, mn, mx, l, d, _ in GRADE_SCALE]


# ----------------------------------------------------------------- terms ----

TERM_NAMES = ['Term 1', 'Term 2', 'Term 3']

# Default calendar used when a new year is prepared (start month, end month)
DEFAULT_TERM_RANGES = {
    'Term 1': (1, 3),    # January to March/April
    'Term 2': (5, 7),    # May to July/August
    'Term 3': (9, 11),   # September to November/December
}


def normalize_year(value, fallback=None):
    """Normalize any legacy year value ("2026/2027", "2026") to a single year string."""
    if value is None:
        return str(fallback) if fallback else None
    text = str(value).strip()
    match = re.match(r'(\d{4})', text)
    if match:
        return match.group(1)
    if fallback:
        return str(fallback)
    return None


def default_term_dates(year):
    """Default start/end dates for the three terms of a given year."""
    year = int(normalize_year(year) or datetime.now().year)
    ranges = {}
    for term, (m_start, m_end) in DEFAULT_TERM_RANGES.items():
        last_day_start = _days_in_month(year, m_start)
        last_day_end = _days_in_month(year, m_end)
        ranges[term] = (
            date(year, m_start, min(1 + ((last_day_start - 1) // 2), last_day_start)),
            date(year, m_end, last_day_end),
        )
    return ranges


def _days_in_month(year, month):
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - date(year, month, 1)).days


# ------------------------------------------------------------- usernames ----

def slugify_name(value):
    """Lowercase letters only; drop spaces/special characters."""
    cleaned = re.sub(r"[^a-z]", '', (value or '').lower())
    return cleaned


def generate_username(first_name, last_name, exists_fn):
    """firstname + surname joined lowercase, e.g. 'tariromoyo'.

    If taken, appends a number: tariromoyo2, tariromoyo3 ...
    `exists_fn(username)` must return True when the username is already used.
    """
    base = f"{slugify_name(first_name)}{slugify_name(last_name)}"
    if not base:
        base = 'student'
    candidate = base
    counter = 1
    while exists_fn(candidate):
        counter += 1
        candidate = f"{base}{counter}"
    return candidate


# ------------------------------------------------------------ period ctx ----

def current_period_label(term, year_name, on_break=False):
    if on_break or term is None:
        return 'School Holiday / Between Terms'
    return f'{term.name}, {year_name}'
