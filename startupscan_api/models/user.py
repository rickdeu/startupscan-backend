from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_ENTREPRENEUR = "entrepreneur"
    ROLE_INVESTOR = "investor"
    ROLE_GENERAL_PUBLIC = "general_public"
    ROLE_ANALYST = "analyst"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_ENTREPRENEUR, "Entrepreneur"),
        (ROLE_INVESTOR, "Investor"),
        (ROLE_GENERAL_PUBLIC, "General public"),
        (ROLE_ANALYST, "Analyst"),
        (ROLE_ADMIN, "Administrator"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="User",
    )
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default=ROLE_GENERAL_PUBLIC,
        verbose_name="Access profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
