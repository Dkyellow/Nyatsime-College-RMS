import os
import hashlib
from io import BytesIO

from PIL import Image
from xhtml2pdf import pisa
from flask import render_template_string, current_app


# ================================================================
# REPORT TEMPLATE VERSION
# ================================================================
# Change this whenever the PDF layout is changed.
# This prevents old cached PDFs from being reused.

REPORT_TEMPLATE_VERSION = "v14"


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
    margin: 9mm 12mm 9mm 12mm;

    /*
     * watermark_path is a FULL A4 transparent image.
     * The school logo has already been positioned at the centre
     * by Python, so xhtml2pdf does not need to calculate its position.
     */
    background-image: url("{{ watermark_path }}");
    background-repeat: no-repeat;
    background-position: 0mm 0mm;
    background-width: 210mm;
    background-height: 297mm;
}


* {
    margin: 0;
    padding: 0;
}


body {
    font-family: Helvetica, Arial, sans-serif;
    font-size: 9pt;
    color: #111;
}


/* ================================================================
   HEADER
   ================================================================ */

.hdr {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 3mm;
}

.hdr td {
    vertical-align: middle;
}

.hdr-logo {
    width: 23mm;
}

.hdr-logo img {
    width: 21mm;
    height: 21mm;
}

.hdr-title {
    padding-left: 12mm;
    text-align: center;
}

.hdr-rc {
    font-size: 24pt;
    font-weight: bold;
    color: #111;
    letter-spacing: 2px;
    line-height: 1;
}

.hdr-school {
    font-size: 11pt;
    font-weight: bold;
    color: {{ primary_color }};
    letter-spacing: 1.5px;
    margin-top: 1mm;
}


/* ================================================================
   STUDENT INFORMATION
   ================================================================ */

.info {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 2mm;
}

.info td {
    vertical-align: bottom;
    padding: 0 1.5mm 0 0;
}

.lbl {
    font-size: 9pt;
    font-weight: bold;
    white-space: nowrap;
    padding-right: 1.5mm;
}

.fld {
    border-bottom: 1.2pt solid #222;
    padding-bottom: 0.8mm;
    font-size: 9.5pt;
    font-weight: bold;
}

.spacer {
    width: 4mm;
}


/* ================================================================
   MARKS TABLE
   ================================================================ */

.marks {
    width: 100%;
    border-collapse: collapse;
    margin-top: 3mm;
}

.marks th {
    background: #111;
    color: #fff;
    font-size: 11pt;
    font-weight: bold;
    padding: 2mm 1.5mm;
    border: 1pt solid #000;
    text-align: center;
    vertical-align: middle;
}

.marks th.l {
    text-align: left;
}

.marks td {
    border: 1pt solid #000;
    padding: 1.5mm 1.5mm;
    vertical-align: middle;
    text-align: center;
}

.marks td.c1 {
    width: 10mm;
}

.marks td.c5 {
    width: 27mm;
}


/* ================================================================
   TABLE FONT SIZES
   ================================================================ */

.number-cell {
    font-size: 10pt;
}

.subject-cell {
    font-size: 10pt;
    font-weight: normal;
    text-align: left;
}

.mark-cell {
    font-size: 10pt;
}

.grade-cell {
    font-size: 11pt;
    font-weight: bold;
}


/* ================================================================
   TEACHER COMMENTS
   ================================================================ */

.cmt-hd {
    font-size: 9pt;
    font-weight: bold;
    text-align: right;
    margin-top: 3mm;
    margin-bottom: 1.5mm;
}

.cmt-line {
    border-bottom: 1pt solid #333;
    height: 5mm;
    margin-bottom: 1mm;
}

.cmt-text {
    font-size: 8.5pt;
    color: #333;
    padding: 1mm 0;
}


/* ================================================================
   FOOTER
   ================================================================ */

.ftr {
    border-top: 0.5pt solid #ccc;
    padding-top: 1.5mm;
    text-align: center;
    font-size: 6.5pt;
    color: #777;
    margin-top: 3mm;
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

        <div class="hdr-rc">
            REPORT CARD
        </div>

        <div class="hdr-school">
            {{ school_name }}
        </div>

    </td>


    <!-- Keeps title visually centred -->
    <td style="width:23mm"></td>

</tr>
</table>



<!-- =============================================================
     STUDENT INFORMATION - ROW 1
     ============================================================= -->

<table class="info">
<tr>

    <td class="lbl">
        Student Name:
    </td>

    <td style="width:62mm" class="fld">
        {{ student.first_name }} {{ student.last_name }}
    </td>

    <td class="spacer"></td>

    <td class="lbl">
        Class:
    </td>

    <td style="width:42mm" class="fld">
        {{ class_name }}
    </td>

</tr>
</table>



<!-- =============================================================
     STUDENT INFORMATION - ROW 2
     ============================================================= -->

<table class="info">
<tr>

    <td class="lbl">
        School Year:
    </td>

    <td style="width:24mm" class="fld">
        {{ report.academic_year }}
    </td>

    <td class="spacer"></td>

    <td class="lbl">
        Term:
    </td>

    <td style="width:24mm" class="fld">
        {{ report.academic_term }}
    </td>

    <td class="spacer"></td>

    <td class="lbl">
        Position:
    </td>

    <td style="width:32mm" class="fld">

        {% if report.position %}

            {{ report.position }}

            {% if class_size %}
                / {{ class_size }}
            {% endif %}

        {% else %}

            &mdash;

        {% endif %}

    </td>

</tr>
</table>



<!-- =============================================================
     MARKS TABLE
     ============================================================= -->

<table class="marks">

    <tr>

        <th class="c1">
            No
        </th>

        <th class="l">
            Subject
        </th>

        <th class="c5">
            Term Mark
        </th>

        <th class="c5">
            Avg Mark
        </th>

        <th class="c5">
            Grade
        </th>

    </tr>


    {% for m in marks %}

    <tr>

        <td class="c1 number-cell"
            style="font-size:10pt;">
            {{ loop.index }}
        </td>


        <td class="subject-cell"
            style="font-size:10pt; text-align:left;">
            {{ m.subject.name }}
        </td>


        <td class="mark-cell"
            style="font-size:10pt;">
            {{ "%.1f"|format(m.score) }}
        </td>


        <td class="mark-cell"
            style="font-size:10pt;">
            {{ "%.1f"|format(m.percent) }}%
        </td>


        <td class="grade-cell"
            style="font-size:11pt; font-weight:bold;">
            {{ m.grade or '&mdash;' }}
        </td>

    </tr>

    {% endfor %}



    <!-- Add empty rows only when there are fewer than 8 subjects -->

    {% for i in range([8 - marks|length, 0]|max) %}

    <tr>

        <td class="c1 number-cell"
            style="font-size:10pt;">
            &nbsp;
        </td>

        <td class="subject-cell"
            style="font-size:10pt; text-align:left;">
            &nbsp;
        </td>

        <td class="mark-cell"
            style="font-size:10pt;">
            &nbsp;
        </td>

        <td class="mark-cell"
            style="font-size:10pt;">
            &nbsp;
        </td>

        <td class="grade-cell"
            style="font-size:11pt;">
            &nbsp;
        </td>

    </tr>

    {% endfor %}

</table>



<!-- =============================================================
     TEACHER'S COMMENT
     ============================================================= -->

<div class="cmt-hd">
    Teacher's Comment
</div>


{% if report.teacher_comment %}

<div class="cmt-line">

    <div class="cmt-text">
        {{ report.teacher_comment }}
    </div>

</div>

{% endif %}


<div class="cmt-line"></div>



<!-- =============================================================
     FOOTER
     ============================================================= -->

<div class="ftr">

    {{ school_name }}

    {% if school_address %}
        &bull; {{ school_address }}
    {% endif %}

    {% if school_phone %}
        &bull; Tel: {{ school_phone }}
    {% endif %}

    {% if school_email %}
        &bull; {{ school_email }}
    {% endif %}

    <br/>

    This is an official academic document generated by the
    {{ school_name }} Academic Records System.

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
        "hillside-academy-crest.png"
    )


# ================================================================
# CREATE FULL A4 WATERMARK
# ================================================================

def _get_watermark_path():
    """
    Creates a full A4 transparent PNG.

    The school's logo is placed in the exact centre of this
    A4-sized image. This avoids relying on xhtml2pdf's
    background-position support, which can be inconsistent.
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

        WATERMARK_SIZE = 620


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


        # 8% visibility
        alpha = alpha.point(
            lambda p: int(p * 0.08)
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


    # Main logo shown in report header
    crest_path = _get_logo_path()


    # Full A4 transparent watermark
    watermark_path = _get_watermark_path()


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
            "HILLSIDE ACADEMY"
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
            "#1C3480"
        ),

        accent_color=setting(
            "accent_color",
            "#7A1F2B"
        ),

    )


    # ============================================================
    # GENERATE PDF
    # ============================================================

    output = BytesIO()


    pisa_status = pisa.CreatePDF(

        html_content,

        dest=output

    )


    if pisa_status.err:

        raise Exception(
            "Error generating PDF"
        )


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