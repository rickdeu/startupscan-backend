from django import forms
from django.contrib.auth.models import Group, Permission, User

from startupscan_api.models import (
    IdeaPitchSubmission,
    IdeaPublicFeedback,
    InvestorConnectionInterest,
    PitchAnalysis,
    PromptTemplate,
    UserProfile,
)
from subscriptions.models import MonthlyUsage, Subscription, SubscriptionPlan

WIDGET_ATTRS = {"class": "sa-input"}
TEXTAREA_ATTRS = {"class": "sa-input", "rows": 3}
CHECK_ATTRS = {"class": "sa-check"}


def _style(fields):
    for field in fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.update(CHECK_ATTRS)
        elif isinstance(widget, forms.Textarea):
            widget.attrs.update(TEXTAREA_ATTRS)
        elif isinstance(widget, (forms.SelectMultiple, forms.CheckboxSelectMultiple)):
            widget.attrs.update({"class": "sa-check-list"})
        else:
            widget.attrs.update(WIDGET_ATTRS)


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class UserAccountForm(StyledFormMixin, forms.ModelForm):
    """Core account fields + role + Django permission flags (is_staff/is_superuser)."""

    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, required=True, label="Access profile")
    password1 = forms.CharField(
        label="New password", widget=forms.PasswordInput, required=False,
        help_text="Leave blank to keep the current password.",
    )
    password2 = forms.CharField(label="Confirm new password", widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = [
            "username", "email", "first_name", "last_name",
            "is_active", "is_staff", "is_superuser",
        ]

    def __init__(self, *args, require_password=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.require_password = require_password
        if self.instance and self.instance.pk:
            profile = getattr(self.instance, "profile", None)
            self.fields["role"].initial = profile.role if profile else UserProfile.ROLE_GENERAL_PUBLIC

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if self.require_password and not p1:
            raise forms.ValidationError("A password is required to create a new user.")
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Passwords do not match.")
            if len(p1) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()
            UserProfile.objects.update_or_create(
                user=user, defaults={"role": self.cleaned_data["role"]},
            )
        return user


class UserPermissionsForm(StyledFormMixin, forms.Form):
    """Grant/revoke groups and individual permissions for one user."""

    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(), required=False,
        widget=forms.CheckboxSelectMultiple, label="Groups",
    )
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related("content_type").order_by(
            "content_type__app_label", "codename",
        ),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Individual permissions",
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        initial = kwargs.pop("initial", {}) or {}
        if user is not None:
            initial.setdefault("groups", user.groups.all())
            initial.setdefault("user_permissions", user.user_permissions.all())
        super().__init__(*args, initial=initial, **kwargs)

    def save(self):
        self.user.groups.set(self.cleaned_data["groups"])
        self.user.user_permissions.set(self.cleaned_data["user_permissions"])
        return self.user


class GroupForm(StyledFormMixin, forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related("content_type").order_by(
            "content_type__app_label", "codename",
        ),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Group
        fields = ["name", "permissions"]


class PitchAnalysisForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PitchAnalysis
        fields = [
            "user", "status", "startup_name", "industry", "contact_email", "text",
            "revenue", "growth_rate", "profit_margin", "burn_rate",
            "success_score", "confidence",
        ]


class IdeaPitchSubmissionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = IdeaPitchSubmission
        fields = [
            "user", "status", "model_source", "startup_name", "one_liner",
            "problem", "solution", "target_customer", "market_size",
            "business_model", "competitive_advantage", "traction", "team",
            "funding_goal", "use_of_funds", "call_to_action",
        ]


class IdeaPublicFeedbackForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = IdeaPublicFeedback
        fields = ["submission", "user", "stars", "endorsed", "comment"]


class InvestorConnectionInterestForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = InvestorConnectionInterest
        fields = [
            "analysis", "investor", "entrepreneur", "status",
            "investor_message", "entrepreneur_reply",
        ]


class SubscriptionPlanForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "name", "tier", "interval", "price_usd", "price_eur", "price_aoa",
            "is_active", "trial_days",
            "analyses_per_month", "videos_per_month", "investor_interests_per_month", "batch_max_rows",
            "local_analysis", "gpt_analysis", "deepseek_analysis", "ollama_analysis",
            "audio_upload", "video_upload", "youtube_url", "financial_data",
            "pdf_report", "pdf_investor", "pitch_template_choice", "pitch_gpt", "pitch_pdf",
            "batch_analysis", "investor_dashboard", "video_generation", "business_model_canvas",
        ]


class SubscriptionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Subscription
        fields = [
            "user", "plan", "status", "trial_end",
            "current_period_start", "current_period_end", "cancel_at_period_end",
        ]
        widgets = {
            "trial_end": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "current_period_start": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "current_period_end": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class MonthlyUsageForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = MonthlyUsage
        fields = ["user", "year", "month", "analyses_count", "videos_count", "investor_interests_count"]


class PromptTemplateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PromptTemplate
        fields = ["engine", "purpose", "is_active", "content"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # StyledFormMixin._style() forces every Textarea to rows=3, so this
        # has to be re-applied after super().__init__() runs. Large,
        # distraction-free plain-text panel (see .sa-prompt-editor in
        # admin.css) — deliberately not a rich-text/WYSIWYG editor: this
        # content is sent verbatim to an LLM API, where HTML formatting
        # would corrupt the prompt.
        self.fields["content"].widget.attrs.update({
            "class": "sa-input sa-prompt-editor",
            "rows": 26,
            "spellcheck": "false",
        })
