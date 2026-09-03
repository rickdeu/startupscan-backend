from django import forms
from django.db import OperationalError, ProgrammingError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from startupscan_api.roles import (
    ROLE_CHOICES_REGISTRATION,
    ROLE_GENERAL_PUBLIC,
    normalize_role,
    translated_role_choices,
)
from startupscan_api.models import UserProfile

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    profile_role = forms.ChoiceField(
        choices=ROLE_CHOICES_REGISTRATION,
        required=True,
        initial=ROLE_GENERAL_PUBLIC,
        label="Access profile",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "profile_role", "password1", "password2"]

    def __init__(self, *args, ui_text=None, **kwargs):
        super().__init__(*args, **kwargs)
        if ui_text:
            self.fields["profile_role"].choices = translated_role_choices(
                ROLE_CHOICES_REGISTRATION, ui_text
            )
            self.fields["profile_role"].label = ui_text.get("user_profile", self.fields["profile_role"].label)

    def save(self, commit=True):
        user = super(RegisterForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        selected_role = normalize_role(self.cleaned_data.get("profile_role"))
        
        if commit:
            user.save()
            try:
                UserProfile.objects.update_or_create(
                    user=user,
                    defaults={"role": selected_role},
                )
            except (OperationalError, ProgrammingError):
                # Migration not applied yet in this environment.
                pass
        return user