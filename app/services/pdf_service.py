import os
import hashlib
from io import BytesIO
from xhtml2pdf import pisa
from flask import render_template_string, current_app
from datetime import datetime


REPORT_CARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page { size: A4; margin: 12mm 14mm; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #1F2937; }
        .header { text-align: center; margin-bottom: 4px; }
        .crest { width: 64px; height: 70px; }
        .school-name { font-size: 20pt; font-weight: bold; color: #0370b1; letter-spacing: 2px; margin-top: 4px; }
        .school-tag { font-size: 8pt; color: #6B7280; letter-spacing: 3px; text-transform: uppercase; }
        .motto { font-style: italic; color: #374151; font-size: 9pt; margin-top: 2px; }
        .report-title { background: #0370b1; color: #F7C948; text-align: center; font-size: 11pt;
                        font-weight: bold; padding: 5px 0; margin: 12px -2mm 0 -2mm; letter-spacing: 2px; }
        .student-info { width: 100%; border-collapse: collapse; margin-top: 12px; }
        .student-info td { padding: 4px 6px; font-size: 9.5pt; border-bottom: 1px solid #E5EAF1; }
        .label { font-weight: bold; color: #0370b1; width: 16%; }
        .section-title { font-size: 10.5pt; font-weight: bold; margin: 14px 0 6px 0; color: #0370b1;
                         border-bottom: 2px solid #F7C948; padding-bottom: 3px; }
        .marks-table { width: 100%; border-collapse: collapse; margin-bottom: 4px; }
        .marks-table th { background: #0370b1; color: white; padding: 7px 8px; text-align: left; font-size: 9pt; }
        .marks-table th.num { text-align: center; }
        .marks-table td { padding: 6px 8px; border-bottom: 1px solid #E5EAF1; font-size: 9pt; }
        .marks-table td.num { text-align: center; }
        .marks-table tr:nth-child(even) { background: #F6F8FB; }
        .grade-badge { color: #0370b1; font-weight: bold; padding: 1px 8px; border: 1.5px solid #F7C948;
                       background: #FEF7E0; border-radius: 4px; font-size: 8pt; }
        .summary-table { width: 100%; border-collapse: separate; border-spacing: 6px 0; margin: 10px 0 4px 0; }
        .summary-table td { width: 25%; text-align: center; padding: 9px 4px; background: #F6F8FB;
                            border: 1px solid #E5EAF1; border-top: 3px solid #F7C948; border-radius: 4px; }
        .summary-table .value { font-size: 15pt; font-weight: bold; color: #0370b1; }
        .summary-table .lbl { font-size: 7.5pt; color: #6B7280; text-transform: uppercase; letter-spacing: 1px; }
        .comments { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
        .comments td { vertical-align: top; width: 50%; padding-right: 8px; }
        .comment-box { border: 1px solid #E5EAF1; border-radius: 4px; padding: 8px 10px; min-height: 52px; }
        .comment-box .title { font-weight: bold; color: #0370b1; font-size: 8.5pt; margin-bottom: 3px;
                              text-transform: uppercase; letter-spacing: 0.5px; }
        .comment-box .text { font-size: 9pt; color: #374151; }
        .signature-section { width: 100%; margin-top: 22px; }
        .signature-section td { width: 33%; text-align: center; padding: 0 8px; }
        .signature-line { border-top: 1px solid #374151; margin-top: 34px; padding-top: 4px; font-size: 8pt; color: #4B5563; }
        .footer { text-align: center; font-size: 7.5pt; color: #9CA3AF; margin-top: 14px;
                  border-top: 1px solid #E5EAF1; padding-top: 6px; }
    </style>
</head>
<body>
    <div class="header">
        <img class="crest" src="{{ crest_path }}" />
        <div class="school-name">{{ school_name }}</div>
        <div class="school-tag">Academic Report Card</div>
        {% if school_motto %}<div class="motto">{{ school_motto }}</div>{% endif %}
    </div>

    <div class="report-title">TERM REPORT &mdash; {{ report.academic_term }} &nbsp;&bull;&nbsp; {{ report.academic_year }}</div>

    <table class="student-info">
        <tr>
            <td class="label">Student Name</td><td><b>{{ student.first_name }} {{ student.last_name }}</b></td>
            <td class="label">Student ID</td><td>{{ student.admission_number }}</td>
        </tr>
        <tr>
            <td class="label">Form / Class</td><td>{{ form_name }} &mdash; {{ class_name }}</td>
            <td class="label">Gender</td><td>{{ student.gender or 'N/A' }}</td>
        </tr>
        <tr>
            <td class="label">Date of Birth</td><td>{{ student_dob }}</td>
            <td class="label">Date Issued</td><td>{{ generated_date }}</td>
        </tr>
    </table>

    <div class="section-title">Subject Results</div>
    <table class="marks-table">
        <thead>
            <tr>
                <th width="36" class="num">#</th>
                <th>Subject</th>
                <th width="80" class="num">Mark</th>
                <th width="80" class="num">Percentage</th>
                <th width="80" class="num">Grade</th>
            </tr>
        </thead>
        <tbody>
            {% for m in marks %}
            <tr>
                <td class="num">{{ loop.index }}</td>
                <td>{{ m.subject.name }}</td>
                <td class="num">{{ "%.1f"|format(m.score) }} / {{ m.max_score }}</td>
                <td class="num">{{ "%.1f"|format(m.percent) }}%</td>
                <td class="num"><span class="grade-badge">{{ m.grade or '-' }}</span></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <table class="summary-table">
        <tr>
            <td>
                <div class="value">{{ "%.1f"|format(report.total_marks) }}</div>
                <div class="lbl">Total Marks</div>
            </td>
            <td>
                <div class="value">{{ "%.1f"|format(report.average) }}%</div>
                <div class="lbl">Average</div>
            </td>
            <td>
                <div class="value">{{ report.overall_grade or '-' }}</div>
                <div class="lbl">Overall Grade</div>
            </td>
            <td>
                <div class="value">{% if report.position %}{{ report.position }}{% if class_size %} of {{ class_size }}{% endif %}{% else %}-{% endif %}</div>
                <div class="lbl">Class Position</div>
            </td>
        </tr>
    </table>

    <div class="section-title">Remarks</div>
    <table class="comments">
        <tr>
            <td>
                <div class="comment-box">
                    <div class="title">Class Teacher's Remark</div>
                    <div class="text">{{ report.teacher_comment or 'No comment provided.' }}</div>
                </div>
            </td>
            <td>
                <div class="comment-box">
                    <div class="title">Head's Remark</div>
                    <div class="text">{{ report.admin_comment or 'No comment provided.' }}</div>
                </div>
            </td>
        </tr>
    </table>

    <table class="signature-section">
        <tr>
            <td><div class="signature-line">Class Teacher's Signature</div></td>
            <td><div class="signature-line">Head's Signature</div></td>
            <td><div class="signature-line">Parent/Guardian's Signature</div></td>
        </tr>
    </table>

    <div class="footer">
        {{ school_name }}{% if school_address %} &bull; {{ school_address }}{% endif %}{% if school_phone %} &bull; Tel: {{ school_phone }}{% endif %}{% if school_email %} &bull; {{ school_email }}{% endif %}
        <br/>This is an official academic document generated by the Nyatsime College Academic Records System.
    </div>
</body>
</html>
"""


def _get_cache_dir():
    cache_dir = current_app.config.get('REPORT_CACHE_DIR', 'cached_reports')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _get_cache_key(report_id, updated_at):
    raw = f"report_{report_id}_{updated_at}"
    return hashlib.md5(raw.encode()).hexdigest()


def _get_cache_path(report_id, updated_at):
    cache_dir = _get_cache_dir()
    key = _get_cache_key(report_id, updated_at)
    return os.path.join(cache_dir, f"report_{report_id}_{key}.pdf")


def generate_report_card_pdf(report):
    cache_path = _get_cache_path(report.id, report.updated_at)

    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            return f.read()

    student = report.student
    class_obj = report.class_obj

    marks = []
    for m in report.marks:
        max_score = m.max_score or 100
        percent = (m.score / max_score) * 100 if max_score else 0
        marks.append({
            'subject': m.subject,
            'score': m.score or 0,
            'max_score': max_score,
            'percent': percent,
            'grade': m.grade,
        })

    from app.models import SchoolSetting, Student as StudentModel

    def setting(key, default=''):
        return SchoolSetting.get(key, default)

    crest_path = os.path.join(current_app.root_path, 'static', 'img', 'nyatsime-crest.png')
    class_size = StudentModel.query.filter_by(class_id=report.class_id, is_active=True).count()

    dob = student.date_of_birth.strftime('%d %B %Y') if student.date_of_birth else 'N/A'

    html_content = render_template_string(
        REPORT_CARD_HTML,
        student=student,
        student_dob=dob,
        class_name=class_obj.name if class_obj else 'N/A',
        form_name=class_obj.grade.name if class_obj and class_obj.grade else 'N/A',
        report=report,
        marks=marks,
        class_size=class_size,
        crest_path=crest_path,
        school_name=setting('school_name', 'NYATSIME COLLEGE'),
        school_motto=setting('school_motto', ''),
        school_address=setting('school_address', ''),
        school_phone=setting('school_phone', ''),
        school_email=setting('school_email', ''),
        generated_date=datetime.now().strftime('%d %B %Y'),
    )

    output = BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=output)

    if pisa_status.err:
        raise Exception('Error generating PDF')

    output.seek(0)
    pdf_bytes = output.getvalue()

    try:
        with open(cache_path, 'wb') as f:
            f.write(pdf_bytes)
    except Exception:
        pass

    return pdf_bytes


def invalidate_report_cache(report_id):
    cache_dir = _get_cache_dir()
    for filename in os.listdir(cache_dir):
        if filename.startswith(f"report_{report_id}_"):
            try:
                os.remove(os.path.join(cache_dir, filename))
            except Exception:
                pass
