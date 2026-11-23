from django.urls import path
from analytics import views

urlpatterns = [
    # Telemetry and CV endpoints
    path('api/interviews/<uuid:interview_id>/tech-check/', views.save_tech_check_view, name='save_tech_check'),
    path('api/interviews/<uuid:interview_id>/calibration/', views.save_baseline_calibration_view, name='save_calibration'),
    path('api/interviews/<uuid:interview_id>/telemetry/', views.save_posture_telemetry_batch_view, name='save_posture_telemetry'),
    
    # Phase 7: Scorecard and PDF Report endpoints
    path('interviews/<uuid:interview_id>/report/', views.interview_report_view, name='interview_report'),
    path('interviews/<uuid:interview_id>/report/pdf/', views.interview_report_pdf_view, name='interview_report_pdf'),
]


