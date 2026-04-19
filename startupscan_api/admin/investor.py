from django.contrib import admin
from startupscan_api.models import InvestorConnectionInterest


@admin.register(InvestorConnectionInterest)
class InvestorConnectionInterestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "analysis",
        "investor",
        "entrepreneur",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "created_at", "updated_at")
    search_fields = (
        "analysis__startup_name",
        "investor__username",
        "entrepreneur__username",
        "investor_message",
        "entrepreneur_reply",
    )
    readonly_fields = ("created_at", "updated_at", "responded_at")
