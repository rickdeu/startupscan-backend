from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class PitchAnalysis(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('completed', 'Completo'),
        ('failed', 'Falhou'),
    ]

    INDUSTRY_CHOICES = [
        ('tech', 'Tecnologia'),
        ('health', 'Saúde'),
        ('finance', 'Finanças'),
        ('education', 'Educação'),
        ('ecommerce', 'E-commerce'),
        ('other', 'Outro'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuário",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de criação")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data de atualização")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status",
    )
    processing_time = models.FloatField(
        null=True, blank=True, verbose_name="Tempo de processamento (segundos)"
    )

    startup_name = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Nome da Startup"
    )
    industry = models.CharField(
        max_length=20,
        choices=INDUSTRY_CHOICES,
        default='tech',
        verbose_name="Setor",
    )
    contact_email = models.EmailField(null=True, blank=True, verbose_name="E-mail de contato")

    text = models.TextField(verbose_name="Texto do Pitch")
    audio_file = models.FileField(
        upload_to='pitches/audio/%Y/%m/%d/', null=True, blank=True, verbose_name="Arquivo de Áudio"
    )
    video_file = models.FileField(
        upload_to='pitches/video/%Y/%m/%d/', null=True, blank=True, verbose_name="Arquivo de Vídeo"
    )
    explainer_video_file = models.FileField(
        upload_to='pitches/explainer/%Y/%m/%d/', null=True, blank=True, verbose_name="Vídeo Explicativo IA"
    )
    presenter_face_image_file = models.FileField(
        upload_to='pitches/presenter/%Y/%m/%d/', null=True, blank=True, verbose_name="Rosto do Apresentador"
    )
    document_file = models.FileField(
        upload_to='pitches/docs/%Y/%m/%d/', null=True, blank=True, verbose_name="Ficheiro Submetido"
    )
    submission_date = models.DateField(null=True, blank=True, verbose_name="Data de submissão")

    revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Receita Anual (AOA)",
    )
    growth_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(-100), MaxValueValidator(1000)],
        verbose_name="Taxa de Crescimento (%)",
    )
    profit_margin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Margem de Lucro (%)",
    )
    burn_rate = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Taxa de Queima (AOA/mês)",
    )

    success_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        null=True,
        blank=True,
        verbose_name="Score de Sucesso",
    )
    confidence = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True,
        verbose_name="Confiança da Análise (%)",
    )
    report = models.JSONField(default=dict, verbose_name="Relatório Completo")
    metadata = models.JSONField(default=dict, verbose_name="Metadados Técnicos")

    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Endereço IP")
    user_agent = models.TextField(null=True, blank=True, verbose_name="User Agent")
    model_version = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Versão do Modelo"
    )

    class Meta:
        verbose_name = "Análise de Pitch"
        verbose_name_plural = "Análises de Pitch"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['success_score']),
            models.Index(fields=['industry']),
        ]

    def __str__(self):
        name = self.startup_name or f"Análise #{self.id}"
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
