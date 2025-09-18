from django.http import JsonResponse
from django.http import FileResponse
from .utils import generate_report_card
from backend.supabase_client import supabase
from datetime import datetime
import uuid
from supabase import create_client
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

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

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


@api_view(["POST"])
def supabase_login_api(request):
    email = request.data.get("email")
    password = request.data.get("password")

    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})

        if user and user.user:
            user_id = user.user.id
            print(user_id)
            teacher = supabase.table("Teacher").select("*").eq("user_id", user_id).execute()
            teacher_data = teacher.data[0] if teacher.data else None
            print(teacher_data)
            

            classes = supabase.table("Teacher_subject_class").select("*").eq("teacher_id", teacher_data['teacher_id']).execute()
            teacher = supabase.table("Teacher").select("*").eq("teacher_id", teacher_data['teacher_id']).execute()
            #print(class_details.data)
            # {"email": "kritichopra@gmail.com", "password": "password"}

             # = supabase.query(query).execute()  # or supabase.sql(query).execute() depending on library version


            return Response({
                "message": "Login successful",
                "user_id": user_id,
                "email": email,
                "teacher": teacher_data,
                "class_info":classes.data
            })

        return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def supabase_signup_api(request):
    email = request.data.get("email")
    password = request.data.get("password")
    teacher_id = request.data.get("teacher_id", "").strip()

    try:
        # Step 1: Sign up user
        user_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
        })

        user = user_response.user
        session = user_response.session

        if session is None:
            return Response({
                "message": "Please check your email to confirm your account before logging in."
            }, status=status.HTTP_202_ACCEPTED)

        # Step 2: Set session for further auth-required actions
        supabase.auth.set_session(session.access_token, session.refresh_token)

        user_id = user.id

        # Step 3: Check if teacher exists and is unlinked
        existing = supabase.table("Teacher").select("user_id").eq("teacher_id", teacher_id).execute()

        if not existing.data:
            return Response({"error": "Teacher not found"}, status=status.HTTP_404_NOT_FOUND)

        if existing.data[0]["user_id"] is not None:
            return Response({"error": "This teacher is already linked to a user."}, status=status.HTTP_400_BAD_REQUEST)

        # Step 4: Link user_id to teacher
        update_response = supabase.table("Teacher").update({"user_id": user_id}).eq("teacher_id", teacher_id).execute()

        if update_response.error:
            return Response({"error": f"Failed to link teacher: {update_response.error.message}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "Signup and teacher linking successful",
            "user_id": user_id,
            "email": email
        })

    except Exception as e:
        print("Signup error:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def home_api(request):
    user_id = request.query_params.get("user_id")

    if not user_id:
        return Response({"error": "User ID is required"}, status=status.HTTP_400_BAD_REQUEST)

    teacher = None
    teacher_subject_info = []
    timetable = []

    try:
        # Fetch teacher by user_id
        response = (
            supabase.table("Teacher")
            .select("*")
            .eq("user_id", str(user_id).strip())
            .execute()
        )

        if response.data:
            teacher = response.data[0]
            teacher_id = str(teacher.get("teacher_id")).strip()
        else:
            return Response({"message": "No teacher found for this user_id"}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": f"Error fetching teacher: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        # Fetch subjects
        subject_resp = supabase.rpc("get_teacher_subjects", {"teacher_id_input": teacher_id}).execute()
        teacher_subject_info = subject_resp.data if subject_resp else []

    except Exception as e:
        return Response({"error": f"Error fetching subject details: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        # Fetch timetable
        timetable_resp = supabase.rpc("get_teacher_timetable", {"p_teacher_id": teacher_id}).execute()
        timetable = timetable_resp.data if timetable_resp else []

    except Exception as e:
        return Response({"error": f"Error fetching timetable: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        "teacher": teacher,
        "teacher_subject_info": teacher_subject_info,
        "timetable": timetable
    })


@api_view(["POST"])
def logout_api(request):
    request.session.flush()
    return Response({"message": "Logged out successfully"})


