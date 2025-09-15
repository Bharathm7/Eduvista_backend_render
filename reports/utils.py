from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # ✅ ensures plots render off-screen




def calculate_grade(percentage):
    if percentage >= 90:
        return "A+"
    elif percentage >= 75:
        return "A"
    elif percentage >= 60:
        return "B"
    elif percentage >= 50:
        return "C"
    elif percentage >= 35:
        return "D"
    else:
        return "F"


def generate_bar_chart(midterm_results, final_results):
    subjects = [m["subject"] for m in midterm_results]
    mid_marks = [m["marks"] for m in midterm_results]
    final_marks = [f["marks"] for f in final_results]

    plt.figure(figsize=(8, 4))
    x = range(len(subjects))
    plt.bar(x, mid_marks, width=0.4, label="Midterm", align="center")
    plt.bar([i + 0.4 for i in x], final_marks, width=0.4, label="Final", align="center")
    plt.xticks([i + 0.2 for i in x], subjects, rotation=45, ha="right")
    plt.ylabel("Marks")
    plt.title("Midterm vs Final Performance")
    plt.legend()

    buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format="PNG")
    buffer.seek(0)
    plt.close()
    return buffer


def generate_report_card(student, class_info, academic_year, midterm_results, final_results, attendance_records):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # --- Title ---
    elements.append(Paragraph("<b>STUDENT REPORT CARD</b>", styles["Heading1"]))
    elements.append(Spacer(1, 12))

    # --- Student Info ---
    student_info = f"""
    <b>Name:</b> {student['first_name']} {student['last_name']}<br/>
    <b>Class:</b> {class_info['class_name']} ({class_info['class_id']})<br/>
    <b>DOB:</b> {student['DOB']}<br/>
    <b>Gender:</b> {student['gender']}<br/>
    <b>Academic Year:</b> {academic_year}
    """
    elements.append(Paragraph(student_info, styles["Normal"]))
    elements.append(Spacer(1, 12))

    # --- Midterm Results ---
    if midterm_results:
        data = [["Subject", "Marks", "Max Marks"]]
        total, max_total = 0, 0
        for r in midterm_results:
            data.append([r["subject"], r["marks"], r["max_marks"]])
            total += r["marks"]
            max_total += r["max_marks"]

        percentage = (total / max_total) * 100 if max_total else 0
        grade = calculate_grade(percentage)

        data.append(["<b>Total</b>", total, max_total])
        data.append(["<b>Percentage</b>", f"{percentage:.2f}%", grade])

        table = Table(data, colWidths=[200, 80, 80])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ]))
        elements.append(Paragraph("<b>Midterm Exam</b>", styles["Heading2"]))
        elements.append(table)
        elements.append(Spacer(1, 12))

    # --- Final Results ---
    if final_results:
        data = [["Subject", "Marks", "Max Marks"]]
        total, max_total = 0, 0
        for r in final_results:
            data.append([r["subject"], r["marks"], r["max_marks"]])
            total += r["marks"]
            max_total += r["max_marks"]

        percentage = (total / max_total) * 100 if max_total else 0
        grade = calculate_grade(percentage)

        data.append(["<b>Total</b>", total, max_total])
        data.append(["<b>Percentage</b>", f"{percentage:.2f}%", grade])

        table = Table(data, colWidths=[200, 80, 80])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ]))
        elements.append(Paragraph("<b>Final Exam</b>", styles["Heading2"]))
        elements.append(table)
        elements.append(Spacer(1, 12))

    # --- Graph ---
    if midterm_results and final_results:
        chart = generate_bar_chart(midterm_results, final_results)
        elements.append(Paragraph("<b>Performance Comparison</b>", styles["Heading2"]))
        elements.append(Image(chart, width=400, height=200))
        elements.append(Spacer(1, 12))

        # --- Attendance ---# --- Attendance Section ---
    if attendance_records:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("<b>Attendance Summary</b>", styles["Heading2"]))

    total_days = len(attendance_records)
    present_days = sum(1 for a in attendance_records if a["status"].lower() == "present")
    absent_days = sum(1 for a in attendance_records if a["status"].lower() == "absent")
    leave_days = sum(1 for a in attendance_records if a["status"].lower() == "leave")
    holiday_days = sum(1 for a in attendance_records if a["status"].lower() == "holiday")

    attendance_percent = (present_days / total_days * 100) if total_days > 0 else 0

    data = [
        ["Total Days", "Present", "Absent", "Leave", "Holiday", "Attendance %"],
        [total_days, present_days, absent_days, leave_days, holiday_days, f"{attendance_percent:.2f}%"],
    ]

    table = Table(data, colWidths=[70]*6)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    elements.append(table)


    doc.build(elements)
    buffer.seek(0)
    return buffer
