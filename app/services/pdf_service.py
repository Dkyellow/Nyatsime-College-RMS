import os
import hashlib
from io import BytesIO
from xhtml2pdf import pisa
from flask import render_template_string, current_app
from datetime import datetime


ECD_REPORT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page { size: A4; margin: 12mm 15mm; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #333; }
        .header { text-align: center; padding-bottom: 10px; margin-bottom: 12px; }
        .school-name { font-size: 22pt; font-weight: bold; color: #1B2A4A; margin-bottom: 2px; }
        .school-motto { font-style: italic; color: #666; font-size: 9pt; }
        .student-info { margin-bottom: 15px; }
        .student-info table { width: 100%; border-collapse: collapse; }
        .student-info td { padding: 3px 0; font-size: 9pt; }
        .student-info .label { font-weight: bold; width: 120px; color: #333; }
        .section-title { font-size: 11pt; font-weight: bold; margin: 12px 0 8px 0; color: #333; }
        .marks-table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
        .marks-table th { background: #1B2A4A; color: white; padding: 7px 10px; text-align: left; font-size: 9pt; }
        .marks-table td { padding: 6px 10px; border-bottom: 1px solid #e0e0e0; font-size: 9pt; }
        .marks-table tr:nth-child(even) { background: #f8f9fa; }
        .grade-badge { background: #C41E3A; color: white; padding: 2px 10px; border-radius: 4px; font-size: 8pt; font-weight: bold; }
        .summary-table { width: 100%; margin-bottom: 12px; }
        .summary-table td { width: 50%; text-align: center; padding: 10px 5px; background: #f0e6ea; border: 2px solid white; }
        .summary-table .value { font-size: 18pt; font-weight: bold; color: #1B2A4A; }
        .summary-table .label { font-size: 8pt; color: #666; }
        .comments { margin-bottom: 12px; }
        .comment-box { padding: 8px 0; }
        .comment-box .title { font-weight: bold; color: #1B2A4A; font-size: 9pt; margin-bottom: 2px; }
        .comment-box .text { font-size: 9pt; color: #333; }
        .signature-section { width: 100%; margin-top: 15px; }
        .signature-section td { width: 33%; text-align: center; padding: 0 10px; }
        .signature-line { border-top: 1px solid #333; margin-top: 40px; padding-top: 5px; font-size: 8pt; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <div class="school-name">Hillside Academy</div>
        <div class="school-motto">"Education For Self Reliance"</div>
    </div>
    <div class="student-info">
        <table>
            <tr>
                <td class="label">Student Name:</td>
                <td>{{ student.first_name }} {{ student.last_name }}</td>
                <td class="label">Grade/Class:</td>
                <td>{{ class_name }}</td>
            </tr>
            <tr>
                <td class="label">Admission No:</td>
                <td>{{ student.admission_number }}</td>
                <td class="label">Academic Term:</td>
                <td>{{ report.academic_term }}</td>
            </tr>
            <tr>
                <td class="label">Gender:</td>
                <td>{{ student.gender or 'N/A' }}</td>
                <td class="label">Academic Year:</td>
                <td>{{ report.academic_year }}</td>
            </tr>
        </table>
    </div>
    <div class="section-title">Developmental Assessment</div>
    <table class="marks-table">
        <thead>
            <tr>
                <th width="40">S/N</th>
                <th>Assessment Area</th>
                <th width="80">Score</th>
                <th width="80">Grade</th>
            </tr>
        </thead>
        <tbody>
            {% for mark in ecd_marks %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>{{ mark.assessment_field.name }}</td>
                <td>{{ "%.1f"|format(mark.score) }}</td>
                <td><span class="grade-badge">{{ mark.grade }}</span></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    <table class="summary-table">
        <tr>
            <td>
                <div class="value">{{ "%.1f"|format(report.total_marks) }}</div>
                <div class="label">Total Score</div>
            </td>
            <td>
                <div class="value">{{ "%.1f"|format(report.average) }}</div>
                <div class="label">Average</div>
            </td>
        </tr>
    </table>
    <div class="section-title">Comments</div>
    <div class="comments">
        <div class="comment-box">
            <div class="title">Teacher's Comment:</div>
            <div class="text">{{ report.teacher_comment or 'No comment provided.' }}</div>
        </div>
        <hr style="border:none;border-top:1px solid #e0e0e0;margin:5px 0;">
        <div class="comment-box">
            <div class="title">Administrator's Comment:</div>
            <div class="text">{{ report.admin_comment or 'No comment provided.' }}</div>
        </div>
    </div>
    <table class="signature-section">
        <tr>
            <td><div class="signature-line">Class Teacher's Signature</div></td>
            <td><div class="signature-line">Head Teacher's Signature</div></td>
            <td><div class="signature-line">Parent/Guardian's Signature</div></td>
        </tr>
    </table>
</body>
</html>
"""

PRIMARY_REPORT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page { size: A4; margin: 12mm 15mm; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #333; }
        .header { text-align: center; padding-bottom: 10px; margin-bottom: 12px; }
        .school-name { font-size: 22pt; font-weight: bold; color: #1B2A4A; margin-bottom: 2px; }
        .school-motto { font-style: italic; color: #666; font-size: 9pt; }
        .student-info { margin-bottom: 15px; }
        .student-info table { width: 100%; border-collapse: collapse; }
        .student-info td { padding: 3px 0; font-size: 9pt; }
        .student-info .label { font-weight: bold; width: 120px; color: #333; }
        .section-title { font-size: 11pt; font-weight: bold; margin: 12px 0 8px 0; color: #333; }
        .marks-table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
        .marks-table th { background: #1B2A4A; color: white; padding: 7px 10px; text-align: left; font-size: 9pt; }
        .marks-table td { padding: 6px 10px; border-bottom: 1px solid #e0e0e0; font-size: 9pt; }
        .marks-table tr:nth-child(even) { background: #f8f9fa; }
        .grade-badge { background: #C41E3A; color: white; padding: 2px 10px; border-radius: 4px; font-size: 8pt; font-weight: bold; }
        .summary-table { width: 100%; margin-bottom: 12px; }
        .summary-table td { width: 25%; text-align: center; padding: 10px 5px; background: #f0e6ea; border: 2px solid white; }
        .summary-table .value { font-size: 18pt; font-weight: bold; color: #1B2A4A; }
        .summary-table .label { font-size: 8pt; color: #666; }
        .comments { margin-bottom: 12px; }
        .comment-box { padding: 8px 0; }
        .comment-box .title { font-weight: bold; color: #1B2A4A; font-size: 9pt; margin-bottom: 2px; }
        .comment-box .text { font-size: 9pt; color: #333; }
        .signature-section { width: 100%; margin-top: 15px; }
        .signature-section td { width: 33%; text-align: center; padding: 0 10px; }
        .signature-line { border-top: 1px solid #333; margin-top: 40px; padding-top: 5px; font-size: 8pt; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <div class="school-name">Hillside Academy</div>
        <div class="school-motto">"Education For Self Reliance"</div>
    </div>
    <div class="student-info">
        <table>
            <tr>
                <td class="label">Student Name:</td>
                <td>{{ student.first_name }} {{ student.last_name }}</td>
                <td class="label">Grade/Class:</td>
                <td>{{ class_name }}</td>
            </tr>
            <tr>
                <td class="label">Admission No:</td>
                <td>{{ student.admission_number }}</td>
                <td class="label">Academic Term:</td>
                <td>{{ report.academic_term }}</td>
            </tr>
            <tr>
                <td class="label">Gender:</td>
                <td>{{ student.gender or 'N/A' }}</td>
                <td class="label">Academic Year:</td>
                <td>{{ report.academic_year }}</td>
            </tr>
        </table>
    </div>
    <div class="section-title">Subject Marks</div>
    <table class="marks-table">
        <thead>
            <tr>
                <th width="40">S/N</th>
                <th>Subject</th>
                <th width="80">Score</th>
                <th width="60">Grade</th>
            </tr>
        </thead>
        <tbody>
            {% for mark in report.marks %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>{{ mark.subject.name }}</td>
                <td>{{ "%.1f"|format(mark.score) }}</td>
                <td><span class="grade-badge">{{ mark.grade }}</span></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    <table class="summary-table">
        <tr>
            <td>
                <div class="value">{{ "%.1f"|format(report.total_marks) }}</div>
                <div class="label">Total Marks</div>
            </td>
            <td>
                <div class="value">{{ "%.1f"|format(report.average) }}</div>
                <div class="label">Average</div>
            </td>
            <td>
                <div class="value">{{ report.overall_grade }}</div>
                <div class="label">Overall Grade</div>
            </td>
            <td>
                <div class="value">{{ report.position }}</div>
                <div class="label">Class Position</div>
            </td>
        </tr>
    </table>
    <div class="section-title">Comments</div>
    <div class="comments">
        <div class="comment-box">
            <div class="title">Teacher's Comment:</div>
            <div class="text">{{ report.teacher_comment or 'No comment provided.' }}</div>
        </div>
        <hr style="border:none;border-top:1px solid #e0e0e0;margin:5px 0;">
        <div class="comment-box">
            <div class="title">Administrator's Comment:</div>
            <div class="text">{{ report.admin_comment or 'No comment provided.' }}</div>
        </div>
    </div>
    <table class="signature-section">
        <tr>
            <td><div class="signature-line">Class Teacher's Signature</div></td>
            <td><div class="signature-line">Head Teacher's Signature</div></td>
            <td><div class="signature-line">Parent/Guardian's Signature</div></td>
        </tr>
    </table>
</body>
</html>
"""

SECONDARY_REPORT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page { size: A4; margin: 12mm 15mm; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #333; }
        .header { text-align: center; padding-bottom: 10px; margin-bottom: 12px; }
        .school-name { font-size: 22pt; font-weight: bold; color: #1B2A4A; margin-bottom: 2px; }
        .school-motto { font-style: italic; color: #666; font-size: 9pt; }
        .student-info { margin-bottom: 15px; }
        .student-info table { width: 100%; border-collapse: collapse; }
        .student-info td { padding: 3px 0; font-size: 9pt; }
        .student-info .label { font-weight: bold; width: 120px; color: #333; }
        .section-title { font-size: 11pt; font-weight: bold; margin: 12px 0 8px 0; color: #333; }
        .marks-table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
        .marks-table th { background: #1B2A4A; color: white; padding: 7px 10px; text-align: left; font-size: 9pt; }
        .marks-table td { padding: 6px 10px; border-bottom: 1px solid #e0e0e0; font-size: 9pt; }
        .marks-table tr:nth-child(even) { background: #f8f9fa; }
        .grade-badge { background: #C41E3A; color: white; padding: 2px 10px; border-radius: 4px; font-size: 8pt; font-weight: bold; }
        .summary-table { width: 100%; margin-bottom: 12px; }
        .summary-table td { width: 25%; text-align: center; padding: 10px 5px; background: #f0e6ea; border: 2px solid white; }
        .summary-table .value { font-size: 18pt; font-weight: bold; color: #1B2A4A; }
        .summary-table .label { font-size: 8pt; color: #666; }
        .comments { margin-bottom: 12px; }
        .comment-box { padding: 8px 0; }
        .comment-box .title { font-weight: bold; color: #1B2A4A; font-size: 9pt; margin-bottom: 2px; }
        .comment-box .text { font-size: 9pt; color: #333; }
        .signature-section { width: 100%; margin-top: 15px; }
        .signature-section td { width: 33%; text-align: center; padding: 0 10px; }
        .signature-line { border-top: 1px solid #333; margin-top: 40px; padding-top: 5px; font-size: 8pt; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <div class="school-name">Hillside Academy</div>
        <div class="school-motto">"Education For Self Reliance"</div>
    </div>
    <div class="student-info">
        <table>
            <tr>
                <td class="label">Student Name:</td>
                <td>{{ student.first_name }} {{ student.last_name }}</td>
                <td class="label">Grade/Class:</td>
                <td>{{ class_name }}</td>
            </tr>
            <tr>
                <td class="label">Admission No:</td>
                <td>{{ student.admission_number }}</td>
                <td class="label">Academic Term:</td>
                <td>{{ report.academic_term }}</td>
            </tr>
            <tr>
                <td class="label">Gender:</td>
                <td>{{ student.gender or 'N/A' }}</td>
                <td class="label">Academic Year:</td>
                <td>{{ report.academic_year }}</td>
            </tr>
        </table>
    </div>
    <div class="section-title">Subject Marks</div>
    <table class="marks-table">
        <thead>
            <tr>
                <th width="40">S/N</th>
                <th>Subject</th>
                <th width="80">Score</th>
                <th width="60">Grade</th>
            </tr>
        </thead>
        <tbody>
            {% for mark in report.marks %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>{{ mark.subject.name }}</td>
                <td>{{ "%.1f"|format(mark.score) }}</td>
                <td><span class="grade-badge">{{ mark.grade }}</span></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    <table class="summary-table">
        <tr>
            <td>
                <div class="value">{{ "%.1f"|format(report.total_marks) }}</div>
                <div class="label">Total Marks</div>
            </td>
            <td>
                <div class="value">{{ "%.1f"|format(report.average) }}</div>
                <div class="label">Average</div>
            </td>
            <td>
                <div class="value">{{ report.overall_grade }}</div>
                <div class="label">Overall Grade</div>
            </td>
            <td>
                <div class="value">{{ report.position }}</div>
                <div class="label">Class Position</div>
            </td>
        </tr>
    </table>
    <div class="section-title">Comments</div>
    <div class="comments">
        <div class="comment-box">
            <div class="title">Teacher's Comment:</div>
            <div class="text">{{ report.teacher_comment or 'No comment provided.' }}</div>
        </div>
        <hr style="border:none;border-top:1px solid #e0e0e0;margin:5px 0;">
        <div class="comment-box">
            <div class="title">Administrator's Comment:</div>
            <div class="text">{{ report.admin_comment or 'No comment provided.' }}</div>
        </div>
    </div>
    <table class="signature-section">
        <tr>
            <td><div class="signature-line">Class Teacher's Signature</div></td>
            <td><div class="signature-line">Head Teacher's Signature</div></td>
            <td><div class="signature-line">Parent/Guardian's Signature</div></td>
        </tr>
    </table>
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

    template_type = 'primary'
    if class_obj and class_obj.grade and class_obj.grade.education_level:
        level_name = class_obj.grade.education_level.name
        if level_name == 'ECD':
            template_type = 'ecd'
        elif level_name == 'Secondary':
            template_type = 'secondary'

    ecd_marks = []
    if template_type == 'ecd':
        ecd_marks = report.ecd_marks

    if template_type == 'ecd':
        html_template = ECD_REPORT_HTML
    elif template_type == 'secondary':
        html_template = SECONDARY_REPORT_HTML
    else:
        html_template = PRIMARY_REPORT_HTML

    html_content = render_template_string(
        html_template,
        student=student,
        class_name=class_obj.name if class_obj else 'N/A',
        report=report,
        ecd_marks=ecd_marks,
        generated_date=datetime.now().strftime('%B %d, %Y')
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
