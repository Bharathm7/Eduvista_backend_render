from django.urls import path
from . import views

urlpatterns = [
    path("students/", views.students_list),
    path("teachers/", views.teachers_list),
    path("exams/", views.exams_list),
    path("marks/", views.marks_list),
    path("report/<int:student_id>/", views.report_card), 
    path("report/pdf/<int:student_id>/", views.report_card_pdf, name="report_card_pdf"),
    path("api/login/", views.supabase_login_api, name="api_login"),
    path("api/signup/", views.supabase_signup_api, name="api_signup"),
    path("api/home/", views.home_api, name="api_home"),
    path("api/logout/", views.logout_api, name="api_logout"),
    

]
