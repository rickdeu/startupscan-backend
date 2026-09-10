from django.urls import path

from .views.activity import ActivityLogDeleteView, ActivityLogDetailView, ActivityLogListView
from .views.dashboard import DashboardView
from .views.groups import (
    GroupCreateView,
    GroupDeleteView,
    GroupDetailView,
    GroupListView,
    GroupUpdateView,
)
from .views.idea import (
    IdeaFeedbackCreateView,
    IdeaFeedbackDeleteView,
    IdeaFeedbackDetailView,
    IdeaFeedbackListView,
    IdeaFeedbackUpdateView,
    IdeaSubmissionCreateView,
    IdeaSubmissionDeleteView,
    IdeaSubmissionDetailView,
    IdeaSubmissionListView,
    IdeaSubmissionUpdateView,
)
from .views.investor import (
    InvestorInterestCreateView,
    InvestorInterestDeleteView,
    InvestorInterestDetailView,
    InvestorInterestListView,
    InvestorInterestUpdateView,
)
from .views.pitch import (
    PitchAnalysisCreateView,
    PitchAnalysisDeleteView,
    PitchAnalysisDetailView,
    PitchAnalysisListView,
    PitchAnalysisUpdateView,
)
from .views.subscriptions import (
    PlanCreateView,
    PlanDeleteView,
    PlanDetailView,
    PlanListView,
    PlanUpdateView,
    SubscriptionCreateView,
    SubscriptionDeleteView,
    SubscriptionDetailView,
    SubscriptionListView,
    SubscriptionUpdateView,
    UsageCreateView,
    UsageDeleteView,
    UsageDetailView,
    UsageListView,
    UsageUpdateView,
)
from .views.users import (
    UserCreateView,
    UserDeleteView,
    UserDetailView,
    UserEditView,
    UserListView,
)

app_name = "superadmin"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),

    # Users & permissions
    path("users/", UserListView.as_view(), name="user_list"),
    path("users/new/", UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user_detail"),
    path("users/<int:pk>/edit/", UserEditView.as_view(), name="user_edit"),
    path("users/<int:pk>/delete/", UserDeleteView.as_view(), name="user_delete"),

    # Groups (permission sets)
    path("groups/", GroupListView.as_view(), name="group_list"),
    path("groups/new/", GroupCreateView.as_view(), name="group_create"),
    path("groups/<int:pk>/", GroupDetailView.as_view(), name="group_detail"),
    path("groups/<int:pk>/edit/", GroupUpdateView.as_view(), name="group_edit"),
    path("groups/<int:pk>/delete/", GroupDeleteView.as_view(), name="group_delete"),

    # Pitch analyses
    path("pitch-analyses/", PitchAnalysisListView.as_view(), name="pitch_list"),
    path("pitch-analyses/new/", PitchAnalysisCreateView.as_view(), name="pitch_create"),
    path("pitch-analyses/<int:pk>/", PitchAnalysisDetailView.as_view(), name="pitch_detail"),
    path("pitch-analyses/<int:pk>/edit/", PitchAnalysisUpdateView.as_view(), name="pitch_edit"),
    path("pitch-analyses/<int:pk>/delete/", PitchAnalysisDeleteView.as_view(), name="pitch_delete"),

    # Idea pitch submissions
    path("ideas/", IdeaSubmissionListView.as_view(), name="idea_list"),
    path("ideas/new/", IdeaSubmissionCreateView.as_view(), name="idea_create"),
    path("ideas/<int:pk>/", IdeaSubmissionDetailView.as_view(), name="idea_detail"),
    path("ideas/<int:pk>/edit/", IdeaSubmissionUpdateView.as_view(), name="idea_edit"),
    path("ideas/<int:pk>/delete/", IdeaSubmissionDeleteView.as_view(), name="idea_delete"),

    # Idea public feedback
    path("idea-feedback/", IdeaFeedbackListView.as_view(), name="idea_feedback_list"),
    path("idea-feedback/new/", IdeaFeedbackCreateView.as_view(), name="idea_feedback_create"),
    path("idea-feedback/<int:pk>/", IdeaFeedbackDetailView.as_view(), name="idea_feedback_detail"),
    path("idea-feedback/<int:pk>/edit/", IdeaFeedbackUpdateView.as_view(), name="idea_feedback_edit"),
    path("idea-feedback/<int:pk>/delete/", IdeaFeedbackDeleteView.as_view(), name="idea_feedback_delete"),

    # Investor connection interests
    path("investor-interests/", InvestorInterestListView.as_view(), name="investor_interest_list"),
    path("investor-interests/new/", InvestorInterestCreateView.as_view(), name="investor_interest_create"),
    path("investor-interests/<int:pk>/", InvestorInterestDetailView.as_view(), name="investor_interest_detail"),
    path("investor-interests/<int:pk>/edit/", InvestorInterestUpdateView.as_view(), name="investor_interest_edit"),
    path("investor-interests/<int:pk>/delete/", InvestorInterestDeleteView.as_view(), name="investor_interest_delete"),

    # Subscription plans
    path("plans/", PlanListView.as_view(), name="plan_list"),
    path("plans/new/", PlanCreateView.as_view(), name="plan_create"),
    path("plans/<int:pk>/", PlanDetailView.as_view(), name="plan_detail"),
    path("plans/<int:pk>/edit/", PlanUpdateView.as_view(), name="plan_edit"),
    path("plans/<int:pk>/delete/", PlanDeleteView.as_view(), name="plan_delete"),

    # Subscriptions
    path("subscriptions/", SubscriptionListView.as_view(), name="subscription_list"),
    path("subscriptions/new/", SubscriptionCreateView.as_view(), name="subscription_create"),
    path("subscriptions/<int:pk>/", SubscriptionDetailView.as_view(), name="subscription_detail"),
    path("subscriptions/<int:pk>/edit/", SubscriptionUpdateView.as_view(), name="subscription_edit"),
    path("subscriptions/<int:pk>/delete/", SubscriptionDeleteView.as_view(), name="subscription_delete"),

    # Monthly usage
    path("usage/", UsageListView.as_view(), name="usage_list"),
    path("usage/new/", UsageCreateView.as_view(), name="usage_create"),
    path("usage/<int:pk>/", UsageDetailView.as_view(), name="usage_detail"),
    path("usage/<int:pk>/edit/", UsageUpdateView.as_view(), name="usage_edit"),
    path("usage/<int:pk>/delete/", UsageDeleteView.as_view(), name="usage_delete"),

    # Activity log (operations audit trail)
    path("activity/", ActivityLogListView.as_view(), name="activity_list"),
    path("activity/<int:pk>/", ActivityLogDetailView.as_view(), name="activity_detail"),
    path("activity/<int:pk>/delete/", ActivityLogDeleteView.as_view(), name="activity_delete"),
]
