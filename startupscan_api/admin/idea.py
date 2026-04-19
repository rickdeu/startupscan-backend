from django.contrib import admin
from startupscan_api.models import IdeaPublicFeedback


@admin.register(IdeaPublicFeedback)
class IdeaPublicFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "user", "stars", "endorsed", "created_at", "updated_at")
    list_filter = ("stars", "endorsed", "created_at")
    search_fields = ("submission__startup_name", "user__username", "comment")
    readonly_fields = ("created_at", "updated_at")
