import re
from html import escape

ALLOWED_TAGS = {
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li', 'a', 'blockquote',
    'h1', 'h2', 'h3', 'h4', 'hr', 'span', 'div', 'img'
}
ALLOWED_ATTRS = {'href', 'title', 'target', 'rel', 'src', 'alt', 'class'}


def sanitize_newsletter_html(value):
    text = value or ''
    text = re.sub(r'<script.*?</script>', '', text, flags=re.I | re.S)
    text = re.sub(r'<iframe.*?</iframe>', '', text, flags=re.I | re.S)
    text = re.sub(r'on\w+\s*=\s*(["\']).*?\1', '', text, flags=re.I | re.S)
    text = re.sub(r'javascript\s*:', '', text, flags=re.I)
    text = re.sub(r'<\s*(/?)(?:script|iframe|object|embed|style)\b[^>]*>', '', text, flags=re.I)
    text = re.sub(r'href\s*=\s*(?:["\'])?javascript:[^\s"\'>]+', '', text, flags=re.I)
    return text


def newsletter_matches_user(user, audience, target_value=None, current_user_role=None, class_name=None):
    if audience in (None, '', 'all', 'everyone'):
        return True

    if user is None:
        return False

    role = user.get('role') if isinstance(user, dict) else current_user_role

    if audience == 'students' and role == 'student':
        return True
    if audience == 'teachers' and role == 'teacher':
        return True
    if audience == 'parents' and role == 'parent':
        return True

    if audience == 'class':
        target = target_value or class_name
        if not target:
            return False
        student_grade = user.get('student_class_grade') if isinstance(user, dict) else None
        class_name_value = user.get('class_name') if isinstance(user, dict) else None
        return str(student_grade or class_name_value or '').lower() == str(target).lower()

    if audience == 'all_students' and role == 'student':
        return True
    if audience == 'all_teachers' and role == 'teacher':
        return True

    return False
