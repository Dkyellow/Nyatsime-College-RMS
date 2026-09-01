import os
from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.teacher import teacher_bp
    from app.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(student_bp, url_prefix='/student')

    @app.context_processor
    def inject_globals():
        from app.models import User, SchoolSetting

        def setting(key, default=''):
            try:
                return SchoolSetting.get(key, default)
            except Exception:
                return default

        # ── Core school information ──────────────────────────────────────────
        school_name    = setting('school_name',    'HILLSIDE ACADEMY')
        school_motto   = setting('school_motto',   'Knowledge | Integrity | Excellence')
        school_address = setting('school_address', 'P.O. Box Hillside, Zimbabwe')
        school_phone   = setting('school_phone',   '')
        school_email   = setting('school_email',   '')
        school_short_name = setting('school_short_name', '')
        school_website = setting('school_website', '')
        school_city    = setting('school_city',    '')
        school_country = setting('school_country', '')
        report_footer  = setting('report_footer',  '')

        # ── Brand colours ────────────────────────────────────────────────────
        primary_color = setting('primary_color', '#1C3480')
        accent_color  = setting('accent_color',  '#7A1F2B')

        # Derive a darker shade of primary for hover states (simple offset)
        def _hex_darken(hex_color, factor=0.85):
            """Return a slightly darkened version of a hex colour string."""
            try:
                h = hex_color.lstrip('#')
                r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                r = max(0, int(r * factor))
                g = max(0, int(g * factor))
                b = max(0, int(b * factor))
                return f'#{r:02x}{g:02x}{b:02x}'
            except Exception:
                return hex_color

        def _hex_to_soft(hex_color, alpha=0.12):
            """Return a very light tint of a hex colour as rgba()."""
            try:
                h = hex_color.lstrip('#')
                r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                return f'rgba({r},{g},{b},{alpha})'
            except Exception:
                return 'rgba(3,112,177,0.12)'

        primary_dark  = _hex_darken(primary_color, 0.82)
        primary_soft  = _hex_to_soft(primary_color, 0.12)
        accent_soft   = _hex_to_soft(accent_color,  0.15)

        # Inline CSS that overrides the generic --brand-* design tokens
        # with this school's chosen colours.  Injected into <head> by base.html.
        brand_css = f"""<style>
:root {{
  --brand-primary:      {primary_color};
  --brand-primary-dark: {primary_dark};
  --brand-primary-soft: {primary_soft};
  --brand-accent:       {accent_color};
  --brand-accent-soft:  {accent_soft};
  --brand-dark:         #0E1B3A;
}}
</style>"""

        # ── School logo ──────────────────────────────────────────────────────
        logo_filename = setting('logo_filename', '')
        if logo_filename:
            school_logo_url = f'/static/uploads/{logo_filename}'
        else:
            school_logo_url = '/static/img/hillside-academy-crest.png'

        return dict(
            User=User,
            SCHOOL_NAME=school_name,
            SCHOOL_MOTTO=school_motto,
            SCHOOL_ADDRESS=school_address,
            SCHOOL_PHONE=school_phone,
            SCHOOL_EMAIL=school_email,
            SCHOOL_SHORT_NAME=school_short_name,
            SCHOOL_WEBSITE=school_website,
            SCHOOL_CITY=school_city,
            SCHOOL_COUNTRY=school_country,
            REPORT_FOOTER=report_footer,
            PRIMARY_COLOR=primary_color,
            ACCENT_COLOR=accent_color,
            SCHOOL_LOGO_URL=school_logo_url,
            BRAND_CSS=brand_css,
            CURRENT_YEAR=datetime.now().year,
        )

    return app
