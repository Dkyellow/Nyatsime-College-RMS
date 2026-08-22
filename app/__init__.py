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
    from app.parent import parent_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(parent_bp, url_prefix='/parent')

    @app.context_processor
    def inject_globals():
        from app.models import User, SchoolSetting

        def setting(key, default=''):
            try:
                return SchoolSetting.get(key, default)
            except Exception:
                return default

        return dict(
            User=User,
            SCHOOL_NAME=setting('school_name', 'NYATSIME COLLEGE'),
            SCHOOL_MOTTO=setting('school_motto', 'Knowledge | Integrity | Excellence'),
            SCHOOL_ADDRESS=setting('school_address', 'P.O. Box Nyatsime, Zimbabwe'),
            SCHOOL_PHONE=setting('school_phone', ''),
            SCHOOL_EMAIL=setting('school_email', ''),
            CURRENT_YEAR=datetime.now().year,
        )

    return app
