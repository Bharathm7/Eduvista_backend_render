from django.urls import path
from . import views

urlpatterns = [
    path("students/", views.students_list),
    path("teachers/", views.teachers_list),
    path("exams/", views.exams_list),
    path("marks/", views.marks_list),
    path("report/<int:student_id>/", views.report_card), 
    path("report/pdf/<int:student_id>/", views.report_card_pdf, name="report_card_pdf"),
    

]
