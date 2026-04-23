from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SubscriptionPlan(models.Model):
    TIER_TRIAL = 'trial'
    TIER_BASIC = 'basic'
    TIER_PRO = 'pro'
    TIER_CHOICES = [
        (TIER_TRIAL, 'Trial'),
        (TIER_BASIC, 'Basic'),
        (TIER_PRO, 'Pro'),
    ]

    INTERVAL_MONTH = 'month'
    INTERVAL_YEAR = 'year'
    INTERVAL_ONCE = 'once'
    INTERVAL_CHOICES = [
        (INTERVAL_MONTH, 'Mensal'),
        (INTERVAL_YEAR, 'Anual'),
        (INTERVAL_ONCE, 'Único (Trial)'),
    ]

    name = models.CharField(max_length=100, verbose_name='Nome')
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, verbose_name='Tier')
    interval = models.CharField(
        max_length=10, choices=INTERVAL_CHOICES,
        default=INTERVAL_MONTH, verbose_name='Intervalo',
    )
    price_usd = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Preço (USD)',
    )
    price_eur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Preço (EUR)',
    )
    price_aoa = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='Preço (AOA)',
    )
    is_active = models.BooleanField(default=True, verbose_name='Ativo')
    trial_days = models.IntegerField(
        default=7, verbose_name='Dias de trial',
        help_text='Apenas relevante para planos Trial',
    )

    # Stripe sync
    stripe_product_id = models.CharField(max_length=100, blank=True, verbose_name='Stripe Product ID')
    stripe_price_id = models.CharField(max_length=100, blank=True, verbose_name='Stripe Price ID')

    # Limites de uso mensal (0 = ilimitado)
    analyses_per_month = models.IntegerField(
        default=3, verbose_name='Análises/mês',
        help_text='0 = ilimitado',
    )
    videos_per_month = models.IntegerField(
        default=0, verbose_name='Vídeos IA/mês',
        help_text='0 = ilimitado',
    )
    investor_interests_per_month = models.IntegerField(
        default=0, verbose_name='Interesses de investidor/mês',
        help_text='0 = ilimitado',
    )
    batch_max_rows = models.IntegerField(
        default=0, verbose_name='Máx. linhas por batch',
        help_text='0 = ilimitado',
    )

    # Funcionalidades booleanas
    gpt_analysis = models.BooleanField(default=False, verbose_name='Análise via GPT')
    audio_upload = models.BooleanField(default=False, verbose_name='Upload de áudio')
    video_upload = models.BooleanField(default=False, verbose_name='Upload de vídeo')
    youtube_url = models.BooleanField(default=False, verbose_name='URL YouTube')
    financial_data = models.BooleanField(default=False, verbose_name='Dados financeiros')
    pdf_report = models.BooleanField(default=False, verbose_name='PDF relatório de análise')
    pdf_investor = models.BooleanField(default=False, verbose_name='PDF pitch para investidor')
    pitch_template_choice = models.BooleanField(default=False, verbose_name='Escolha de template de pitch')
    pitch_gpt = models.BooleanField(default=False, verbose_name='Gerar pitch via GPT')
    pitch_pdf = models.BooleanField(default=False, verbose_name='Exportar pitch PDF')
    batch_analysis = models.BooleanField(default=False, verbose_name='Análise em lote (CSV)')
    investor_dashboard = models.BooleanField(default=False, verbose_name='Dashboard de investidores')
    video_generation = models.BooleanField(default=False, verbose_name='Gerar vídeo explicativo IA')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Plano de Subscrição'
        verbose_name_plural = 'Planos de Subscrição'
        ordering = ['price_usd']

    def __str__(self):
        interval_label = {'month': 'mês', 'year': 'ano', 'once': 'trial'}.get(self.interval, self.interval)
        return f'{self.name} (${self.price_usd}/{interval_label})'

    # Exchange rate fallbacks when EUR/AOA prices are not explicitly set
    _USD_TO_EUR = '0.92'
    _USD_TO_AOA = '912'

    @property
    def price_cents(self):
        return int(self.price_usd * 100)

    @property
    def price_eur_display(self):
        from decimal import Decimal
        if self.price_eur > 0:
            return self.price_eur
        return (self.price_usd * Decimal(self._USD_TO_EUR)).quantize(Decimal('1'))

    @property
    def price_aoa_display(self):
        from decimal import Decimal
        if self.price_aoa > 0:
            return self.price_aoa
        return (self.price_usd * Decimal(self._USD_TO_AOA)).quantize(Decimal('1'))

    def has_feature(self, feature: str) -> bool:
        return bool(getattr(self, feature, False))

    def is_within_limit(self, counter_field: str, current_count: int) -> bool:
        limit = getattr(self, counter_field, 0)
        if limit == 0:
            return True
        return current_count < limit


class Subscription(models.Model):
    STATUS_TRIALING = 'trialing'
    STATUS_ACTIVE = 'active'
    STATUS_PAST_DUE = 'past_due'
    STATUS_CANCELED = 'canceled'
    STATUS_INCOMPLETE = 'incomplete'
    STATUS_INACTIVE = 'inactive'

    STATUS_CHOICES = [
        (STATUS_TRIALING, 'Em trial'),
        (STATUS_ACTIVE, 'Ativa'),
        (STATUS_PAST_DUE, 'Pagamento em atraso'),
        (STATUS_CANCELED, 'Cancelada'),
        (STATUS_INCOMPLETE, 'Incompleta'),
        (STATUS_INACTIVE, 'Inativa'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='subscription', verbose_name='Usuário',
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='subscriptions',
        verbose_name='Plano',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_TRIALING, verbose_name='Status',
    )

    # Stripe
    stripe_customer_id = models.CharField(
        max_length=100, blank=True, unique=True, null=True,
        verbose_name='Stripe Customer ID',
    )
    stripe_subscription_id = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name='Stripe Subscription ID',
    )

    trial_end = models.DateTimeField(null=True, blank=True, verbose_name='Fim do trial')
    current_period_start = models.DateTimeField(null=True, blank=True, verbose_name='Início do período')
    current_period_end = models.DateTimeField(null=True, blank=True, verbose_name='Fim do período')
    cancel_at_period_end = models.BooleanField(default=False, verbose_name='Cancelar no fim do período')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscrição'
        verbose_name_plural = 'Subscrições'

    def __str__(self):
        plan_name = self.plan.name if self.plan else 'Sem plano'
        return f'{self.user.username} – {plan_name} ({self.get_status_display()})'

    @property
    def is_active(self) -> bool:
        if self.status == self.STATUS_TRIALING:
            return self.trial_end is None or self.trial_end > timezone.now()
        return self.status == self.STATUS_ACTIVE

    @property
    def trial_days_left(self) -> int:
        if self.status != self.STATUS_TRIALING or not self.trial_end:
            return 0
        delta = self.trial_end - timezone.now()
        return max(0, delta.days)

    @property
    def plan_tier(self) -> str:
        if self.plan:
            return self.plan.tier
        return SubscriptionPlan.TIER_TRIAL


class MonthlyUsage(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='monthly_usages', verbose_name='Usuário',
    )
    year = models.IntegerField(verbose_name='Ano')
    month = models.IntegerField(verbose_name='Mês')
    analyses_count = models.IntegerField(default=0, verbose_name='Análises realizadas')
    videos_count = models.IntegerField(default=0, verbose_name='Vídeos gerados')
    investor_interests_count = models.IntegerField(default=0, verbose_name='Interesses enviados')

    class Meta:
        verbose_name = 'Uso Mensal'
        verbose_name_plural = 'Usos Mensais'
        unique_together = [('user', 'year', 'month')]

    def __str__(self):
        return f'{self.user.username} – {self.year}/{self.month:02d}'

    @classmethod
    def get_or_create_current(cls, user):
        now = timezone.now()
        obj, _ = cls.objects.get_or_create(
            user=user, year=now.year, month=now.month,
        )
        return obj

    @classmethod
    def increment(cls, user, field: str):
        from django.db.models import F
        obj = cls.get_or_create_current(user)
        cls.objects.filter(pk=obj.pk).update(**{field: F(field) + 1})
        obj.refresh_from_db()
        return obj
