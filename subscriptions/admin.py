from django.contrib import admin
from django.utils.html import format_html
from .models import MonthlyUsage, Subscription, SubscriptionPlan
from .stripe_sync import sync_plan_to_stripe


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'tier', 'interval', 'price_usd', 'is_active',
        'analyses_per_month', 'stripe_price_id_short',
    ]
    list_filter = ['tier', 'interval', 'is_active']
    search_fields = ['name', 'stripe_product_id', 'stripe_price_id']
    readonly_fields = ['stripe_product_id', 'stripe_price_id', 'created_at', 'updated_at']

    fieldsets = [
        ('Identificação', {
            'fields': ['name', 'tier', 'interval', 'price_usd', 'is_active', 'trial_days'],
        }),
        ('Stripe (sincronização automática)', {
            'fields': ['stripe_product_id', 'stripe_price_id'],
            'classes': ['collapse'],
        }),
        ('Limites de uso mensal', {
            'fields': [
                'analyses_per_month', 'videos_per_month',
                'investor_interests_per_month', 'batch_max_rows',
            ],
            'description': '0 = ilimitado',
        }),
        ('Funcionalidades incluídas', {
            'fields': [
                'gpt_analysis', 'audio_upload', 'video_upload', 'youtube_url',
                'financial_data', 'pdf_report', 'pdf_investor',
                'pitch_template_choice', 'pitch_gpt', 'pitch_pdf',
                'batch_analysis', 'investor_dashboard', 'video_generation',
            ],
        }),
        ('Datas', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    actions = ['sync_to_stripe']

    @admin.display(description='Stripe Price ID')
    def stripe_price_id_short(self, obj):
        if obj.stripe_price_id:
            return format_html(
                '<code title="{}">{}</code>',
                obj.stripe_price_id,
                obj.stripe_price_id[:20] + '…' if len(obj.stripe_price_id) > 20 else obj.stripe_price_id,
            )
        return '—'

    @admin.action(description='Sincronizar com Stripe')
    def sync_to_stripe(self, request, queryset):
        synced = 0
        for plan in queryset:
            if sync_plan_to_stripe(plan):
                synced += 1
        self.message_user(request, f'{synced} plano(s) sincronizado(s) com o Stripe.')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        synced = sync_plan_to_stripe(obj)
        if synced:
            self.message_user(request, f'Plano "{obj.name}" sincronizado com Stripe.')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'plan', 'status', 'trial_days_left_display',
        'current_period_end', 'cancel_at_period_end',
    ]
    list_filter = ['status', 'plan__tier', 'cancel_at_period_end']
    search_fields = ['user__username', 'user__email', 'stripe_customer_id', 'stripe_subscription_id']
    readonly_fields = ['stripe_customer_id', 'stripe_subscription_id', 'created_at', 'updated_at']
    raw_id_fields = ['user', 'plan']

    @admin.display(description='Dias trial restantes')
    def trial_days_left_display(self, obj):
        if obj.status == Subscription.STATUS_TRIALING:
            return obj.trial_days_left
        return '—'


@admin.register(MonthlyUsage)
class MonthlyUsageAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'year', 'month', 'analyses_count',
        'videos_count', 'investor_interests_count',
    ]
    list_filter = ['year', 'month']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['user', 'year', 'month']
