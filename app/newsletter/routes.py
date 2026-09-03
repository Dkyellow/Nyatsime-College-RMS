from datetime import datetime

from flask import abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app import db
from app.admin import admin_bp
from app.models import Class, Grade, SchoolSetting, Student, Teacher, User
from app.newsletter.models import Newsletter, NewsletterRead
from app.newsletter.utils import newsletter_matches_user, sanitize_newsletter_html
from app.student import student_bp


def admin_required(f):
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def school_logo_url():
    from app.models import SchoolSetting
    logo = SchoolSetting.get('logo_filename', '')
    if logo:
        return url_for('static', filename=f'uploads/{logo}')
    return url_for('static', filename='img/nyatsime-crest.png')


def get_school_brand():
    return {
        'name': SchoolSetting.get('school_name', 'NYATSIME COLLEGE'),
        'motto': SchoolSetting.get('school_motto', 'Knowledge | Integrity | Excellence'),
        'logo': school_logo_url(),
        'address': SchoolSetting.get('school_address', ''),
        'phone': SchoolSetting.get('school_phone', ''),
        'email': SchoolSetting.get('school_email', ''),
        'primary_color': SchoolSetting.get('primary_color', '#1C3480'),
        'accent_color': SchoolSetting.get('accent_color', '#7A1F2B'),
    }


@admin_bp.route('/newsletters')
@admin_required
def newsletters():
    status_filter = request.args.get('status', 'all')
    q = request.args.get('q', '').strip()
    query = Newsletter.query
    if status_filter != 'all':
        query = query.filter(Newsletter.status == status_filter)
    if q:
        query = query.filter(Newsletter.title.ilike(f'%{q}%'))
    items = query.order_by(Newsletter.published_at.desc().nulls_last(), Newsletter.created_at.desc()).all()
    return render_template('newsletters.html', newsletters=items, status_filter=status_filter, q=q)


@admin_bp.route('/newsletters/create', methods=['GET', 'POST'])
@admin_required
def create_newsletter():
    form_classes = Grade.query.order_by(Grade.display_order).all()
    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        subtitle = (request.form.get('subtitle') or '').strip()
        content = request.form.get('content', '')
        cover_image = request.form.get('cover_image', '').strip()
        audience = request.form.get('audience', 'all')
        target_value = request.form.get('target_value', '').strip()
        status = request.form.get('status', 'draft')
        scheduled_raw = request.form.get('scheduled_at', '').strip()
        scheduled_at = datetime.strptime(scheduled_raw, '%Y-%m-%dT%H:%M') if scheduled_raw else None

        if not title or not content:
            flash('Title and content are required.', 'danger')
            return render_template('newsletter_editor.html', form_classes=form_classes, edit=False)

        newsletter = Newsletter(
            title=title,
            subtitle=subtitle,
            content=sanitize_newsletter_html(content),
            cover_image=cover_image,
            audience=audience,
            target_value=target_value,
            status=status,
            scheduled_at=scheduled_at,
            created_by=current_user.id,
            published_at=datetime.utcnow() if status == 'published' else None,
        )
        db.session.add(newsletter)
        db.session.commit()
        flash('Newsletter saved successfully.', 'success')
        return redirect(url_for('admin.newsletters'))

    return render_template('newsletter_editor.html', form_classes=form_classes, edit=False, newsletter=None)


@admin_bp.route('/newsletters/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_newsletter(id):
    newsletter = db.session.get(Newsletter, id)
    if not newsletter:
        abort(404)
    form_classes = Grade.query.order_by(Grade.display_order).all()
    if request.method == 'POST':
        newsletter.title = (request.form.get('title') or '').strip()
        newsletter.subtitle = (request.form.get('subtitle') or '').strip()
        newsletter.content = sanitize_newsletter_html(request.form.get('content', ''))
        newsletter.cover_image = (request.form.get('cover_image') or '').strip()
        newsletter.audience = request.form.get('audience', newsletter.audience or 'all')
        newsletter.target_value = (request.form.get('target_value') or '').strip()
        status = request.form.get('status', newsletter.status)
        if status == 'published' and newsletter.status != 'published':
            newsletter.published_at = datetime.utcnow()
        elif status != 'published':
            newsletter.published_at = None if newsletter.status == 'draft' else newsletter.published_at
        newsletter.status = status
        scheduled_raw = request.form.get('scheduled_at', '').strip()
        newsletter.scheduled_at = datetime.strptime(scheduled_raw, '%Y-%m-%dT%H:%M') if scheduled_raw else None
        db.session.commit()
        flash('Newsletter updated.', 'success')
        return redirect(url_for('admin.newsletters'))
    return render_template('newsletter_editor.html', form_classes=form_classes, edit=True, newsletter=newsletter)


@admin_bp.route('/newsletters/<int:id>/preview')
@admin_required
def preview_newsletter(id):
    newsletter = db.session.get(Newsletter, id)
    if not newsletter:
        abort(404)
    return render_template('newsletter_view.html', newsletter=newsletter, brand=get_school_brand(), preview=True)


@admin_bp.route('/newsletters/<int:id>/duplicate', methods=['POST'])
@admin_required
def duplicate_newsletter(id):
    source = db.session.get(Newsletter, id)
    if not source:
        abort(404)
    clone = Newsletter(
        title=f'{source.title} (Copy)',
        subtitle=source.subtitle,
        content=source.content,
        cover_image=source.cover_image,
        audience=source.audience,
        target_value=source.target_value,
        status='draft',
        created_by=current_user.id,
        published_at=None,
        scheduled_at=None,
    )
    db.session.add(clone)
    db.session.commit()
    flash('Newsletter duplicated as a draft.', 'success')
    return redirect(url_for('admin.newsletters'))


@admin_bp.route('/newsletters/<int:id>/archive', methods=['POST'])
@admin_required
def archive_newsletter(id):
    newsletter = db.session.get(Newsletter, id)
    if not newsletter:
        abort(404)
    newsletter.status = 'archived'
    newsletter.archived_at = datetime.utcnow()
    db.session.commit()
    flash('Newsletter archived.', 'success')
    return redirect(url_for('admin.newsletters'))


@admin_bp.route('/newsletters/<int:id>/delete', methods=['POST'])
@admin_required
def delete_newsletter(id):
    newsletter = db.session.get(Newsletter, id)
    if not newsletter:
        abort(404)
    db.session.delete(newsletter)
    db.session.commit()
    flash('Newsletter deleted.', 'success')
    return redirect(url_for('admin.newsletters'))


@admin_bp.route('/newsletters/<int:id>/publish', methods=['POST'])
@admin_required
def publish_newsletter(id):
    newsletter = db.session.get(Newsletter, id)
    if not newsletter:
        abort(404)
    newsletter.status = 'published'
    newsletter.published_at = datetime.utcnow()
    newsletter.scheduled_at = None
    db.session.commit()
    flash('Newsletter published.', 'success')
    return redirect(url_for('admin.newsletters'))


@student_bp.route('/newsletters')
@login_required
def student_newsletters():
    student = Student.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not student:
        flash('No student record linked to your account.', 'warning')
        return redirect(url_for('student.dashboard'))

    items = Newsletter.query.filter(Newsletter.status == 'published').order_by(Newsletter.published_at.desc()).all()
    readable = []
    for item in items:
        if newsletter_matches_user({
            'role': 'student',
            'student_class_grade': getattr(student.class_obj.grade, 'name', None) if student.class_obj and student.class_obj.grade else None,
            'class_name': student.class_obj.name if student.class_obj else None,
        }, item.audience, item.target_value, 'student', student.class_obj.name if student.class_obj else None):
            readable.append(item)
    return render_template('student/newsletters.html', newsletters=readable, student=student)


@student_bp.route('/newsletters/<int:id>')
@login_required
def student_view_newsletter(id):
    student = Student.query.filter_by(user_id=current_user.id, is_active=True).first()
    if not student:
        return redirect(url_for('student.dashboard'))
    newsletter = Newsletter.query.filter_by(id=id, status='published').first_or_404()
    if not newsletter_matches_user({
        'role': 'student',
        'student_class_grade': getattr(student.class_obj.grade, 'name', None) if student.class_obj and student.class_obj.grade else None,
        'class_name': student.class_obj.name if student.class_obj else None,
    }, newsletter.audience, newsletter.target_value, 'student', student.class_obj.name if student.class_obj else None):
        abort(403)
    if not NewsletterRead.query.filter_by(newsletter_id=newsletter.id, user_id=current_user.id).first():
        db.session.add(NewsletterRead(newsletter_id=newsletter.id, user_id=current_user.id))
        db.session.commit()
    return render_template('newsletter_view.html', newsletter=newsletter, brand=get_school_brand(), preview=False)


@admin_bp.route('/newsletters/<int:id>')
@admin_required
def admin_view_newsletter(id):
    newsletter = db.session.get(Newsletter, id)
    if not newsletter:
        abort(404)
    return render_template('newsletter_view.html', newsletter=newsletter, brand=get_school_brand(), preview=False)


@admin_bp.route('/newsletters/<int:id>/readers')
@admin_required
def newsletter_analytics(id):
    newsletter = db.session.get(Newsletter, id)
    if not newsletter:
        abort(404)
    audience_total = User.query.count()
    read_count = NewsletterRead.query.filter_by(newsletter_id=id).count()
    return render_template('newsletter_analytics.html', newsletter=newsletter, audience_total=audience_total, read_count=read_count, read_rate=(read_count / audience_total * 100) if audience_total else 0)
