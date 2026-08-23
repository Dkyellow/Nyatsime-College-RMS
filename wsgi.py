import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db

app = create_app()

with app.app_context():
    db.create_all()

    from app.models import User
    if not User.query.first():
        from seed import seed_database
        seed_database()
