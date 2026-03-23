from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class UserProfile(models.Model):
    ROLE_EMPREENDEDOR = "empreendedor"
    ROLE_INVESTIDOR = "investidor"
    ROLE_PUBLICO = "publico_geral"
    ROLE_ANALISTA = "analista"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_EMPREENDEDOR, "Empreendedor"),
        (ROLE_INVESTIDOR, "Investidor"),
        (ROLE_PUBLICO, "Público em geral"),
        (ROLE_ANALISTA, "Analista"),
        (ROLE_ADMIN, "Administrador"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Usuário",
    )
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default=ROLE_PUBLICO,
        verbose_name="Perfil de acesso",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuário"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class PitchAnalysis(models.Model):
    # Status choices
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('completed', 'Completo'),
        ('failed', 'Falhou'),
    ]
    
    # Categoria da startup (opcional)
    INDUSTRY_CHOICES = [
        ('tech', 'Tecnologia'),
        ('health', 'Saúde'),
        ('finance', 'Finanças'),
        ('education', 'Educação'),
        ('ecommerce', 'E-commerce'),
        ('other', 'Outro'),
    ]

    # Relacionamento com usuário
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Usuário"
    )
    
    # Metadados da análise
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de criação"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Data de atualização"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    processing_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Tempo de processamento (segundos)"
    )
    
    # Informações da startup
    startup_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Nome da Startup"
    )
    industry = models.CharField(
        max_length=20,
        choices=INDUSTRY_CHOICES,
        default='tech',
        verbose_name="Setor"
    )
    contact_email = models.EmailField(
        null=True,
        blank=True,
        verbose_name="E-mail de contato"
    )
    
    # Dados do pitch
    text = models.TextField(
        verbose_name="Texto do Pitch"
    )
    audio_file = models.FileField(
        upload_to='pitches/audio/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Arquivo de Áudio"
    )
    video_file = models.FileField(
        upload_to='pitches/video/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Arquivo de Vídeo"
    )
    explainer_video_file = models.FileField(
        upload_to='pitches/explainer/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Vídeo Explicativo IA"
    )
    presenter_face_image_file = models.FileField(
        upload_to='pitches/presenter/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Rosto do Apresentador"
    )
    document_file = models.FileField(
        upload_to='pitches/docs/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Ficheiro Submetido"
    )
    submission_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de submissão"
    )
    
    # Dados financeiros
    revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Receita Anual (AOA)"
    )
    growth_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(-100), MaxValueValidator(1000)],
        verbose_name="Taxa de Crescimento (%)"
    )
    profit_margin = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Margem de Lucro (%)"
    )
    burn_rate = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Taxa de Queima (AOA/mês)"
    )
    
    # Resultados da análise
    success_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        null=True,
        blank=True,
        verbose_name="Score de Sucesso"
    )
    confidence = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True,
        verbose_name="Confiança da Análise (%)"
    )
    report = models.JSONField(
        default=dict,
        verbose_name="Relatório Completo"
    )
    metadata = models.JSONField(
        default=dict,
        verbose_name="Metadados Técnicos"
    )
    
    # Informações técnicas
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Endereço IP"
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name="User Agent"
    )
    model_version = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Versão do Modelo"
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
        """Override save para adicionar lógica personalizada"""
        if not self.submission_date:
            self.submission_date = timezone.now().date()
        
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """URL para a página de resultados"""
        from django.urls import reverse
        return reverse('pitch_results', args=[str(self.id)])

    @property
    def is_completed(self):
        return self.status == 'completed'

    @property
    def financial_health(self):
        """Calcula uma métrica simples de saúde financeira"""
        if not all([self.revenue, self.growth_rate, self.profit_margin]):
            return None
            
        try:
            score = (float(self.growth_rate) * 0.4 + 
                    float(self.profit_margin) * 0.6) * float(self.revenue) / 1000000
            return min(max(score, 0), 100)
        except:
            return None

    def get_file_links(self):
        """Retorna links para os arquivos de mídia"""
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


class IdeaPitchSubmission(models.Model):
    """
    Submissão de ideia para geração posterior de pitch completo.
    """

    STATUS_CHOICES = [
        ("draft", "Rascunho"),
        ("generated", "Pitch gerado"),
    ]

    MODEL_SOURCE_CHOICES = [
        ("local", "Local"),
        ("gpt", "GPT"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuário",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    startup_name = models.CharField(max_length=120, verbose_name="Nome da startup")
    one_liner = models.CharField(max_length=300, blank=True, default="")
    problem = models.TextField(verbose_name="Problema")
    solution = models.TextField(verbose_name="Solução")
    target_customer = models.TextField(verbose_name="Cliente-alvo")
    market_size = models.TextField(blank=True, default="")
    business_model = models.TextField(verbose_name="Modelo de negócio")
    competitive_advantage = models.TextField(blank=True, default="")
    traction = models.TextField(blank=True, default="")
    team = models.TextField(blank=True, default="")
    funding_goal = models.TextField(blank=True, default="")
    use_of_funds = models.TextField(blank=True, default="")
    call_to_action = models.TextField(blank=True, default="")

    model_source = models.CharField(
        max_length=10,
        choices=MODEL_SOURCE_CHOICES,
        default="local",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    generated_pitch = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Submissão de Ideia para Pitch"
        verbose_name_plural = "Submissões de Ideia para Pitch"

    def __str__(self):
        return f"{self.startup_name} ({self.get_status_display()})"


class InvestorConnectionInterest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_REVIEWING = "reviewing"
    STATUS_CONNECTED = "connected"
    STATUS_REJECTED = "rejected"
    STATUS_WITHDRAWN = "withdrawn"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendente"),
        (STATUS_REVIEWING, "Em análise"),
        (STATUS_CONNECTED, "Conexão iniciada"),
        (STATUS_REJECTED, "Recusado"),
        (STATUS_WITHDRAWN, "Retirado"),
    ]

    analysis = models.ForeignKey(
        PitchAnalysis,
        on_delete=models.CASCADE,
        related_name="connection_interests",
        verbose_name="Análise de interesse",
    )
    investor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_connection_interests",
        verbose_name="Investidor",
    )
    entrepreneur = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_connection_interests",
        verbose_name="Empreendedor",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="Status da conexão",
    )
    investor_message = models.TextField(blank=True, default="", verbose_name="Mensagem do investidor")
    entrepreneur_reply = models.TextField(blank=True, default="", verbose_name="Resposta do empreendedor")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Interesse de Conexão"
        verbose_name_plural = "Interesses de Conexão"
        constraints = [
            models.UniqueConstraint(fields=["analysis", "investor"], name="unique_interest_per_investor_analysis")
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        startup = self.analysis.startup_name or f"Análise #{self.analysis_id}"
        return f"{self.investor.username} -> {startup} ({self.status})"


class IdeaPublicFeedback(models.Model):
    """
    Interações do público geral com ideias publicadas na plataforma.
    """

    submission = models.ForeignKey(
        IdeaPitchSubmission,
        on_delete=models.CASCADE,
        related_name="public_feedbacks",
        verbose_name="Ideia",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="idea_public_feedbacks",
        verbose_name="Utilizador",
    )
    stars = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Estrelas (1 a 5)",
    )
    endorsed = models.BooleanField(
        default=False,
        verbose_name="Apoia esta ideia",
    )
    comment = models.TextField(blank=True, default="", verbose_name="Comentário público")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Feedback Público de Ideia"
        verbose_name_plural = "Feedbacks Públicos de Ideias"
        constraints = [
            models.UniqueConstraint(fields=["submission", "user"], name="unique_public_feedback_per_user_submission")
        ]
        indexes = [
            models.Index(fields=["stars"]),
            models.Index(fields=["endorsed"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.submission.startup_name} ({self.stars} estrelas)"