import os
import hashlib
from io import BytesIO
from pathlib import Path

from PIL import Image
from weasyprint import HTML
from flask import render_template_string, current_app


# ================================================================
# REPORT TEMPLATE VERSION
# ================================================================
# Change this whenever the PDF layout is changed.
# This prevents old cached PDFs from being reused.

REPORT_TEMPLATE_VERSION = "v31"


# ================================================================
# REPORT CARD HTML
# ================================================================

REPORT_CARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">

<style>

/* ================================================================
   PAGE
   ================================================================ */

@page {
    size: A4;
    margin: 10mm 14mm 10mm 14mm;

    background-image: url("{{ watermark_path }}");
    background-repeat: no-repeat;
    background-position: center center;
    background-size: 210mm 297mm;
}


* {
    margin: 0;
    padding: 0;
}


body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 9pt;
    color: #1a1a1a;
    background-color: transparent;
}


/* ================================================================
   HEADER
   ================================================================ */

.hdr {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 5mm;
    background-color: transparent;
}

.hdr td {
    vertical-align: middle;
}

.hdr-logo {
    width: 26mm;
}

.hdr-logo img {
    width: 24mm;
    height: 24mm;
}

.hdr-title {
    text-align: center;
    padding: 0 4mm;
}

.hdr-school {
    font-size: 16pt;
    font-weight: bold;
    color: {{ primary_color }};
    letter-spacing: 2px;
    line-height: 1.1;
    margin-bottom: 1mm;
}

.hdr-motto {
    font-size: 7pt;
    font-weight: bold;
    color: {{ accent_color }};
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 2mm;
}

.hdr-report {
    font-size: 9pt;
    font-weight: bold;
    color: #444;
    letter-spacing: 2px;
    text-transform: uppercase;
    border-top: 2pt solid {{ primary_color }};
    border-bottom: 1pt solid {{ primary_color }};
    padding: 1.5mm 0;
    margin-top: 1mm;
}


/* ================================================================
   STUDENT INFORMATION
   ================================================================ */

.info-box {
    width: 100%;
    border: 1pt solid {{ primary_color }};
    border-radius: 2mm;
    overflow: hidden;
    margin-top: 10mm;
    margin-bottom: 15mm;
}

.info-box-header {
    background: {{ primary_color }};
    color: #fff;
    font-size: 8pt;
    font-weight: bold;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 1.5mm 3mm;
}

.info {
    width: 100%;
    border-collapse: collapse;
}

.info td {
    vertical-align: middle;
    padding: 1.8mm 2mm;
}

.info .lbl {
    font-size: 7.5pt;
    font-weight: bold;
    white-space: nowrap;
    color: {{ primary_color }};
    text-transform: uppercase;
    letter-spacing: 0.5px;
    width: 22%;
}

.info .fld {
    font-size: 9pt;
    font-weight: bold;
    color: #1a1a1a;
    border-bottom: 0.5pt solid #ddd;
    padding-bottom: 1mm;
}

.info .spacer {
    width: 4mm;
}

.info tr:nth-child(odd) td {
    background: transparent;
}

.info tr:nth-child(even) td {
    background: rgba(253, 251, 249, 0.4);
}


/* ================================================================
   MARKS TABLE
   ================================================================ */

.marks {
    width: 100%;
    border-collapse: collapse;
    margin-top: 6mm;
    margin-bottom: 6mm;
    border: 0.5pt solid #ddd;
}

.marks th {
    background: {{ primary_color }};
    color: #fff;
    font-size: 7.5pt;
    font-weight: bold;
    padding: 2.5mm 2mm;
    border: none;
    text-align: center;
    vertical-align: middle;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

.marks th.l {
    text-align: left;
    padding-left: 3mm;
}

.marks td {
    border: none;
    padding: 2mm 2mm;
    vertical-align: middle;
    text-align: center;
    font-size: 9pt;
    border-bottom: 0.5pt solid #eee;
}

.marks tr:last-child td {
    border-bottom: none;
}

.marks tr:nth-child(odd) td {
    background: transparent;
}

.marks tr:nth-child(even) td {
    background: rgba(248, 246, 243, 0.8);
}

.marks td.c1 {
    width: 10mm;
    font-weight: bold;
    color: {{ primary_color }};
}

.marks td.subject-cell {
    text-align: left;
    padding-left: 3mm;
    font-weight: 600;
}

.marks td.grade-cell {
    font-weight: bold;
    color: {{ primary_color }};
}

.marks td.remarks-cell {
    text-align: left;
    padding-left: 2mm;
    font-size: 7.5pt;
    color: #555;
    font-style: italic;
    max-width: 35mm;
}


/* ================================================================
   PERFORMANCE SUMMARY
   ================================================================ */

.summary {
    width: 100%;
    border-collapse: collapse;
    margin-top: 6mm;
    margin-bottom: 6mm;
    border: 0.5pt solid #999;
}

.summary td {
    padding: 1.5mm 3mm;
    font-size: 9pt;
    border: 0.5pt solid #999;
    background: transparent;
}

.summary .s-label {
    font-weight: bold;
    color: #555;
    width: 35%;
}

.summary .s-value {
    font-weight: bold;
    color: {{ primary_color }};
}


/* ================================================================
   TEACHER COMMENTS (in footer)
   ================================================================ */

.cmt-section {
    margin-bottom: 2mm;
    width: 100%;
    text-align: center;
}

.cmt-hd {
    font-size: 7pt;
    font-weight: bold;
    text-align: center;
    margin: 0 0 1mm 0;
    color: #555;
    padding: 0;
}

.cmt-line {
    height: auto;
    margin-bottom: 0.5mm;
    width: 100%;
    text-align: center;
}

.cmt-text {
    font-size: 8pt;
    color: #333;
    font-style: italic;
    text-align: center;
    margin: 0 0 0.5mm 0;
    padding: 0;
}


/* ================================================================
   SIGNATURES (in footer)
   ================================================================ */

.sig-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 2mm;
}

.sig-table td {
    width: 50%;
    padding: 1mm 4mm;
    vertical-align: bottom;
}

.sig-line {
    border-bottom: 0.5pt solid #333;
    height: 5mm;
    margin-bottom: 0.5mm;
}

.sig-label {
    font-size: 7pt;
    color: #555;
}


/* ================================================================
   FOOTER
   ================================================================ */

.ftr {
    position: fixed;
    left: 14mm;
    bottom: 10mm;
    width: 182mm;
    border-top: 1.5pt solid {{ primary_color }};
    padding-top: 2mm;
    text-align: center;
    font-size: 7pt;
    color: #666;
    background-color: transparent;
}

.ftr-school {
    font-weight: bold;
    color: {{ primary_color }};
    font-size: 7.5pt;
    letter-spacing: 1px;
    margin-bottom: 0.5mm;
}

.ftr-divider {
    width: 30mm;
    height: 0.5pt;
    background: {{ primary_color }};
    margin: 1mm auto;
    opacity: 0.4;
}

.ftr-text {
    font-size: 6.5pt;
    color: #888;
    font-style: italic;
}

</style>
</head>


<body>

<!-- =============================================================
     HEADER
     ============================================================= -->

<table class="hdr">
<tr>
    <td class="hdr-logo">
        <img src="{{ crest_path }}" />
    </td>
    <td class="hdr-title">
        <div class="hdr-school">{{ school_name }}</div>
        <div class="hdr-motto">{{ school_motto }}</div>
        <div class="hdr-report">Report Card</div>
    </td>
    <td style="width:26mm"></td>
</tr>
</table>



<!-- =============================================================
     STUDENT INFORMATION
     ============================================================= -->

<div class="info-box">
<div class="info-box-header">Student Details</div>
<table class="info">
<tr>
    <td class="lbl">Student Name:</td>
    <td class="fld">{{ student.first_name }} {{ student.last_name }}</td>
    <td class="spacer"></td>
    <td class="lbl">Class:</td>
    <td class="fld">{{ class_name }}</td>
</tr>
<tr>
    <td class="lbl">School Year:</td>
    <td class="fld">{{ report.academic_year }}</td>
    <td class="spacer"></td>
    <td class="lbl">Term:</td>
    <td class="fld">{{ report.academic_term }}</td>
</tr>
<tr>
    <td class="lbl">Admission No:</td>
    <td class="fld">{{ student.admission_number }}</td>
    <td class="spacer"></td>
    <td class="lbl">Position:</td>
    <td class="fld">
        {% if report.position %}
            {{ report.position }}{% if class_size %} / {{ class_size }}{% endif %}
        {% else %}
            &mdash;
        {% endif %}
    </td>
</tr>
</table>
</div>



<!-- =============================================================
     MARKS TABLE
     ============================================================= -->

<table class="marks">
    <thead>
    <tr>
        <th class="c1">No</th>
        <th class="l">Subject</th>
        <th>Secured Mark</th>
        <th>Final Grade</th>
        <th>Grade Score</th>
        <th class="l">Remarks</th>
    </tr>
    </thead>
    <tbody>
    {% for m in marks %}
    <tr>
        <td class="c1">{{ loop.index }}</td>
        <td class="subject-cell">{{ m.subject.name }}</td>
        <td>{{ "%.0f"|format(m.score) }}</td>
        <td class="grade-cell">{{ m.grade or '&mdash;' }}</td>
        <td>{{ "%.0f"|format(m.percent) }}%</td>
        <td class="remarks-cell">{{ m.comment or '' }}</td>
    </tr>
    {% endfor %}
    </tbody>
</table>

{% if marks|length < 8 %}
<table class="marks" style="border-top:none;">
    <tbody>
    {% for i in range([8 - marks|length, 0]|max) %}
    <tr>
        <td class="c1">&nbsp;</td>
        <td class="subject-cell">&nbsp;</td>
        <td>&nbsp;</td>
        <td>&nbsp;</td>
        <td>&nbsp;</td>
        <td>&nbsp;</td>
    </tr>
    {% endfor %}
    </tbody>
</table>
{% endif %}



<!-- =============================================================
     PERFORMANCE SUMMARY
     ============================================================= -->

<table class="summary">
<tr>
    <td class="s-label">Average Mark</td>
    <td class="s-value">{{ "%.1f"|format(report.average) }}%</td>
    <td class="s-label">Overall Grade</td>
    <td class="s-value">{{ report.overall_grade or '&mdash;' }}</td>
</tr>
</table>


<!-- =============================================================
     FOOTER (comment + signatures + school info)
     ============================================================= -->

<div class="ftr">

    <div class="cmt-section">
        {% if report.teacher_comment %}
        <p class="cmt-text">{{ report.teacher_comment }}</p>
        {% endif %}
        <p class="cmt-hd">Class Teacher's Comment</p>
    </div>

    <table class="sig-table">
    <tr>
        <td>
            <div class="sig-line"></div>
            <div class="sig-label">Class Teacher &mdash; Signature &amp; Date</div>
        </td>
        <td>
            <div class="sig-line"></div>
            <div class="sig-label">Head of School &mdash; Signature &amp; Date</div>
        </td>
    </tr>
    </table>

    <div class="ftr-school">{{ school_name }}</div>
    <div class="ftr-divider"></div>
    <div class="ftr-text">
        {{ school_motto }}
        {% if school_address %} &bull; {{ school_address }}{% endif %}
        {% if school_phone %} &bull; Tel: {{ school_phone }}{% endif %}
        {% if school_email %} &bull; {{ school_email }}{% endif %}
        <br/>This is an official academic document generated by the {{ school_name }} Academic Records System.
    </div>

</div>

</body>
</html>
"""


# ================================================================
# CACHE DIRECTORY
# ================================================================

def _get_cache_dir():

    cache_dir = current_app.config.get(
        "REPORT_CACHE_DIR",
        "cached_reports"
    )

    os.makedirs(
        cache_dir,
        exist_ok=True
    )

    return cache_dir


# ================================================================
# CACHE KEY
# ================================================================

def _get_cache_key(report_id, updated_at):

    raw = (
        f"report_{report_id}_"
        f"{updated_at}_"
        f"{REPORT_TEMPLATE_VERSION}"
    )

    return hashlib.md5(
        raw.encode()
    ).hexdigest()


# ================================================================
# CACHE PATH
# ================================================================

def _get_cache_path(report_id, updated_at):

    cache_dir = _get_cache_dir()

    key = _get_cache_key(
        report_id,
        updated_at
    )

    return os.path.join(
        cache_dir,
        f"report_{report_id}_{key}.pdf"
    )


# ================================================================
# GET SCHOOL LOGO
# ================================================================

def _get_logo_path():
    """
    Returns the currently configured school logo.

    Falls back to the default logo when no uploaded logo
    is configured.
    """

    from app.models import SchoolSetting

    logo_filename = SchoolSetting.get(
        "logo_filename",
        ""
    )

    if logo_filename:

        path = os.path.join(
            current_app.root_path,
            "static",
            "uploads",
            logo_filename
        )

        if os.path.exists(path):
            return path


    return os.path.join(
        current_app.root_path,
        "static",
        "img",
        "logo.png"
    )


# ================================================================
# CREATE FULL A4 WATERMARK
# ================================================================

def _get_watermark_path():
    """
    Creates a full A4 transparent PNG.

    The school's logo is placed in the exact centre of this
    A4-sized image to serve as a page watermark.
    """

    logo_path = _get_logo_path()


    # Directory where generated watermark images are stored
    watermark_dir = os.path.join(
        current_app.root_path,
        "static",
        "watermarks"
    )

    os.makedirs(
        watermark_dir,
        exist_ok=True
    )


    # Build a watermark filename based on the school's logo name
    logo_name = os.path.splitext(
        os.path.basename(logo_path)
    )[0]


    watermark_path = os.path.join(
        watermark_dir,
        f"a4_watermark_{logo_name}.png"
    )


    # ============================================================
    # REUSE WATERMARK IF IT IS NEWER THAN THE SOURCE LOGO
    # ============================================================

    try:

        if os.path.exists(watermark_path):

            watermark_modified = os.path.getmtime(
                watermark_path
            )

            logo_modified = os.path.getmtime(
                logo_path
            )

            if watermark_modified >= logo_modified:
                return watermark_path

    except Exception:
        pass


    try:

        # ========================================================
        # OPEN SCHOOL LOGO
        # ========================================================

        logo = Image.open(
            logo_path
        ).convert("RGBA")


        # ========================================================
        # CREATE FULL A4 CANVAS
        #
        # 1240 x 1754 follows the A4 aspect ratio.
        # The exact pixel resolution is not important because
        # the image is scaled to A4 dimensions in the PDF.
        # ========================================================

        PAGE_WIDTH = 1240
        PAGE_HEIGHT = 1754


        page = Image.new(
            "RGBA",
            (
                PAGE_WIDTH,
                PAGE_HEIGHT
            ),
            (
                255,
                255,
                255,
                0
            )
        )


        # ========================================================
        # WATERMARK SIZE
        # ========================================================
        # Maximum size for the school logo.

        WATERMARK_SIZE = 700


        logo.thumbnail(
            (
                WATERMARK_SIZE,
                WATERMARK_SIZE
            ),
            Image.LANCZOS
        )


        # ========================================================
        # MAKE LOGO TRANSPARENT
        # ========================================================

        alpha = logo.getchannel("A")


        # 25% visibility
        alpha = alpha.point(
            lambda p: int(p * 0.25)
        )


        logo.putalpha(
            alpha
        )


        # ========================================================
        # CALCULATE EXACT CENTRE OF PAGE
        # ========================================================

        logo_width, logo_height = logo.size


        x = (
            PAGE_WIDTH - logo_width
        ) // 2


        y = (
            PAGE_HEIGHT - logo_height
        ) // 2


        # ========================================================
        # PLACE LOGO ON A4 CANVAS
        # ========================================================

        page.alpha_composite(
            logo,
            (
                x,
                y
            )
        )


        # ========================================================
        # SAVE FULL A4 WATERMARK
        # ========================================================

        page.save(
            watermark_path,
            "PNG"
        )


        return watermark_path


    except Exception:

        # Fall back to the normal logo if watermark generation fails.
        return logo_path


# ================================================================
# CONVERT FILESYSTEM PATH TO FILE URI
# ================================================================

def _path_to_uri(path):
    """
    Converts an absolute filesystem path to a file:/// URI
    that WeasyPrint can resolve.
    """
    return Path(path).as_uri()


# ================================================================
# GENERATE REPORT CARD PDF
# ================================================================

def generate_report_card_pdf(report):

    cache_path = _get_cache_path(
        report.id,
        report.updated_at
    )


    # ============================================================
    # RETURN CACHED REPORT
    # ============================================================

    if os.path.exists(cache_path):

        with open(
            cache_path,
            "rb"
        ) as f:

            return f.read()


    # ============================================================
    # STUDENT AND CLASS
    # ============================================================

    student = report.student
    class_obj = report.class_obj


    # ============================================================
    # PREPARE MARKS
    # ============================================================

    marks = []


    for m in sorted(
        report.marks,
        key=lambda x: (
            x.subject.name
            if x.subject
            else ""
        )
    ):

        max_score = m.max_score or 100


        percent = (
            (m.score / max_score) * 100
            if max_score
            else 0
        )


        marks.append({

            "subject": m.subject,

            "score": m.score or 0,

            "max_score": max_score,

            "percent": percent,

            "grade": m.grade,

            "comment": m.comment or '',

        })


    # ============================================================
    # LOAD SCHOOL SETTINGS
    # ============================================================

    from app.models import (
        SchoolSetting,
        Student as StudentModel
    )


    def setting(key, default=""):

        return SchoolSetting.get(
            key,
            default
        )


    # Main logo shown in report header (converted to file URI for WeasyPrint)
    crest_path = _path_to_uri(_get_logo_path())


    # Full A4 transparent watermark (converted to file URI for WeasyPrint)
    watermark_path = _path_to_uri(_get_watermark_path())


    # Active student count for class position display
    class_size = StudentModel.query.filter_by(

        class_id=report.class_id,

        is_active=True

    ).count()


    # ============================================================
    # RENDER REPORT HTML
    # ============================================================

    html_content = render_template_string(

        REPORT_CARD_HTML,

        student=student,

        class_name=(
            class_obj.name
            if class_obj
            else "N/A"
        ),

        report=report,

        marks=marks,

        class_size=class_size,

        crest_path=crest_path,

        watermark_path=watermark_path,


        school_name=setting(
            "school_name",
            "NYATSIME COLLEGE"
        ),

        school_address=setting(
            "school_address",
            ""
        ),

        school_phone=setting(
            "school_phone",
            ""
        ),

        school_email=setting(
            "school_email",
            ""
        ),

        primary_color=setting(
            "primary_color",
            "#4EA3D8"
        ),

        accent_color=setting(
            "accent_color",
            "#F4C542"
        ),

    )


    # ============================================================
    # GENERATE PDF
    # ============================================================

    output = BytesIO()


    HTML(
        string=html_content,
        base_url=current_app.root_path
    ).write_pdf(output)


    output.seek(0)

    pdf_bytes = output.getvalue()


    # ============================================================
    # CACHE GENERATED PDF
    # ============================================================

    try:

        with open(
            cache_path,
            "wb"
        ) as f:

            f.write(
                pdf_bytes
            )

    except Exception:

        # PDF generation should still work even if caching fails.
        pass


    return pdf_bytes


# ================================================================
# INVALIDATE REPORT CACHE
# ================================================================

def invalidate_report_cache(report_id):
    """
    Deletes all cached PDF files belonging to one report.
    """

    cache_dir = _get_cache_dir()


    for filename in os.listdir(cache_dir):

        if filename.startswith(
            f"report_{report_id}_"
        ):

            try:

                os.remove(
                    os.path.join(
                        cache_dir,
                        filename
                    )
                )

            except Exception:

                pass