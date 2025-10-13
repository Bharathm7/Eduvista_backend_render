from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # off-screen rendering

from io import BytesIO
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

PAGE_WIDTH, PAGE_HEIGHT = A4
BOTTOM_MARGIN = 2*cm




# ---------- Helpers ----------
def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")


def generate_attendance_remark(attendance_percentage, longest_absent_streak):
    if attendance_percentage >= 95:
        remark = "Excellent attendance! Your child is consistently present and engaged in class."
    elif 90 <= attendance_percentage < 95:
        remark = "Good attendance! Your child attends regularly, keep encouraging them to maintain this consistency."
    elif 75 <= attendance_percentage < 90:
        remark = "Fair attendance. Encourage your child to attend regularly for better progress."
    else:
        remark = "Attendance is low. We recommend working together to improve regularity and participation."

    if longest_absent_streak >= 5:
        remark += " There were a few long absence periods; regular attendance helps in learning continuity."
    return remark


def get_attendance_summary(attendance_records):
    if not attendance_records:
        return {}

    attendance_records.sort(key=lambda x: parse_date(x['date']))
    total_days = len(attendance_records)
    total_present = sum(1 for r in attendance_records if r['status'].lower() == 'present')
    total_absent = total_days - total_present
    attendance_percentage = (total_present / total_days) * 100 if total_days else 0

    weekly_summary = defaultdict(lambda: {'present': 0, 'absent': 0, 'percentage': 0})
    for rec in attendance_records:
        date_obj = parse_date(rec['date'])
        week_start = date_obj - timedelta(days=date_obj.weekday())
        week_key = week_start.strftime("%Y-%m-%d")
        if rec['status'].lower() == 'present':
            weekly_summary[week_key]['present'] += 1
        else:
            weekly_summary[week_key]['absent'] += 1

    for week, data in weekly_summary.items():
        total = data['present'] + data['absent']
        data['percentage'] = (data['present'] / total) * 100 if total else 0

    longest_streak = 0
    current_streak = 0
    for rec in attendance_records:
        if rec['status'].lower() != 'present':
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0

    remark = generate_attendance_remark(attendance_percentage, longest_streak)

    return {
        'total_days': total_days,
        'total_present': total_present,
        'total_absent': total_absent,
        'attendance_percentage': round(attendance_percentage, 2),
        'weekly_summary': dict(weekly_summary),
        'remark': remark
    }


def create_attendance_pie_chart(attendance_records):
    present_count = sum(1 for r in attendance_records if r['status'].lower() == 'present')
    absent_count = sum(1 for r in attendance_records if r['status'].lower() == 'absent')
    total = present_count + absent_count

    if total == 0:
        return None

    plt.style.use("ggplot")
    fig, ax = plt.subplots(figsize=(5, 5), dpi=300)
    ax.pie(
        [present_count, absent_count],
        labels=["Present", "Absent"],
        autopct='%1.1f%%',
        startangle=90,
        colors=['#4CAF50', '#E74C3C'],
        textprops={'fontsize': 12}
    )
    ax.set_title("Attendance Distribution", fontsize=14, fontweight='bold')

    buf = BytesIO()
    plt.savefig(buf, format='PNG', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return buf


# ---------- PDF Generator ----------
def generate_attendance_pdf(student_name, attendance_records, month=10, year=2024):
    # Filter records for selected month & year
    month_records = [
        r for r in attendance_records
        if parse_date(r['date']).month == month and parse_date(r['date']).year == year
    ]

    summary = get_attendance_summary(month_records)
    remark = summary.get('remark', "No attendance data available for this month.")
    month_name = datetime(year, month, 1).strftime("%B %Y")

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    PAGE_WIDTH, PAGE_HEIGHT = A4
    BOTTOM_MARGIN = 2 * cm
    y = PAGE_HEIGHT - 2 * cm

    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(2 * cm, y, f"Attendance Report - {month_name}")
    y -= 1.2 * cm

    c.setFont("Helvetica", 14)
    c.drawString(2 * cm, y, f"Student: {student_name}")
    y -= 1.2 * cm

    # Attendance Summary
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, "Summary:")
    y -= 1 * cm
    c.setFont("Helvetica", 12)
    c.drawString(2 * cm, y, f"Total Days: {summary['total_days']}")
    y -= 0.6 * cm
    c.drawString(2 * cm, y, f"Days Present: {summary['total_present']}")
    y -= 0.6 * cm
    c.drawString(2 * cm, y, f"Days Absent: {summary['total_absent']}")
    y -= 0.6 * cm
    c.drawString(2 * cm, y, f"Attendance Percentage: {summary['attendance_percentage']}%")
    y -= 1.5 * cm

    # Weekly Breakdown Table
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, "Weekly Summary:")
    y -= 1 * cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Week Start")
    c.drawString(8 * cm, y, "Present")
    c.drawString(11 * cm, y, "Absent")
    c.drawString(14 * cm, y, "%")
    y -= 0.6 * cm
    c.setFont("Helvetica", 12)

    for week, data in summary['weekly_summary'].items():
        if y < BOTTOM_MARGIN + 3 * cm:
            c.showPage()
            y = PAGE_HEIGHT - 2 * cm
        c.drawString(2 * cm, y, week)
        c.drawString(8 * cm, y, str(data['present']))
        c.drawString(11 * cm, y, str(data['absent']))
        c.drawString(14 * cm, y, f"{data['percentage']:.1f}%")
        y -= 0.5 * cm

    y -= 1.5 * cm

    # Pie Chart
    chart_buffer = create_attendance_pie_chart(month_records)
    if chart_buffer:
        img = ImageReader(chart_buffer)
        chart_size = 8 * cm
        if y < BOTTOM_MARGIN + chart_size:
            c.showPage()
            y = PAGE_HEIGHT - 2 * cm
        c.drawImage(img, 5 * cm, y - chart_size, width=chart_size, height=chart_size)
        y -= chart_size + 1 * cm

    # Remark
    if y < BOTTOM_MARGIN + 2 * cm:
        c.showPage()
        y = PAGE_HEIGHT - 2 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, "Teacher's Note:")
    y -= 0.8 * cm
    c.setFont("Helvetica-Oblique", 12)
    remark_lines = []
    line = ""
    for word in remark.split():
        if c.stringWidth(line + " " + word, "Helvetica-Oblique", 12) < (PAGE_WIDTH - 4 * cm):
            line += " " + word
        else:
            remark_lines.append(line.strip())
            line = word
    remark_lines.append(line.strip())
    for l in remark_lines:
        if y < BOTTOM_MARGIN:
            c.showPage()
            y = PAGE_HEIGHT - 2 * cm
        c.drawString(2 * cm, y, l)
        y -= 0.6 * cm

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer



def generate_bar_chart(subjects_data):
    subjects = [s["subject_name"] for s in subjects_data]
    midterm_percents = []
    final_percents = []
    for s in subjects_data:
        # Extract midterm and final percentages from marks
        mid = next((m["percent"] for m in s["marks"] if m["exam_type"].lower() == "midterm"), 0)
        final = next((m["percent"] for m in s["marks"] if m["exam_type"].lower() == "final"), 0)
        midterm_percents.append(mid)
        final_percents.append(final)

    x = range(len(subjects))
    plt.figure(figsize=(8, 4))
    plt.bar(x, midterm_percents, width=0.4, label="Midterm", color="#4B8BBE", align='center')
    plt.bar([i + 0.4 for i in x], final_percents, width=0.4, label="Final", color="#306998", align='center')
    plt.xticks([i + 0.2 for i in x], subjects, rotation=45, ha="right")
    plt.ylim(0, 100)
    plt.ylabel("Percentage (%)")
    plt.title("Midterm vs Final Performance")
    plt.legend()

    # Annotate bars with values
    for i in x:
        plt.text(i, midterm_percents[i] + 1, f"{midterm_percents[i]:.1f}%", ha='center', fontsize=8)
        plt.text(i + 0.4, final_percents[i] + 1, f"{final_percents[i]:.1f}%", ha='center', fontsize=8)

    buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format="PNG")
    plt.close()
    buffer.seek(0)
    return buffer

# utils.py

def analyze_attendance(attendance_records, subjects_data):
    total_days = len(attendance_records)
    present_days = sum(1 for a in attendance_records if a["status"].lower() == "present")
    absent_days = sum(1 for a in attendance_records if a["status"].lower() == "absent")
    leave_days = sum(1 for a in attendance_records if a["status"].lower() == "leave")
    holiday_days = sum(1 for a in attendance_records if a["status"].lower() == "holiday")

    attendance_percent = (present_days / total_days * 100) if total_days else 0

    if subjects_data:
        overall_avg_percent = sum(sub['average_percent'] for sub in subjects_data) / len(subjects_data)
    else:
        overall_avg_percent = 0

    if attendance_percent < 75 and overall_avg_percent < 60:
        attendance_remark = (
            "Critical: Make sure your son/daughter is attending classes for improvement."
        )
    elif attendance_percent < 75 and overall_avg_percent >= 60:
        attendance_remark = "Attendance is low, improving attendance will help further."
    elif attendance_percent >= 75 and overall_avg_percent < 60:
        attendance_remark = "Attendance is okay, focus on improving academic performance."
    else:
        attendance_remark = "Good overall performance and attendance."

    return {
        "total_days": total_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "leave_days": leave_days,
        "holiday_days": holiday_days,
        "attendance_percent": attendance_percent,
        "overall_avg_percent": overall_avg_percent,
        "attendance_remark": attendance_remark
    }

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors

def generate_report_card(student_name, subjects_data, strengths, weaknesses, attendance_records):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()

    # Define custom styles for a clean, professional look
    title_style = ParagraphStyle(
        name="TitleStyle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0B3D91"),  # Deep Blue
        spaceAfter=24,
    )

    header_style = ParagraphStyle(
        name="HeaderStyle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#2E8B57"),  # Sea Green
        spaceBefore=12,
        spaceAfter=8,
    )

    subheader_style = ParagraphStyle(
        name="SubHeaderStyle",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#333333"),
        spaceBefore=8,
        spaceAfter=6,
    )

    normal_style = ParagraphStyle(
        name="NormalStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#4B4B4B"),
        spaceAfter=6,
    )

    italic_style = ParagraphStyle(
        name="ItalicStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#777777"),
        spaceAfter=10,
    )

    elements = []

    # Attendance calculations
    total_days = len(attendance_records)
    present_days = sum(1 for a in attendance_records if a["status"].lower() == "present")
    absent_days = sum(1 for a in attendance_records if a["status"].lower() == "absent")
    leave_days = sum(1 for a in attendance_records if a["status"].lower() == "leave")
    holiday_days = sum(1 for a in attendance_records if a["status"].lower() == "holiday")

    attendance_percent = (present_days / total_days * 100) if total_days else 0

    # Calculate average academic percentage
    overall_avg_percent = (sum(sub['average_percent'] for sub in subjects_data) / len(subjects_data)) if subjects_data else 0

    # Title
    elements.append(Paragraph(f"{student_name}'s Academic Report", title_style))

    # Attendance Summary Box
    attendance_summary = (
        f"<b>Attendance Summary:</b><br/>"
        f"Total Days: {total_days} &nbsp;&nbsp; "
        f"Present: {present_days} &nbsp;&nbsp; "
        f"Absent: {absent_days} &nbsp;&nbsp; "
        f"Leave: {leave_days} &nbsp;&nbsp; "
        f"Holidays: {holiday_days} &nbsp;&nbsp; "
        f"<br/><br/>"
        f"<b>Attendance Percentage:</b> {attendance_percent:.2f}%"
    )
    elements.append(Paragraph(attendance_summary, normal_style))
    elements.append(Spacer(1, 15))

    # Strengths & Weaknesses
    elements.append(Paragraph("Strengths", header_style))
    strengths_text = ", ".join(strengths) if strengths else "None"
    elements.append(Paragraph(strengths_text, normal_style))

    elements.append(Paragraph("Areas to Improve", header_style))
    weaknesses_text = ", ".join(weaknesses) if weaknesses else "None"
    elements.append(Paragraph(weaknesses_text, normal_style))
    elements.append(Spacer(1, 20))

    # Subject Performance Table
    table_data = [
        ["Subject","Midterm","Final","Average", "Grade", "Remarks", "Trend"]
    ]

    for subject in subjects_data:
        midterm_percent = next((m["percent"] for m in subject['marks'] if m["exam_type"].lower() == "midterm"), 0)
        final_percent = next((m["percent"] for m in subject['marks'] if m["exam_type"].lower() == "final"), 0)
        avg = subject['average_percent']

        grade = (
            subject['marks'][0]['grade']
            if subject['marks'] and subject['marks'][0].get('grade') != "No sufficient data"
            else "N/A"
        )
        remarks = subject['remarks']
        trend = subject['progress_trend']

        table_data.append([
            subject['subject_name'],
            f"{midterm_percent:.1f}%" if midterm_percent else "N/A",
            f"{final_percent:.1f}%" if final_percent else "N/A",
            f"{avg:.1f}%",
            grade,
            remarks,
            trend
        ])

    # Attendance remark logic
    if attendance_percent < 75 and overall_avg_percent < 60:
        attendance_remark = "Critical: Please ensure regular attendance for academic improvement."
    elif attendance_percent < 75 and overall_avg_percent >= 60:
        attendance_remark = "Attendance is low; improving it will support further progress."
    elif attendance_percent >= 75 and overall_avg_percent < 60:
        attendance_remark = "Attendance is satisfactory; focus on improving academics."
    else:
        attendance_remark = "Good overall performance and attendance."

    elements.append(Paragraph(
        f"<b>Attendance Remark:</b> {attendance_remark}",
        italic_style
    ))
    elements.append(Spacer(1, 12))
    col_widths = [100, 56, 55, 55, 40, 220, 60]
    # Table styling and layout
    table = Table(table_data, colWidths = col_widths )
    table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4B8BBE")),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 13),
    ('ALIGN', (1, 1), (-2, -1), 'CENTER'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
    ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ('ALIGN', (5, 1), (5, -1), 'LEFT'),  # Remarks left aligned
    ('ALIGN', (6, 1), (6, -1), 'CENTER'),  # Trend centered
    ('WORDWRAP', (0, 0), (-1, -1), True),  # Enable word wrap (sometimes helps)
]))
    elements.append(table)

    elements.append(PageBreak())

    # Performance Chart
    chart_buffer = generate_bar_chart(subjects_data)  # Assume this returns an Image-ready buffer
    elements.append(Paragraph("Performance Comparison (Midterm vs Final)", header_style))
    elements.append(Image(chart_buffer, width=450, height=225))
    elements.append(Spacer(1, 20))

    # Closing notes
    closing_text = """
    <para align=center>
    <b>Note:</b> This report card provides an overview of the student's performance in midterm and final exams. 
    Strengths and weaknesses are highlighted to guide future learning efforts.
    </para>
    """
    elements.append(Paragraph(closing_text, italic_style))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

