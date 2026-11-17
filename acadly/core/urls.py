from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import EmailLoginForm

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html",
                                                authentication_form=EmailLoginForm), name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("attendance/mark/", views.attendance_mark, name="attendance_mark"),
    path("attendance/manual/", views.attendance_manual, name="attendance_manual"),
    path("attendance/base/", views.attendance_base, name="attendance_base"),
    path("attendance/history/", views.attendance_history, name="attendance_history"),
    path("attendance/delete/<int:pk>/", views.attendance_delete, name="attendance_delete"),

    path("timetable/", views.timetable, name="timetable"),
    path("timetable/upload/", views.timetable_upload, name="timetable_upload"),
    path("timetable/review/", views.timetable_review, name="timetable_review"),

    path("marks/", views.marks, name="marks"),
    path("gpa/", views.gpa, name="gpa"),
    path("gpa/semester/delete/<int:pk>/", views.semester_delete, name="semester_delete"),
    path("resources/", views.resources, name="resources"),
    path("resources/delete/<int:pk>/", views.resource_delete, name="resource_delete"),
]
