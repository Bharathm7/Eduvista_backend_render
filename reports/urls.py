from django.urls import path
from . import views

urlpatterns = [
    path("students/", views.students_list),
    path("teachers/", views.teachers_list),
    path("exams/", views.exams_list),
    # path("marks/<str:subject_id>/<int:student_id>", views.marks_list),
    path("marks/<str:subject_id>/<int:class_id>/<str:exam_type>", views.marks_list),
    path("grades/<str:teacher_id>/<str:subject_id>/<int:class_id>/<str:exam_type>", views.grades_list),
    # path("grades/<str:teacher_id>/<int:class_id>/<str:exam_type>", views.grades_list),
    path("marks_update/", views.marks_update),
    path("classes/<str:teacher_id>/<str:subject_id>", views.class_list),
    path("subjects/<str:teacher_id>/", views.subject_list),
    path("subject/<str:teacher_id>/<int:class_id>", views.getSubject),
    path("api/myclass/students/<int:my_class_id>/", views.students_of_my_class, name="students_of_my_class_with_id"),
    path("mark_attendance/", views.mark_attendance),
    path("report/<int:student_id>/", views.report_card), 
    path("report/pdf/<int:student_id>/", views.report_card_pdf, name="report_card_pdf"),
    path("api/login/", views.supabase_login_api, name="api_login"),
    path("api/signup/", views.supabase_signup_api, name="api_signup"),
    path("api/home/", views.home_api, name="api_home"),
    path("api/logout/", views.logout_api, name="api_logout"),
    

]
