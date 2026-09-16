from .api import (
    BatchAnalysisResultsView,
    BatchAnalysisStatusView,
    BatchAnalysisView,
    ModelRetrainView,
    StartupPitchAnalyzer,
    TrainingStatusView,
)
from .auth import RoleBasedLoginView, RoleHomeView, register_view, set_ui_language
from .dashboard import DashboardView, LandingView
from .idea import (
    IdeaPitchBuilderView,
    IdeaPitchDetailView,
    IdeaPitchPDFView,
    PublicIdeaDetailView,
    PublicIdeaFeedbackView,
    PublicIdeasView,
)
from .investor import (
    ConnectionInterestUpdateView,
    ConnectionsHubView,
    InvestorDashboardView,
    InvestorInterestCreateView,
)
from .model_management import ModelManagementView, ModelTrainingProgressView
from .pitch import PitchFormView, PitchInvestorPDFView, PitchReportPDFView, PitchResultsView
from .pitch_video import (
    PitchExplainerVideoGenerateView,
    PitchExplainerVideoProgressView,
    PitchPresenterGenderDetectView,
)
from .sample_data import generate_sample_data

__all__ = [
    "BatchAnalysisResultsView",
    "BatchAnalysisStatusView",
    "BatchAnalysisView",
    "ConnectionInterestUpdateView",
    "ConnectionsHubView",
    "DashboardView",
    "LandingView",
    "IdeaPitchBuilderView",
    "IdeaPitchDetailView",
    "IdeaPitchPDFView",
    "InvestorDashboardView",
    "InvestorInterestCreateView",
    "ModelManagementView",
    "ModelRetrainView",
    "ModelTrainingProgressView",
    "PitchExplainerVideoGenerateView",
    "PitchExplainerVideoProgressView",
    "PitchFormView",
    "PitchInvestorPDFView",
    "PitchPresenterGenderDetectView",
    "PitchReportPDFView",
    "PitchResultsView",
    "PublicIdeaDetailView",
    "PublicIdeaFeedbackView",
    "PublicIdeasView",
    "RoleBasedLoginView",
    "RoleHomeView",
    "StartupPitchAnalyzer",
    "TrainingStatusView",
    "generate_sample_data",
    "register_view",
    "set_ui_language",
]
