import json
from django.contrib import admin
from django.utils.html import format_html
from startupscan_api.models import PitchAnalysis


@admin.register(PitchAnalysis)
class PitchAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'startup_name',
        'user_display',
        'status_badge',
        'success_score_display',
        'financial_metrics',
        'created_at_short',
        'analysis_actions',
    )
    list_display_links = ('id', 'startup_name')
    list_filter = ('status', 'industry', 'created_at', 'success_score')
    search_fields = ('startup_name', 'text', 'user__username', 'contact_email', 'id')
    list_per_page = 25
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    readonly_fields = (
        'created_at',
        'updated_at',
        'processing_time',
        'ip_address',
        'user_agent',
        'model_version',
        'analysis_duration',
        'file_links',
    )
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('status', 'startup_name', 'user', 'contact_email', 'industry'),
        }),
        ('Conteúdo do Pitch', {
            'fields': ('text', 'audio_file', 'video_file', 'file_links', 'submission_date'),
        }),
        ('Dados Financeiros', {
            'fields': ('revenue', 'growth_rate', 'profit_margin', 'burn_rate'),
        }),
        ('Resultados da Análise', {
            'fields': ('success_score', 'confidence', 'report', 'metadata'),
        }),
        ('Metadados Técnicos', {
            'fields': (
                'created_at',
                'updated_at',
                'processing_time',
                'analysis_duration',
                'ip_address',
                'user_agent',
                'model_version',
            ),
            'classes': ('collapse',),
        }),
    )
    save_on_top = True
    actions = ['mark_as_completed', 'reprocess_analysis']
    radio_fields = {'status': admin.HORIZONTAL, 'industry': admin.VERTICAL}

    def user_display(self, obj):
        return obj.user.username if obj.user else 'Anônimo'
    user_display.short_description = 'Usuário'
    user_display.admin_order_field = 'user__username'

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
        }
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 10px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display(),
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def success_score_display(self, obj):
        if obj.success_score is None:
            return '-'
        color = 'green' if obj.success_score >= 7 else 'orange' if obj.success_score >= 5 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.success_score,
        )
    success_score_display.short_description = 'Score'
    success_score_display.admin_order_field = 'success_score'

    def financial_metrics(self, obj):
        return format_html(
            'AOA {}<br>{}% Cresc.<br>{}% Margem',
            f"{obj.revenue:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            obj.growth_rate,
            obj.profit_margin,
        )
    financial_metrics.short_description = 'Métricas Financeiras'
    financial_metrics.admin_order_field = 'revenue'

    def created_at_short(self, obj):
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_short.short_description = 'Criado em'
    created_at_short.admin_order_field = 'created_at'

    def analysis_actions(self, obj):
        return format_html(
            '<a href="{}" class="button" style="padding: 2px 5px; background: #417690; color: white; text-decoration: none;">Ver</a>&nbsp;'
            '<a href="{}" class="button" style="padding: 2px 5px; background: #447e9b; color: white; text-decoration: none;">Editar</a>',
            obj.get_absolute_url(),
            f"{obj.id}/change/",
        )
    analysis_actions.short_description = 'Ações'

    def file_links(self, obj):
        links = []
        if obj.audio_file:
            links.append(f'<a href="{obj.audio_file.url}" target="_blank">Áudio</a>')
        if obj.video_file:
            links.append(f'<a href="{obj.video_file.url}" target="_blank">Vídeo</a>')
        return format_html(' | '.join(links)) if links else '-'
    file_links.short_description = 'Arquivos'

    def analysis_duration(self, obj):
        if obj.processing_time:
            return f"{obj.processing_time:.2f} segundos"
        return '-'
    analysis_duration.short_description = 'Duração da Análise'

    def _format_json(self, data):
        return json.dumps(data, indent=2, ensure_ascii=False)

    @admin.action(description='Marcar como completo')
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f"{updated} análises marcadas como completas.")

    @admin.action(description='Reprocessar análise')
    def reprocess_analysis(self, request, queryset):
        from startupscan_api.tasks import reprocess_pitch_analysis
        for analysis in queryset:
            reprocess_pitch_analysis.delay(analysis.id)
        self.message_user(request, f"{queryset.count()} análises enviadas para reprocessamento.")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(user=request.user)
        return qs

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == 'completed':
            return [f.name for f in self.model._meta.fields] + ['file_links']
        return super().get_readonly_fields(request, obj)

    def get_exclude(self, request, obj=None):
        excluded = list(super().get_exclude(request, obj) or [])
        if not request.user.is_superuser:
            excluded += ['metadata', 'model_version', 'ip_address']
        return excluded
