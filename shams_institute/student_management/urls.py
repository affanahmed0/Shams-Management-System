from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Student List, Edit, Delete, Add
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.student_add, name='student_add'),
    path('students/<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),

    # Student Details
    path('students/<int:pk>/', views.student_detail, name='student_detail'),
    path('search_students/', views.search_students, name='search_students'),

    # Enrollments List, Edit, Delete, Add
    path('enroll_student/', views.enroll_student, name='enroll_student'),
    path('enrollments/', views.enrollment_list, name='enrollment_list'),
    path('enrollments/add/', views.enrollment_add, name='enrollment_add'),
    path('enrollments/<int:pk>/edit/', views.enrollment_edit, name='enrollment_edit'),
    path('enrollments/<int:pk>/delete/', views.enrollment_delete, name='enrollment_delete'),
    path('view_enrolled_students/<int:slot_id>/', views.view_enrolled_students, name='view_enrolled_students'),

    # Courses List, Edit, Delete, Add
    path('courses/', views.course_list, name='course_list'),
    path('courses/add/', views.course_add, name='course_add'),
    path('courses/<int:pk>/edit/', views.course_edit, name='course_edit'),
    path('courses/<int:pk>/delete/', views.course_delete, name='course_delete'),

    # Slot List, Edit, Delete, Add
    path('slots/', views.slot_list, name='slot_list'),
    path('slots/add/', views.slot_add, name='slot_add'),
    path('slots/<int:pk>/edit/', views.slot_edit, name='slot_edit'),
    path('slots/<int:pk>/delete/', views.slot_delete, name='slot_delete'),
    path('get_slots/', views.get_slots, name='get_slots'),

    # Fees List, Edit, Delete, Payment and Report
    path('fees/', views.fee_list, name='fee_list'),
    path('fees/add/', views.fee_add, name='fee_add'),
    path('fees/<int:pk>/edit/', views.fee_edit, name='fee_edit'),
    path('fees/<int:pk>/delete/', views.fee_delete, name='fee_delete'),
    path('daily_fee_report/', views.daily_fee_report, name='daily_fee_report'),
    path('fee_payment/<int:fee_id>/', views.record_fee_payment, name='record_fee_payment'),

    # Generate Fee Receipt
    path('generate_fee_receipt/<int:fee_id>/', views.generate_fee_receipt, name='generate_fee_receipt'),

    # Course Slot Report and Details
    path('course_slots_report/', views.course_slots_report, name='course_slots_report'),
    path('course_slot_details/<int:slot_id>/', views.course_slot_details, name='course_slot_details'),
    
    # Final Test Report 
    path('final_test_report/', views.final_test_report, name='final_test_report'),

    # Over Due Fees Report 
    path('overdue_fees_report/', views.overdue_fees_report, name='overdue_fees_report'),

    # Record Attendance and List 
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('record_attendance/<int:enrollment_id>/', views.record_attendance, name='record_attendance'),

    # Daily Attendance Report
    path('daily_attendance_report/', views.daily_attendance_report, name='daily_attendance_report'),
]