from django.http import JsonResponse
from django.http import FileResponse
from .utils import generate_report_card
from backend.supabase_client import supabase
from datetime import datetime

# --- STUDENTS ---
def students_list(request):
    response = supabase.table("student_details").select("*").execute()
    return JsonResponse(response.data, safe=False)

# --- TEACHERS ---
def teachers_list(request):
    response = supabase.table("Teacher").select("*").execute()
    return JsonResponse(response.data, safe=False)

# --- EXAMS ---
def exams_list(request):
    response = supabase.table("exam_details").select("*").execute()
    return JsonResponse(response.data, safe=False)

# --- MARKS ---
def marks_list(request):
    response = supabase.table("marks_details").select("*").execute()
    return JsonResponse(response.data, safe=False)


def report_card(request, student_id):
    # 1. Get student info
    student = supabase.table("student_details").select("*").eq("student_id", student_id).execute()
    
    # 2. Get marks for this student
    marks = supabase.table("marks_details").select("*").eq("student_id", student_id).execute()
    
    # 3. Get exam details
    exams = supabase.table("exam_details").select("*").execute()
    
    # 4. Get subjects
    subjects = supabase.table("subject_details").select("*").execute()

    # Convert lists to dict for quick lookup
    exam_map = {e["exam_id"]: e for e in exams.data}
    subject_map = {s["subject_id"]: s for s in subjects.data}

    # 5. Build report structure
    report = {
        "student": student.data[0] if student.data else {},
        "results": []
    }


    for m in marks.data:
        report["results"].append({
            "exam": exam_map.get(m["exam_id"], {}),
            "subject": subject_map.get(m["subject_id"], {}),
            "marks": m["marks"],
        })

    return JsonResponse(report, safe=False)
def report_card_pdf(request, student_id):
    # 1. Student
    student = supabase.table("student_details").select("*").eq("student_id", student_id).execute().data[0]

    # 2. Class Info
    class_info = supabase.table("class_details").select("*").eq("class_id", student["class_id"]).execute().data[0]

    # 3. Marks
    marks = supabase.table("marks_details").select("*").eq("student_id", student_id).execute().data

    # 4. Exam Details
    exams = supabase.table("exam_details").select("*").eq("class_id", student["class_id"]).execute().data
    exam_map = {e["exam_id"]: e for e in exams}

    # Academic Year (take from any exam)
    academic_year = exams[0]["academic_year"] if exams else "N/A"

    # 5. Subjects
    subjects = supabase.table("subject_details").select("*").execute().data
    subject_map = {s["subject_id"]: s for s in subjects}

    # 6. Attendance (for that academic year)
    attendance_records = supabase.table("attendance_details") \
        .select("*") \
        .eq("student_id", student_id) \
        .execute().data

    if academic_year != "N/A" and "-" in academic_year:
        start_year, end_year = academic_year.split("-")
        start_year, end_year = int(start_year), int(end_year)

    filtered_attendance = []
    for a in attendance_records:
        try:
            att_year = datetime.strptime(a["date"], "%d-%m-%Y").year
            if start_year <= att_year <= end_year:
                filtered_attendance.append(a)
        except ValueError:
            continue  # skip bad dates
    attendance_records = filtered_attendance

    # 7. Separate Midterm & Final
    midterm_results, final_results = [], []

    for m in marks:
        subj = subject_map.get(m["subject_id"], {"subject_name": "Unknown"})
        exam = exam_map.get(m["exam_id"], {})

        record = {
            "subject": subj["subject_name"],
            "exam_type": exam.get("exam_type", ""),
            "marks": m["marks"],
            "max_marks": m["max_marks"],
        }

        if exam.get("exam_type", "").lower() in ["midterm", "mid term"]:
            midterm_results.append(record)
        elif exam.get("exam_type", "").lower() in ["final", "final exam"]:
            final_results.append(record)

    # 8. Generate PDF
    buffer = generate_report_card(
        student=student,
        class_info=class_info,
        academic_year=academic_year,
        midterm_results=midterm_results,
        final_results=final_results,
        attendance_records=attendance_records,
    )

    return FileResponse(buffer, as_attachment=True, filename=f"report_card_{student_id}_eduvista.pdf")
