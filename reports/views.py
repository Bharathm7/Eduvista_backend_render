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
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
import os
from .utils import generate_attendance_pdf
import logging

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL,SUPABASE_KEY)


# --- STUDENTS ------------------------------------------------------
@csrf_exempt
def students_list(request):
    response = supabase.table("student_details").select("*").execute()
    return JsonResponse(response.data, safe=False)

# --- TEACHERS ------------------------------------------------------
@csrf_exempt
def teachers_list(request):
    response = supabase.table("Teacher").select("*").execute()
    return JsonResponse(response.data, safe=False)

# --- EXAMS ------------------------------------------------------
@csrf_exempt
def exams_list(request):
    response = supabase.table("exam_details").select("*").execute()
    return JsonResponse(response.data, safe=False)

# Set up logging
logger = logging.getLogger(__name__)

#--marks-view------------------------------------------------------
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

        #3. Get exam IDs matching exam_type
        exam_response = supabase.table("exam_details") \
            .select("exam_id") \
            .eq("class_id", class_id) \
            .eq("exam_type",exam_type)\
            .execute()

        exam_ids = [e["exam_id"] for e in exam_response.data]
        print(len(exam_ids))

        if not exam_ids:
            return JsonResponse({"error": "No exams found for this exam type."}, status=404)

        # 4. Get marks filtered by subject, students, and exam_ids
        marks_response = supabase.table("marks_details") \
            .select("*") \
            .eq("subject_id", subject_id) \
            .in_("student_id", student_ids) \
            .in_("exam_id", exam_ids) \
            .execute()
        print("the total length is",len(marks_response.data))

        return JsonResponse(marks_response.data, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

#--marks-update-------------------------------------------------
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
    
# --- GRADES-visualization ------------------------------------------
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

# --- CLASSES ----------------------------------
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

# --- SUBJECTS -----------------------------
@csrf_exempt
def subject_list(request,teacher_id):
    teacher_subject = supabase.table("Teacher_subject_class").select("*").eq("teacher_id", teacher_id).execute()
    subject_ids = [row["subject_id"] for row in teacher_subject.data]
    response = supabase.table("subject_details").select("*").in_("subject_id", subject_ids).execute()
    # print(response)
    return JsonResponse(response.data, safe=False)

# --- GET SUBJECT WITH TECHER_ID AND CLASS_ID -----------------------
@csrf_exempt
def getSubject(request, teacher_id, class_id):
    subject = supabase.table("Teacher_subject_class").select("*").eq("teacher_id", teacher_id).eq("class_id", class_id).execute()
    # print(subject.data)
    return  JsonResponse(subject.data, safe=False)

# --- ATTENDANCE --------------------------------------
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

#--update-attendance---------------------------------
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


#--class-and-teacher-realtion---
def classes(request,teacher):
    result = supabase.table("Teacher_subject_class").select("*").eq("teacher_id", teacher).execute()
    # Extract class IDs
    class_ids = [row["class_id"] for row in result.data]
    # Fetch class details for these class IDs
    class_details = supabase.table("class_details").select("*").in_("class_id", class_ids).execute()

    return JsonResponse(class_details.data, safe=False)

#----report-gen--------------------------------------
#from django.http import JsonResponse
def calculate_remarks(avg_percent):
    if avg_percent is None:
        return "No data"
    elif avg_percent >= 90:
        return "Excellent performance! Keep it up."
    elif avg_percent >= 70:
        return "Good job! Aim for even higher."
    elif avg_percent >= 60:
        return "Satisfactory, but there is room for improvement."
    elif avg_percent >= 50:
        return "Needs improvement, focus more on this subject."
    else:
        return "Poor performance, additional help is recommended."

def calculate_trend(midterm_percent, final_percent,unit_percent):
    if midterm_percent is None or final_percent is None:
        return "No sufficient data"
    if final_percent > midterm_percent:
        return "Improving"
    elif final_percent < midterm_percent:
        return "Declining"
    else:
        return "Stable"
def calculate_grade(avg_percent):
    if avg_percent >= 90:
        return "A+"
    elif avg_percent >= 80:
        return "A"
    elif avg_percent >= 70:
        return "B"
    elif avg_percent >= 60:
        return "C"
    elif avg_percent >= 50:
        return "D"
    else:
        return "F"
def get_attendance_records_for_student(student_id):
    response = supabase.table("attendance_details").select("*").eq("student_id", student_id).execute()
    
    return response.data 

def get_student_analytics(student_id):
    result = []

    # Fetch student
    student_data = supabase.table("student_details").select("*").eq("student_id", student_id).execute().data
    print(f"DEBUG student_data for student_id {student_id}: {student_data}")
    if not student_data:
        print(f"ERROR: No student found for student_id {student_id}")
        return None

    student = student_data[0]
    student_class_id = student["class_id"]
    student_fname = student["first_name"]
    student_lname = student["last_name"]
    print(f"DEBUG class_id: {student_class_id}, student_name: {student_fname} {student_lname}")

    # Fetch related data
    tsc = supabase.table("Teacher_subject_class").select("*").eq("class_id", student_class_id).execute().data
    print(f"DEBUG Teacher_subject_class data: {tsc}")
    subjects = supabase.table("subject_details").select("*").execute().data
    print(f"DEBUG subjects data: {subjects}")
    marks = supabase.table("marks_details").select("*").eq("student_id", student_id).execute().data
    print(f"DEBUG marks_details data: {marks}")
    exams = supabase.table("exam_details").select("exam_id, exam_type").execute().data
    print("=== EXAM TYPES CHECK ===")
    for e in exams:
        print(f"Exam ID: {e['exam_id']}, Type: {e['exam_type']}")


    # Maps for fast lookup
    subject_map = {s["subject_id"]: s for s in subjects}
    exam_map = {e["exam_id"]: e for e in exams}
    subject_marks_map = {}

    subject_midterm_percent = {}
    subject_final_percent = {}
    subject_unit_percent = {}
    print("\n=== DEBUG: Exam Map ===")
    for eid, e in exam_map.items():
        print(f"Exam ID: {eid}, Type: {e['exam_type']}")

    print("\n=== DEBUG: Marks for this student ===")
    for m in marks:
        print(f"Exam ID: {m['exam_id']}, Subject ID: {m['subject_id']}, Marks: {m['marks']}")


    for m in marks:
        sid = m["subject_id"]
        obtained = m["marks"] or 0
        raw_exam_type = exam_map.get(m["exam_id"], {}).get("exam_type")
        exam_type = (raw_exam_type or "unit").lower()
        #exam_type = exam_map.get(m["exam_id"], {}).get("exam_type", "").lower()
        print(f"DEBUG processing mark: student_id={m['student_id']}, subject_id={sid}, exam_id={m['exam_id']}, exam_type={exam_type}, marks={obtained}")

        if "midterm" in exam_type:
            percent = (obtained / 50) * 100
            subject_midterm_percent[sid] = percent
            max_marks = 50
        elif "final" in exam_type:
            percent = (obtained / 100) * 100
            subject_final_percent[sid] = percent
            max_marks = 100
        elif any(x in exam_type for x in ["unit", "ut", "unittest"]):
            percent = (obtained / 100) * 100
            subject_unit_percent[sid] = percent
            max_marks = 100
        else:
            print(f"Unknown exam_type skipped: {exam_type}")
            continue

        if sid not in subject_marks_map:
            subject_marks_map[sid] = []

        subject_marks_map[sid].append({
            "exam_id": m["exam_id"],
            "exam_type": exam_map.get(m["exam_id"], {}).get("exam_type", "Unknown").title(),
            "marks": obtained,
            "max_marks": max_marks,
            "percent": round(percent, 2),
        })

    strengths = []
    weaknesses = []

    for mapping in tsc:
        subject_id = mapping["subject_id"]
        s = subject_map.get(subject_id)
        if not s:
            print(f"DEBUG: No subject found for subject_id {subject_id}")
            continue

        marks_list = subject_marks_map.get(subject_id, [])
        print(f"DEBUGGING {s['subject_name']}: {marks_list}")
        avg_percent = round(sum(m['percent'] for m in marks_list) / len(marks_list), 2) if marks_list else 0.0
        remarks = calculate_remarks(avg_percent)

        midterm_percent = subject_midterm_percent.get(subject_id)
        final_percent = subject_final_percent.get(subject_id)
        unit_percent = subject_unit_percent.get(subject_id)
        progress_trend = calculate_trend(midterm_percent, final_percent, unit_percent)

        if avg_percent >= 85:
            strengths.append(s["subject_name"])
            print(strengths)
        elif avg_percent <= 60:
            weaknesses.append(s["subject_name"])
            print(weaknesses)

        for mark in marks_list:
            mark["grade"] = calculate_grade(avg_percent or 0
            ) if midterm_percent is not None and final_percent is not None else "No sufficient data"

        result.append({
            "student_id": student_id,
            "student_name": f"{student_fname} {student_lname}",
            "subject_id": subject_id,
            "subject_name": s["subject_name"],
            "average_percent": avg_percent,
            "remarks": remarks,
            "progress_trend": progress_trend,
            "marks": marks_list,
            "unit_percent": unit_percent if unit_percent is not None else "No unit test data"
        })

    analytics = {
        "student_name": f"{student_fname} {student_lname}",
        "strengths": strengths,
        "weaknesses": weaknesses,
        "subjects": result,
    }

    # DEBUG: Print subjects and marks
    print("DEBUG subjects_data for student:", student_id)
    for sub in result:
        print(sub["subject_name"], "marks:", sub["marks"], "unit_percent:", sub["unit_percent"])

    return analytics



def final_reports(request, student_id):
    analytics = get_student_analytics(student_id)
    if analytics is None:
        return JsonResponse({"error": "Student not found"}, status=404)
    return JsonResponse(analytics, safe=False)


def gen_pdf(request, student_id):
    """
    Generates a student's report card PDF, uploads it to Supabase Storage,
    saves metadata in report_card_files table, and returns a public preview URL.
    """

    # --- Step 1: Fetch analytics and attendance ---
    analytics = get_student_analytics(student_id)
    if analytics is None or not analytics.get("subjects"):
        return HttpResponse("Student not found or no data", status=404)

    attendance_records = get_attendance_records_for_student(student_id)
    if attendance_records is None:
        return HttpResponse("Attendance records not found", status=404)

    # --- Step 2: Generate PDF in memory ---
    pdf_buffer = generate_report_card(
        student_name=analytics["student_name"],
        subjects_data=analytics["subjects"],
        strengths=analytics["strengths"],
        weaknesses=analytics["weaknesses"],
        attendance_records=attendance_records
    )

    # --- Step 3: Prepare PDF file for upload ---
    file_bytes = pdf_buffer.getvalue()
    file_name = f"report_card_{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    storage_path = f"report_cards/{file_name}"

    # --- Step 4: Upload PDF to Supabase Storage ---
    try:
        upload_response = supabase.storage.from_("report_cards").upload(
            storage_path,
            file_bytes,
            {"content-type": "application/pdf"}
        )
    except Exception as e:
        return JsonResponse({"error": f"Failed to upload PDF: {str(e)}"}, status=500)

    # --- Step 5: Get public preview URL ---
    public_url = supabase.storage.from_("report_cards").get_public_url(storage_path)

    # --- Step 6: Save metadata in report_card_files table ---
    teacher_id = "T001"

    try:
        supabase.table("report_card_files").insert({
            "student_id": student_id,
            "teacher_id": teacher_id,
            "file_path": storage_path,
            "file_url": public_url,
            "created_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        return JsonResponse({"error": f"Failed to save file metadata: {str(e)}"}, status=500)

    # --- Step 7: Return success response ---
    return JsonResponse({
        "message": "Report card generated, uploaded to Supabase successfully",
        "student_name": analytics["student_name"],
        "preview_url": public_url
    })


def behavioural_analysis(request, student_id):
    analytics = get_student_analytics(student_id)
    if analytics is None:
        return HttpResponse("Student not found", status=404)

    all_records = get_attendance_records_for_student(student_id)
    if not all_records:
        return HttpResponse("Attendance records not found", status=404)

    # Filter records for current month
    target_year = 2024
    target_month = 10  # October

    attendance_records = [
        rec for rec in all_records
        if datetime.strptime(rec['date'], '%Y-%m-%d').month == target_month
        and datetime.strptime(rec['date'], '%Y-%m-%d').year == target_year
    ]


    if not attendance_records:
        return HttpResponse("No attendance records for this month", status=404)

    #summary = all_records(attendance_records)
    # Generate PDF with filtered records
    pdf_buffer = generate_attendance_pdf(analytics['student_name'],all_records)

    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{analytics["student_name"].replace(" ","-")}_attendance_report.pdf"'
    return response


#--------aunthentication---------------
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
def home_api(request,user_id):
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

#------------------------ADMIN----------------------------
@api_view(["POST"])
@csrf_exempt
def update_students(request):
    try:
        data = request.data
        student_id = data.get("student_id")
        first_name = data.get("first_name")
        last_name  = data.get("last_name")
        DOB        = data.get("DOB")
        class_id   = data.get("class_id")
        parent_id  = data.get("parent_id")
        gender     = data.get("gender")
        address    = data.get("address")

        if not all ([student_id,first_name,last_name,DOB,class_id,parent_id,gender,address]):
            return Response({"error": "Missing one or more required fields."}, status=400)

        response = supabase.table("student_details").upsert({
                "student_id": student_id,
                "first_name": first_name,
                "last_name": last_name,
                "DOB": DOB,
                "class_id": class_id,
                "parent_id": parent_id,
                "gender": gender,
                "address": address,
            }).execute()

        if response.data:
            return Response({"message": "Data has been updated successfully", "data": response.data})
        else:
            return Response({"message": "There was an issue inserting/updating the data"}, status=500)

    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["post"])
def update_teacher(request):
    try:
        data = request.data
        print("-----------------------------payload-----------------------------------")
        print("available data",data)
        teacher_id = data.get("teacher_id")
        first_name = data.get("first_name")
        last_name  = data.get("last_name")
        designation = data.get("designation")
        education  = data.get("education")
        phone      = data.get("phone")
        salary     = data.get("salary")
        address    = data.get("address")
        gender     = data.get("gender")
        my_class   = data.get("my_class")

        print("Field values:", teacher_id, first_name, last_name, designation, education, phone, salary, address, gender, my_class)


        if not all ([teacher_id,first_name,last_name,designation,education,phone,salary,address,gender,my_class]):
            return Response({"error": "Missing one or more required fields."},status=400)

        response = supabase.table("Teacher").upsert({
            "teacher_id": teacher_id,
            "first_name": first_name,
            "last_name": last_name,
            "designation": designation,
            "education": education,
            "ph.": phone,
            "salary": salary,
            "address": address,
            "gender": gender,
            "my_class": my_class
            }).execute()

        if response.data:
            return Response({"message": "Data has been updated successfully", "data": response.data})
        else:
            return Response({"message": "There was an issue inserting/updating the data"}, status=500)

    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["POST"])
def exam_management(request):
    try:
        data = request.data 
        exam_id = data.get("exam_id")
        academic_year = data.get("academic_year")
        exam_type = data.get("exam_type")
        class_id = data.get("class_id")
        subject_id = data.get("subject_id")
        exam_date = data.get("exam_date")

        if not all ([exam_id,academic_year,exam_type,class_id,subject_id,exam_date]):
            return Response({"error": "Missing one or more fields."},status=400)

        response = supabase.table("exam_details").upsert({
            "exam_id": exam_id,
            "academic_year":academic_year,
            "exam_type":exam_type,
            "class_id":class_id,
            "subject_id":subject_id,
            "exam_date":exam_date
            }).execute()
        
        if reponse.data:
            return Response({"message": "Data has been updated successfully", "data": response.data})
        else:
            return Response({"message": "there was an issue intesering/updating the data"},status=500)
    except Exception as e:
        return Response({"error": str(e)},status=500)


@api_view(["POST"])
@csrf_exempt
def logout_api(request):
    request.session.flush()
    return Response({"message": "Logged out successfully"})


