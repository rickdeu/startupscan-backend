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
        (INTERVAL_MONTH, 'Monthly'),
        (INTERVAL_YEAR, 'Yearly'),
        (INTERVAL_ONCE, 'One-time (Trial)'),
    ]

    name = models.CharField(max_length=100, verbose_name='Name')
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, verbose_name='Tier')
    interval = models.CharField(
        max_length=10, choices=INTERVAL_CHOICES,
        default=INTERVAL_MONTH, verbose_name='Interval',
    )
    price_usd = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Price (USD)',
    )
    price_eur = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Price (EUR)',
    )
    price_aoa = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        verbose_name='Price (AOA)',
    )
    is_active = models.BooleanField(default=True, verbose_name='Active')
    trial_days = models.IntegerField(
        default=7, verbose_name='Trial days',
        help_text='Only relevant for Trial plans',
    )

    # Stripe sync
    stripe_product_id = models.CharField(max_length=100, blank=True, verbose_name='Stripe Product ID')
    stripe_price_id = models.CharField(max_length=100, blank=True, verbose_name='Stripe Price ID')

    # Monthly usage limits (0 = unlimited)
    analyses_per_month = models.IntegerField(
        default=3, verbose_name='Analyses/month',
        help_text='0 = unlimited',
    )
    videos_per_month = models.IntegerField(
        default=0, verbose_name='AI videos/month',
        help_text='0 = unlimited',
    )
    investor_interests_per_month = models.IntegerField(
        default=0, verbose_name='Investor interests/month',
        help_text='0 = unlimited',
    )
    batch_max_rows = models.IntegerField(
        default=0, verbose_name='Max rows per batch',
        help_text='0 = unlimited',
    )

    # Boolean features
    gpt_analysis = models.BooleanField(default=False, verbose_name='GPT analysis')
    audio_upload = models.BooleanField(default=False, verbose_name='Audio upload')
    video_upload = models.BooleanField(default=False, verbose_name='Video upload')
    youtube_url = models.BooleanField(default=False, verbose_name='YouTube URL')
    financial_data = models.BooleanField(default=False, verbose_name='Financial data')
    pdf_report = models.BooleanField(default=False, verbose_name='Analysis report PDF')
    pdf_investor = models.BooleanField(default=False, verbose_name='Investor pitch PDF')
    pitch_template_choice = models.BooleanField(default=False, verbose_name='Pitch template choice')
    pitch_gpt = models.BooleanField(default=False, verbose_name='Generate pitch via GPT')
    pitch_pdf = models.BooleanField(default=False, verbose_name='Export pitch PDF')
    batch_analysis = models.BooleanField(default=False, verbose_name='Batch analysis (CSV)')
    investor_dashboard = models.BooleanField(default=False, verbose_name='Investor dashboard')
    video_generation = models.BooleanField(default=False, verbose_name='Generate AI explainer video')
    business_model_canvas = models.BooleanField(default=False, verbose_name='Business Model Canvas in report')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'
        ordering = ['price_usd']

    def __str__(self):
        interval_label = {'month': 'month', 'year': 'year', 'once': 'trial'}.get(self.interval, self.interval)
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
        (STATUS_TRIALING, 'Trialing'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_PAST_DUE, 'Past due'),
        (STATUS_CANCELED, 'Canceled'),
        (STATUS_INCOMPLETE, 'Incomplete'),
        (STATUS_INACTIVE, 'Inactive'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='subscription', verbose_name='User',
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='subscriptions',
        verbose_name='Plan',
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

    trial_end = models.DateTimeField(null=True, blank=True, verbose_name='Trial end')
    current_period_start = models.DateTimeField(null=True, blank=True, verbose_name='Period start')
    current_period_end = models.DateTimeField(null=True, blank=True, verbose_name='Period end')
    cancel_at_period_end = models.BooleanField(default=False, verbose_name='Cancel at period end')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'

    def __str__(self):
        plan_name = self.plan.name if self.plan else 'No plan'
        return f'{self.user.username} - {plan_name} ({self.get_status_display()})'

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
        related_name='monthly_usages', verbose_name='User',
    )
    year = models.IntegerField(verbose_name='Year')
    month = models.IntegerField(verbose_name='Month')
    analyses_count = models.IntegerField(default=0, verbose_name='Analyses performed')
    videos_count = models.IntegerField(default=0, verbose_name='Videos generated')
    investor_interests_count = models.IntegerField(default=0, verbose_name='Interests sent')

    class Meta:
        verbose_name = 'Monthly Usage'
        verbose_name_plural = 'Monthly Usages'
        unique_together = [('user', 'year', 'month')]

    def __str__(self):
        return f'{self.user.username} - {self.year}/{self.month:02d}'

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
