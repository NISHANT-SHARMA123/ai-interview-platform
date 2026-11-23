from django.urls import path
from interviews import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('interviews/create/', views.create_interview_view, name='create_interview'),
    path('interviews/<uuid:interview_id>/', views.interview_room_shell_view, name='interview_room'),
    path('interviews/<uuid:interview_id>/delete/', views.delete_interview_view, name='delete_interview'),
    
    # AI Interview Orchestration & Speech Endpoints (Phase 5)
    path('api/interviews/<uuid:interview_id>/state/', views.interview_state_api, name='interview_state_api'),
    path('api/interviews/<uuid:interview_id>/start/', views.start_interview_api, name='start_interview_api'),
    path('api/interviews/<uuid:interview_id>/answer/', views.submit_answer_api, name='submit_answer_api'),
    path('api/interviews/<uuid:interview_id>/hint/', views.hint_question_api, name='hint_question_api'),
]
