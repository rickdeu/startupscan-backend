from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class PitchAnalysis(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    INDUSTRY_CHOICES = [
        ('tech', 'Technology'),
        ('health', 'Health'),
        ('finance', 'Finance'),
        ('education', 'Education'),
        ('ecommerce', 'E-commerce'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="User",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status",
    )
    processing_time = models.FloatField(
        null=True, blank=True, verbose_name="Processing time (seconds)"
    )

    startup_name = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Startup Name"
    )
    industry = models.CharField(
        max_length=20,
        choices=INDUSTRY_CHOICES,
        default='tech',
        verbose_name="Industry",
    )
    contact_email = models.EmailField(null=True, blank=True, verbose_name="Contact email")

    text = models.TextField(verbose_name="Pitch Text")
    audio_file = models.FileField(
        upload_to='pitches/audio/%Y/%m/%d/', null=True, blank=True, verbose_name="Audio File"
    )
    video_file = models.FileField(
        upload_to='pitches/video/%Y/%m/%d/', null=True, blank=True, verbose_name="Video File"
    )
    explainer_video_file = models.FileField(
        upload_to='pitches/explainer/%Y/%m/%d/', null=True, blank=True, verbose_name="AI Explainer Video"
    )
    presenter_face_image_file = models.FileField(
        upload_to='pitches/presenter/%Y/%m/%d/', null=True, blank=True, verbose_name="Presenter Face"
    )
    document_file = models.FileField(
        upload_to='pitches/docs/%Y/%m/%d/', null=True, blank=True, verbose_name="Submitted File"
    )
    submission_date = models.DateField(null=True, blank=True, verbose_name="Submission date")

    revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Annual Revenue (AOA)",
    )
    growth_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(-100), MaxValueValidator(1000)],
        verbose_name="Growth Rate (%)",
    )
    profit_margin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Profit Margin (%)",
    )
    burn_rate = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Burn Rate (AOA/month)",
    )

    success_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        null=True,
        blank=True,
        verbose_name="Success Score",
    )
    confidence = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True,
        verbose_name="Analysis Confidence (%)",
    )
    report = models.JSONField(default=dict, verbose_name="Full Report")
    metadata = models.JSONField(default=dict, verbose_name="Technical Metadata")

    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Address")
    user_agent = models.TextField(null=True, blank=True, verbose_name="User Agent")
    model_version = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Model Version"
    )

    class Meta:
        verbose_name = "Pitch Analysis"
        verbose_name_plural = "Pitch Analyses"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['success_score']),
            models.Index(fields=['industry']),
        ]

    def __str__(self):
        name = self.startup_name or f"Analysis #{self.id}"
        return f"{name} - Score: {self.success_score or 'N/A'}"

    def save(self, *args, **kwargs):
        if not self.submission_date:
            self.submission_date = timezone.now().date()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('pitch_results', args=[str(self.id)])

    @property
    def is_completed(self):
        return self.status == 'completed'

    @property
    def financial_health(self):
        if not all([self.revenue, self.growth_rate, self.profit_margin]):
            return None
        try:
            score = (
                float(self.growth_rate) * 0.4 + float(self.profit_margin) * 0.6
            ) * float(self.revenue) / 1_000_000
            return min(max(score, 0), 100)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    def get_file_links(self):
        links = {}
        if self.audio_file:
            links['audio'] = self.audio_file.url
        if self.video_file:
            links['video'] = self.video_file.url
        if self.explainer_video_file:
            links['explainer_video'] = self.explainer_video_file.url
        if self.presenter_face_image_file:
            links['presenter_face'] = self.presenter_face_image_file.url
        if self.document_file:
            links['document'] = self.document_file.url
        return links
