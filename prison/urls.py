from django.urls import path
from . import views
from .views import (
    # ... existing imports ...
    VisitorListView, VisitorCreateView, VisitorUpdateView, VisitorApproveView,
    MedicalRecordListView, MedicalRecordCreateView, MedicalRecordUpdateView, MedicalRecordDetailView,
    IncidentReportListView, IncidentReportCreateView, IncidentReportDetailView,
    ActivityLogListView, # New: Import ActivityLogListView
)


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('prisoners/', views.prisoner_list, name='prisoner_list'),
    path('prisoners/add/', views.add_prisoner, name='add_prisoner'),
    path('prisoners/<int:prisoner_id>/', views.prisoner_detail, name='prisoner_detail'),
    path('prisoners/<int:prisoner_id>/edit/', views.edit_prisoner, name='edit_prisoner'),
    path('prisoners/<int:prisoner_id>/delete/', views.delete_prisoner, name='delete_prisoner'),
    path('prisoners/<int:prisoner_id>/convicted/', views.add_convicted_details, name='add_convicted_details'),
    path('prisoners/<int:prisoner_id>/remand/', views.add_remand_details, name='add_remand_details'),
    path('prisoners/<int:prisoner_id>/convicted/edit/', views.edit_convicted_details, name='edit_convicted_details'),
    path('prisoners/<int:prisoner_id>/remand/edit/', views.edit_remand_details, name='edit_remand_details'),
    path('prisoners/<int:prisoner_id>/transfer/', views.transfer_prisoner, name='transfer_prisoner'),
    path('prisoners/<int:prisoner_id>/reduce-sentence/', views.apply_sentence_reduction, name='apply_sentence_reduction'),
    path('prisoners/<int:prisoner_id>/report/', views.generate_prisoner_report, name='generate_prisoner_report'),
    path('releases/', views.upcoming_releases_report, name='upcoming_releases_report'),
    path('stations/', views.manage_prison_stations, name='manage_prison_stations'),
    path('stations/<int:station_id>/edit/', views.edit_prison_station, name='edit_prison_station'),
    path('stations/<int:station_id>/delete/', views.delete_prison_station, name='delete_prison_station'),
    path('statistics/api/', views.prison_statistics_api, name='prison_statistics_api'),
    path('releases/', views.upcoming_releases_report, name='upcoming_releases_report'),
    path('stations/create/', views.create_prison_station, name='create_prison_station'),
    path('stations/', views.manage_prison_stations, name='manage_prison_stations'),
    path('stations/<int:station_id>/edit/', views.edit_prison_station, name='edit_prison_station'),
    path('stations/<int:station_id>/delete/', views.delete_prison_station, name='delete_prison_station'),
   
    # Visitor URLs
    path('visitors/', VisitorListView.as_view(), name='visitor_list'),
    path('visitors/add/', VisitorCreateView.as_view(), name='visitor_add'),
    path('visitors/<int:pk>/edit/', VisitorUpdateView.as_view(), name='visitor_edit'),
    path('visitors/<int:pk>/approve/', VisitorApproveView.as_view(), name='visitor_approve'),
    path('visitor/<int:pk>/', views.VisitorDetailView.as_view(), name='visitor_detail'),
    # Medical Record URLs
    path('medical-records/', MedicalRecordListView.as_view(), name='medical_record_list'),
    path('medical-records/add/', MedicalRecordCreateView.as_view(), name='medical_record_add'),
    path('medical-records/<int:pk>/', MedicalRecordDetailView.as_view(), name='medical_record_detail'),
    path('medical-records/<int:pk>/edit/', MedicalRecordUpdateView.as_view(), name='medical_record_edit'),
    
    # Inventory URLs
   
 
    
    # Incident Report URLs
    path('incidents/', IncidentReportListView.as_view(), name='incident_report_list'),
    path('incidents/add/', IncidentReportCreateView.as_view(), name='incident_report_add'),
    path('incidents/<int:pk>/', IncidentReportDetailView.as_view(), name='incident_report_detail'),

 # New: Activity Log URL
   path('activity-log/', ActivityLogListView.as_view(), name='activity_log_list'),
]