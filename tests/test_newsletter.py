import unittest

from app.newsletter.utils import sanitize_newsletter_html, newsletter_matches_user


class NewsletterTargetingTests(unittest.TestCase):
    def test_sanitize_newsletter_html_removes_script_and_keeps_allowed_tags(self):
        dirty = '<p>Hello</p><script>alert(1)</script><a href="javascript:alert(1)" onclick="evil()">link</a><img src="x" onerror="evil()">'
        cleaned = sanitize_newsletter_html(dirty)
        self.assertIn('<p>Hello</p>', cleaned)
        self.assertNotIn('<script', cleaned.lower())
        self.assertNotIn('javascript:', cleaned.lower())
        self.assertNotIn('onerror=', cleaned.lower())

    def test_newsletter_matches_user_for_students_and_forms(self):
        # Everyone
        self.assertTrue(newsletter_matches_user(None, 'all', None, None, None))

        # Students
        self.assertTrue(newsletter_matches_user({'role': 'student'}, 'students', None, None, None))
        self.assertFalse(newsletter_matches_user({'role': 'teacher'}, 'students', None, None, None))

        # Form-specific audience
        self.assertTrue(newsletter_matches_user({'role': 'student', 'student_class_grade': 'Form 4'}, 'class', 'Form 4', None, None))
        self.assertFalse(newsletter_matches_user({'role': 'student', 'student_class_grade': 'Form 3'}, 'class', 'Form 4', None, None))


if __name__ == '__main__':
    unittest.main()
