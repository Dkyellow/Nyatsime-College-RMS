from datetime import datetime

from app import db


class Newsletter(db.Model):
    __tablename__ = 'newsletters'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(300))
    content = db.Column(db.Text, nullable=False)
    cover_image = db.Column(db.String(255))
    status = db.Column(db.String(20), default='draft', nullable=False)
    audience = db.Column(db.String(40), default='all')
    target_value = db.Column(db.String(100))
    published_at = db.Column(db.DateTime)
    scheduled_at = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = db.Column(db.DateTime)

    creator = db.relationship('User', backref=db.backref('newsletters', lazy='dynamic'))


class NewsletterRead(db.Model):
    __tablename__ = 'newsletter_reads'
    id = db.Column(db.Integer, primary_key=True)
    newsletter_id = db.Column(db.Integer, db.ForeignKey('newsletters.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)

    newsletter = db.relationship('Newsletter', backref=db.backref('reads', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('newsletter_reads', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('newsletter_id', 'user_id', name='uq_newsletter_read_user'),
    )
