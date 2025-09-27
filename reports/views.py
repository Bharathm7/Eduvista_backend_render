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
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
import os

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL,SUPABASE_KEY)


# --- STUDENTS ---
@csrf_exempt
def students_list(request):
    response = supabase.table("student_details").select("*").execute()
    return JsonResponse(response.data, safe=False)

# --- TEACHERS ---
@csrf_exempt
def teachers_list(request):
    response = supabase.table("Teacher").select("*").execute()
    return JsonResponse(response.data, safe=False)

# --- EXAMS ---
@csrf_exempt
def exams_list(request):
    response = supabase.table("exam_details").select("*").execute()
    return JsonResponse(response.data, safe=False)

# --- MARKS ---
# def marks_list(request):
#     response = supabase.table("marks_details").select("*").execute()
#     return JsonResponse(response.data, safe=False)

# --- MARKS ---
# def marks_list(request, subject_id, student_id):
    # response = supabase.table("marks_details").select("*").eq("subject_id", subject_id).gte("student_id", student_id).lt("student_id", student_id + 40).execute()
    # return JsonResponse(response.data, safe=False)

# @api_view(["GET"])
# def marks_list(request, subject_id, class_id):
    try:
        teachsub = supabase.table("Teacher_subject_class") \
            .select("*") \
            .eq("subject_id", subject_id) \
            .eq("class_id", class_id) \
            .execute()
        if not teachsub.data:
            return JsonResponse({"error": "This subject is not taught in the selected class."}, status=404)
        students = supabase.table("student_details") \
            .select("student_id") \
            .eq("class_id", class_id) \
            .execute()

        student_ids = [s["student_id"] for s in students.data]

        if not student_ids:
            return JsonResponse({"error": "No students found in this class."}, status=404)
        marks = supabase.table("marks_details") \
            .select("*") \
            .eq("subject_id", subject_id) \
            .in_("student_id", student_ids) \
            .execute()

        print(len(marks.data))  # For debugging
        return JsonResponse(marks.data, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# --- MARKS ---
@api_view(["GET"])
@csrf_exempt
def marks_list(request, subject_id, class_id, exam_type):
    try:
        # 1. Check if the subject is taught in this class (optional)
        teachsub_response = supabase.table("Teacher_subject_class") \
            .select("*") \
            .eq("subject_id", subject_id) \
            .eq("class_id", class_id) \
            .execute()
        if not teachsub_response.data:
            return JsonResponse({"error": "Subject not taught in this class"}, status=404)

        # 2. Get all students in the class
        students_response = supabase.table("student_details") \
            .select("student_id") \
            .eq("class_id", class_id) \
            .execute()

        student_ids = [s["student_id"] for s in students_response.data]
        if not student_ids:
            return JsonResponse({"error": "No students found in this class."}, status=404)

        # 3. Get exam IDs matching exam_type
        exam_response = supabase.table("exam_details") \
            .select("exam_id") \
            .eq("class_id", class_id) \
            .execute()

        exam_ids = [e["exam_id"] for e in exam_response.data]
        if not exam_ids:
            return JsonResponse({"error": "No exams found for this exam type.", "exam_response": exam_response}, status=404)

        # 4. Get marks filtered by subject, students, and exam_ids
        marks_response = supabase.table("marks_details") \
            .select("*") \
            .eq("subject_id", subject_id) \
            .in_("student_id", student_ids) \
            .in_("exam_id", exam_ids) \
            .execute()

        return JsonResponse(marks_response.data, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_view(["POST"])
@csrf_exempt
def marks_update(request):
    try:
        data = request.data
        student_id = data.get("student_id")
        subject_id = data.get("subject_id")
        exam_id = data.get("exam_id")
        marks = data.get("marks")

        if not all([student_id, subject_id, exam_id, marks]):
            return Response({
                "error": "Missing one or more required fields (student_id, subject_id, exam_id, marks)"
            }, status=status.HTTP_400_BAD_REQUEST)


        marks_id = f"{student_id}_{subject_id}_{exam_id}"

        response = supabase.table("marks_details").upsert({
            "marks_id": marks_id,
            "student_id": student_id,
            "subject_id": subject_id,
            "exam_id": exam_id,
            "marks": marks
        }).execute()

        if response.data:
            return Response({"message": "Data has been updated successfully", "data": response.data})
        else:
            return Response({"message": "There was an issue inserting/updating the data"}, status=500)

    except Exception as e:
        return Response({"error": str(e)}, status=500)
    
# --- GRADES ---
@csrf_exempt
def grades_list(request, teacher_id, subject_id, class_id, exam_type):
    try:
        # 2. Get all students in the class
        students_response = supabase.table("student_details") \
            .select("student_id") \
            .eq("class_id", class_id) \
            .execute()

        student_ids = [s["student_id"] for s in students_response.data]
        if not student_ids:
            return JsonResponse({"error": "No students found in this class."}, status=404)
        # print(student_ids)
        # 3. Get exam IDs matching exam_type
        exam_response = supabase.table("exam_details") \
            .select("exam_id") \
            .eq("class_id", class_id) \
            .eq("exam_type", exam_type) \
            .execute()

        exam_ids = [e["exam_id"] for e in exam_response.data]
        print("exam_ids: ",exam_ids)
        if not exam_ids:
            return JsonResponse({"error": "No exams found for this exam type."}, status=404)
        
        # 4. Get marks filtered by subject, students, and exam_ids
        marks_response = supabase.table("marks_details") \
            .select("*") \
            .eq("subject_id", subject_id) \
            .in_("exam_id", exam_ids) \
            .in_("student_id", student_ids) \
            .execute()
        # print("marks_response: ",marks_response.data)
        # print("marks_response_error: ",marks_response.error)
        graded_marks = []
        for mark in marks_response.data:
            marks_obtained = mark.get("marks", 0)
            max_marks = mark.get("max_marks", 50 if exam_type.lower() == "midterm" else 100)
            
            # Determine grade based on exam type
            if exam_type.lower() == "midterm":
                if 46 <= marks_obtained <= 50:
                    grade = "A"
                elif 41 <= marks_obtained <= 45:
                    grade = "B"
                elif 36 <= marks_obtained <= 40:
                    grade = "C"
                elif 31 <= marks_obtained <= 35:
                    grade = "D"
                else:
                    grade = "F"
            elif exam_type.lower() == "final":
                if 91 <= marks_obtained <= 100:
                    grade = "A"
                elif 81 <= marks_obtained <= 90:
                    grade = "B"
                elif 71 <= marks_obtained <= 80:
                    grade = "C"
                elif 61 <= marks_obtained <= 70:
                    grade = "D"
                else:
                    grade = "F"
            else:
                grade = "N/A"

            # Include grade in response
            mark_with_grade = {**mark, "grade": grade}
            graded_marks.append(mark_with_grade)

        return JsonResponse(graded_marks, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# --- CLASSES ---
@csrf_exempt
def class_list(request, teacher_id, subject_id):
    teacher_details = supabase.table("Teacher_subject_class").select("*").eq("teacher_id", teacher_id).eq("subject_id", subject_id).execute()
    
    class_ids = [row["class_id"] for row in teacher_details.data]
    # print("Teacher ID:", teacher_id)
    # print("Teacher Details: ", teacher_details)
    # print(class_ids)
    response = supabase.table("class_details").select("*").in_("class_id", class_ids).execute()
    # print("Classes fetched:", response.data)
    return JsonResponse(response.data, safe=False)

# --- SUBJECTS ---
@csrf_exempt
def subject_list(request,teacher_id):
    teacher_subject = supabase.table("Teacher_subject_class").select("*").eq("teacher_id", teacher_id).execute()
    subject_ids = [row["subject_id"] for row in teacher_subject.data]
    response = supabase.table("subject_details").select("*").in_("subject_id", subject_ids).execute()
    # print(response)
    return JsonResponse(response.data, safe=False)

# --- GET SUBJECT WITH TECHER_ID AND CLASS_ID ---
@csrf_exempt
def getSubject(request, teacher_id, class_id):
    subject = supabase.table("Teacher_subject_class").select("*").eq("teacher_id", teacher_id).eq("class_id", class_id).execute()
    # print(subject.data)
    return  JsonResponse(subject.data, safe=False)

# --- ATTENDANCE ---
@csrf_exempt
@api_view(["GET"])
def students_of_my_class(request, my_class_id):
    day = request.GET.get("date")
    # print("Got the attendance request")
    try:

        # formatted_day = datetime.strptime(day, "%Y-%m-%d").strftime("%d-%m-%Y")
        formatted_day = day.strip('"') 

        # 2. Get students of that class
        students_resp = supabase.table("student_details").select("*").eq("class_id", my_class_id).execute()
        students = students_resp.data

        # 3. Get attendance of those students
        student_ids = [s["student_id"] for s in students]
        attendance_resp = supabase.table("attendance_details").select("*").in_("student_id", student_ids).eq("date", formatted_day).execute()
        attendance_data = attendance_resp.data
        # print("attendance_data:", attendance_data)

        # Map attendance by student_id
        attendance_map = {}
        for a in attendance_data:
            sid = a["student_id"]
            if sid not in attendance_map:
                attendance_map[sid] = []
            attendance_map[sid].append(a)

        # 4. Attach attendance to each student
        enriched_students = []
        for s in students:
            s["attendance"] = attendance_map.get(s["student_id"], [])
            enriched_students.append(s)

        return Response({
            "class_id": my_class_id,
            "students": enriched_students
        })

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(["POST"])
@csrf_exempt
def mark_attendance(request):
    try:
        data = request.data
        student_id = data.get("student_id")
        class_id = data.get("class_id")
        status_str = data.get("status")
        att_date = data.get("date")

        if not all([student_id, class_id, status_str]):
            return Response({
                "error": "Missing one or more required fields (student_id, class_id, status)"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create a unique attendance_id similar to marks_id style
        attendance_id = f"{student_id}_{class_id}"

        # Upsert attendance record
        response = supabase.table("attendance_details").upsert({
            "att_id": attendance_id,
            "student_id": student_id,
            "class_id": class_id,
            "status": status_str,
            "date": att_date
        }).execute()

        if response.data:
            return Response({"message": "Attendance updated successfully", "data": response.data})
        else:
            return Response({"message": "Failed to update attendance"}, status=500)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@csrf_exempt
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

@csrf_exempt
def report_card_pdf(request, student_id):
    # 1. Student
    student = supabase.table("student_details").select("*").eq("student_id", student_id).execute().data[0]

    # 2. Class Info
    class_info = supabase.table("class_details").select("*").eq("class_id", student["class_id"]).execute().data[0]
    # print(class_info)
    # 3. Marks
    marks = supabase.table("marks_details").select("*").eq("student_id", student_id).execute().data

    # 4. Exam Details
    exams = supabase.table("exam_details").select("*").eq("class_id", student["class_id"]).execute().data
    exam_map = {e["exam_id"]: e for e in exams}

    # Academic Year (take from any exam)
    academic_year = exams[0]["academic_year"] if exams else "N/A"

    # 5. Subjects
    
    # subjects = supabase.table("subject_details").select("*").execute().data
    # subject_map = {s["subject_id"]: s for s in subjects}

    classSubjects = supabase.table("Teacher_subject_class").select("*").eq("class_id", class_info["class_id"]).execute()
    subjectIds = [row["subject_id"] for row in classSubjects.data]
    subjects = supabase.table("subject_details").select("*").eq("subject_id", subjectIds).execute().data
    subject_map = {s["subject_id"]: s for s in subjects}

    # 6. Attendance (for that academic year)
    attendance_records = supabase.table("attendance_details").select("*").eq("student_id", student_id).execute().data

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




@api_view(["POST"])
@csrf_exempt
def supabase_login_api(request):
    email = request.data.get("email")
    password = request.data.get("password")

    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})

        if user and user.user:
            user_id = user.user.id
            session = user.session

            teacher = supabase.table("Teacher").select("*").eq("user_id", user_id).execute()
            teacher_data = teacher.data[0] if teacher.data else None
            

            classes = supabase.table("Teacher_subject_class").select("*").eq("teacher_id", teacher_data['teacher_id']).execute()
            class_ids = [row["class_id"] for row in classes.data]
            classes_list = supabase.table("class_details").select("*").in_("class_id", class_ids).execute()
            # teacher = supabase.table("Teacher").select("*").eq("teacher_id", teacher_data['teacher_id']).execute()

            # {"email": "kritichopra@gmail.com", "password": "password"}
            

            return Response({
                "message": "Login successful",
                "user_id": user_id,
                "email": email,
                "teacher": teacher_data,
                "class_info": classes_list.data,
                "access_token": session.access_token,    
                "refresh_token": session.refresh_token,   
                "expires_in": session.expires_in,         
                "token_type": session.token_type 
            })

        return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        print("Error: ", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@csrf_exempt
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
@csrf_exempt
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
@csrf_exempt
def logout_api(request):
    request.session.flush()
    return Response({"message": "Logged out successfully"})


