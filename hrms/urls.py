# hrms/urls.py

from django.urls import path
from . import views

app_name = 'hrms'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'), # Main HRMS dashboard
    path('dashboard/data/', views.dashboard_data_api_view, name='dashboard_data_api'),

    # Officer Management
    path('officers/', views.officer_list_view, name='officer_list'),
    path('officers/add/', views.officer_create_view, name='officer_create'),
    path('officers/<str:service_number>/', views.officer_detail_view, name='officer_detail'),
    path('officers/<str:service_number>/edit/', views.officer_update_view, name='officer_update'),
    path('officers/<str:service_number>/delete/', views.officer_delete_view, name='officer_delete'),

    # Service History (Promotions & Transfers)
    path('officers/<str:service_number>/add-history/', views.service_history_create_view, name='service_history_create'),
    path('service-history/', views.service_history_list_view, name='service_history_list'), # Service History List
    path('service-history/<int:pk>/edit/', views.service_history_update_view, name='service_history_update'),
    path('service-history/<int:pk>/delete/', views.service_history_delete_view, name='service_history_delete'),
    path('service-history-report/', views.service_history_report_view, name='service_history_report'),

    # Leave Requests
    path('officers/<str:service_number>/request-leave/', views.leave_request_create_view, name='leave_request_create'),
    path('leave-requests/', views.leave_request_list_view, name='leave_request_list'),
    path('leave-requests/<int:pk>/detail/', views.leave_request_detail_view, name='leave_request_detail'),
    path('leave-requests/<int:pk>/approve/', views.leave_request_approve_view, name='leave_request_approve'),
    path('leave-requests/<int:pk>/reject/', views.leave_request_reject_view, name='leave_request_reject'),
    path('leave-report/', views.leave_report_view, name='leave_report'),

    # Officer Files
    path('officers/<str:service_number>/upload-file/', views.officer_file_upload_view, name='officer_file_upload'),
    path('officer-files/', views.officer_file_list_view, name='officer_file_list'),
    path('officer-files/<int:pk>/detail/', views.officer_file_detail_view, name='officer_file_detail'),
    path('officer-files/<int:pk>/respond/', views.officer_file_respond_view, name='officer_file_respond'),

    # Performance
    path('officers/<str:service_number>/add-performance/', views.performance_record_create_view, name='performance_record_create'),
    path('performance-records/', views.performance_record_list_view, name='performance_record_list'),
    path('performance-report/', views.performance_report_view, name='performance_report'),

    # Office Assignments
    path('officers/<str:service_number>/assign-office/', views.office_assignment_create_view, name='office_assignment_create'),
    path('office-assignments/<int:pk>/edit/', views.office_assignment_update_view, name='office_assignment_update'),

    # Region Management
    path('regions/', views.region_list_view, name='region_list'),
    path('regions/add/', views.region_create_view, name='region_create'),
    path('regions/<int:pk>/edit/', views.region_update_view, name='region_update'),
    path('regions/<int:pk>/delete/', views.region_delete_view, name='region_delete'),

    # Prison Station Management
    path('prison-stations/', views.prison_station_list_view, name='prison_station_list'),
    path('prison-stations/add/', views.prison_station_create_view, name='prison_station_create'),
    path('prison-stations/<int:pk>/edit/', views.prison_station_update_view, name='prison_station_update'),
    path('prison-stations/<int:pk>/delete/', views.prison_station_delete_view, name='prison_station_delete'),

    # Attendance Management
    path('officers/<str:service_number>/add-attendance/', views.attendance_record_create_view, name='attendance_record_create'),
    path('attendance-records/', views.attendance_record_list_view, name='attendance_record_list'),
    path('attendance-records/<int:pk>/edit/', views.attendance_record_update_view, name='attendance_record_update'),
    path('attendance-records/<int:pk>/delete/', views.attendance_record_delete_view, name='attendance_record_delete'),
    path('attendance-report/', views.attendance_report_view, name='attendance_report'),

    # Disciplinary Cases Management
    path('officers/<str:service_number>/add-disciplinary-case/', views.disciplinary_case_create_view, name='disciplinary_case_create'),
    path('disciplinary-cases/', views.disciplinary_case_list_view, name='disciplinary_case_list'),
    path('disciplinary-cases/<int:pk>/edit/', views.disciplinary_case_update_view, name='disciplinary_case_update'),
    path('disciplinary-cases/<int:pk>/delete/', views.disciplinary_case_delete_view, name='disciplinary_case_delete'),
    path('disciplinary-report/', views.disciplinary_report_view, name='disciplinary_report'),

    # Demographics Report
    path('demographics-report/', views.demographics_report_view, name='demographics_report'),

    # Reports List
    path('reports/', views.report_list_view, name='report_list'),

    # Initial Data Setup (for superuser)
    path('setup-data/', views.setup_initial_data, name='setup_initial_data'),

    # Annual Leave Management
    path('annual-leave-reset/', views.annual_leave_reset_view, name='annual_leave_reset'),

    # Notification Management URLs
    path('notifications/', views.notification_list_view, name='notification_list'),
    path('notifications/<int:pk>/', views.notification_detail_view, name='notification_detail'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),

    # NEW: Real-time Notification Count URL (AJAX endpoint)
    path('notifications/unread-count/', views.get_unread_notification_count_view, name='unread_notification_count'),
]
