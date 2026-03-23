from django.urls import path
from .views import (
    BatchAnalysisResultsView,
    BatchAnalysisStatusView,
    DashboardView,
    InvestorDashboardView,
    ModelManagementView,
    PitchFormView,
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
    path('investors/', InvestorDashboardView.as_view(), name='investor_dashboard'),

    path('', DashboardView.as_view(), name='dashboard'),
    path('analyze/form/', PitchFormView.as_view(), name='pitch_form'),
    path('results/<int:analysis_id>/', PitchResultsView.as_view(), name='pitch_results'),
    #path('login/', auth_views.LoginView.as_view(), name='login'),
    path('login/', auth_views.LoginView.as_view(template_name='analyzer/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('register/', register_view, name='register'),
]