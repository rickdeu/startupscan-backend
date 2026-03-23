from django.urls import path
from .views import (
    BatchAnalysisResultsView,
    BatchAnalysisStatusView,
    DashboardView,
    IdeaPitchDetailView,
    IdeaPitchPDFView,
    InvestorDashboardView,
    IdeaPitchBuilderView,
    ModelTrainingProgressView,
    ModelManagementView,
    PitchFormView,
    PitchExplainerVideoGenerateView,
    PitchExplainerVideoProgressView,
    PitchReportPDFView,
    PitchResultsView,
    StartupPitchAnalyzer,
    BatchAnalysisView,
    ModelRetrainView,
    TrainingStatusView,
    register_view
)
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('analyze/', StartupPitchAnalyzer.as_view(), name='pitch-analyzer'),
    path('model/retrain/', ModelRetrainView.as_view(), name='model-retrain'),
    path('training/status/<str:task_id>/', TrainingStatusView.as_view(), name='training-status'),
    path('batch/analyze/', BatchAnalysisView.as_view(), name='batch-analyze'),
    path('batch/status/<uuid:batch_id>/', BatchAnalysisStatusView.as_view(), name='batch-status'),
    path('batch/results/<uuid:batch_id>/', BatchAnalysisResultsView.as_view(), name='batch-results'),
    path('models/', ModelManagementView.as_view(), name='model_management'),
    path('models/training/progress/<str:job_id>/', ModelTrainingProgressView.as_view(), name='model_training_progress'),
    path('investors/', InvestorDashboardView.as_view(), name='investor_dashboard'),

    path('', DashboardView.as_view(), name='dashboard'),
    path('pitch/builder/', IdeaPitchBuilderView.as_view(), name='idea_pitch_builder'),
    path('pitch/builder/<int:submission_id>/', IdeaPitchDetailView.as_view(), name='idea_pitch_detail'),
    path('pitch/builder/<int:submission_id>/pdf/', IdeaPitchPDFView.as_view(), name='idea_pitch_pdf'),
    path('analyze/form/', PitchFormView.as_view(), name='pitch_form'),
    path('results/<int:analysis_id>/', PitchResultsView.as_view(), name='pitch_results'),
    path('results/<int:analysis_id>/pdf/', PitchReportPDFView.as_view(), name='pitch_report_pdf'),
    path('results/<int:analysis_id>/video/generate/', PitchExplainerVideoGenerateView.as_view(), name='pitch_explainer_video_generate'),
    path('results/<int:analysis_id>/video/progress/<str:job_id>/', PitchExplainerVideoProgressView.as_view(), name='pitch_explainer_video_progress'),
    #path('login/', auth_views.LoginView.as_view(), name='login'),
    path('login/', auth_views.LoginView.as_view(template_name='analyzer/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('register/', register_view, name='register'),
]