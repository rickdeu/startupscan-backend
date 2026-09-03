import logging
import os
import tempfile
import uuid
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from startupscan_api.i18n import build_ui_text, normalize_ui_language
from startupscan_api.modeling import analyze_with_gpt, ensure_report_dict
from startupscan_api.models import InvestorConnectionInterest, PitchAnalysis
from startupscan_api.roles import (
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLE_ENTREPRENEUR,
    ROLE_INVESTOR,
    get_user_role,
)
from startupscan_api.services.model_training import ensure_model_exists, predict_pitch_score
from startupscan_api.services.pitch_builder import (
    PITCH_DESIGN_MODE_AUTO,
    export_pitch_pdf,
    generate_pitch_from_idea,
    get_pitch_design_mode_choices,
    get_pitch_design_template_choices,
)
from startupscan_api.services.pitch_input import extract_text_from_uploaded_file, merge_pitch_text
from startupscan_api.services.report_export import export_analysis_pdf
from startupscan_api.utils import generate_interpretable_report, prepare_features
from .helpers import (
    _infer_error_field,
    _is_meaningful_pitch_text,
    _resolve_pitch_design_selection,
    _safe_exception_message,
)
from .jobs import _video_generation_cache_key
from .mixins import RoleRequiredMixin
from subscriptions.mixins import SubscriptionGate, check_feature_access, check_limit_access

logger = logging.getLogger(__name__)


def _ui_text_for_request(request):
    return build_ui_text(normalize_ui_language(getattr(request, "ui_language", None)))


def _build_pitch_payload_from_analysis(analysis: PitchAnalysis) -> dict:
    # NOTE: startupscan_api/services/pitch/generator.py's local fallback
    # (_local_pitch_fallback) that ultimately consumes this payload is a
    # rich but Portuguese-only prose generator with no language parameter
    # of its own. Regenerating analysis.report in another language here
    # would feed non-Portuguese fragments into its Portuguese connective
    # sentences, producing worse mixing than today. Keep this payload (and
    # its fallbacks) in Portuguese until that generator gets its own
    # multi-language support; only report_export.py's technical report is
    # fully language-aware end to end for now.
    report = analysis.report or {}
    investor_pitch = report.get("investor_pitch", {}) if isinstance(report, dict) else {}
    strengths = report.get("strengths", []) if isinstance(report, dict) else []
    weaknesses = report.get("weaknesses", []) if isinstance(report, dict) else []
    recommendations = report.get("recommendations", []) if isinstance(report, dict) else []
    summary = str(report.get("summary", "") if isinstance(report, dict) else "").strip()

    startup_name = analysis.startup_name or f"Startup {analysis.id}"
    industry_label = (
        analysis.get_industry_display() if hasattr(analysis, "get_industry_display") else (analysis.industry or "mercado")
    )
    one_liner = (
        summary.split(".")[0].strip()
        if summary
        else f"{startup_name} resolve problemas críticos no setor {industry_label}."
    )

    def _join_list(values, fallback):
        values = values if isinstance(values, list) else []
        cleaned = [str(v).strip() for v in values if str(v).strip()]
        return " ".join(cleaned[:3]) if cleaned else fallback

    revenue = float(analysis.revenue or 0)
    growth_rate = float(analysis.growth_rate or 0)
    profit_margin = float(analysis.profit_margin or 0)
    success_score = float(analysis.success_score or 0)

    funding_goal_aoa = max(8_000_000, int(max(revenue * 0.55, 0)))
    funding_goal = f"AOA {funding_goal_aoa:,.0f} para acelerar escala e execução comercial."

    return {
        "startup_name": startup_name,
        "one_liner": one_liner,
        "problem": _join_list(weaknesses, f"Baixa eficiência e oportunidade de modernização no setor {industry_label}."),
        "solution": _join_list(strengths, "Solução com foco em eficiência operacional, crescimento e previsibilidade."),
        "target_customer": f"Empresas e decisores estratégicos no setor {industry_label}.",
        "market_size": investor_pitch.get("investment_thesis", "") or "Mercado em expansão com espaço para liderança regional.",
        "business_model": "Modelo orientado a geração de receita recorrente e expansão comercial disciplinada.",
        "competitive_advantage": _join_list(strengths, "Execução rápida, leitura de métricas e adaptação contínua ao mercado."),
        "traction": (
            f"Score {success_score:.1f}/10, receita AOA {revenue:,.0f}, "
            f"crescimento {growth_rate:.1f}% e margem {profit_margin:.1f}%."
        ),
        "team": "Equipe focada em execução e melhoria contínua com orientação a metas de crescimento.",
        "funding_goal": investor_pitch.get("suggested_ticket", "") or funding_goal,
        "use_of_funds": _join_list(
            investor_pitch.get("capital_use_plan", []),
            "Produto, aquisição de clientes e fortalecimento da operação para escala.",
        ),
        "call_to_action": _join_list(
            recommendations,
            "Proposta para avançar para reunião de investimento com plano de execução detalhado.",
        ),
    }


class PitchFormView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_ENTREPRENEUR, ROLE_ANALYST, ROLE_ADMIN}

    def get(self, request):
        return render(request, 'analyzer/pitch_form.html', {
            'default_date': datetime.now().strftime('%Y-%m-%d'),
            'max_file_size': 50,
            'industries': PitchAnalysis.INDUSTRY_CHOICES,
            'form_data': {'model_source': 'local'},
        })

    def post(self, request):
        try:
            startup_name = request.POST.get("startup_name", "").strip()
            contact_email = request.POST.get("contact_email", "").strip()
            industry = request.POST.get("industry", "tech").strip() or "tech"

            raw_text = request.POST.get('text', '').strip()
            text_file = request.FILES.get("text_file")
            youtube_url = request.POST.get("youtube_url", "").strip()
            extracted_text = extract_text_from_uploaded_file(text_file)
            text = merge_pitch_text(raw_text, extracted_text, youtube_url)

            if not text or len(text) < 100:
                t = _ui_text_for_request(request)
                messages.error(
                    request,
                    t.get("msg_pitch_text_too_short", "The pitch text must be at least 100 characters long."),
                    extra_tags=f"text:{t.get('msg_text_too_short_tag', 'Text too short')}",
                )
                return self._render_form_with_data(request)

            if not _is_meaningful_pitch_text(text):
                t = _ui_text_for_request(request)
                not_meaningful_tag = t.get("msg_pitch_text_not_meaningful_tag", "Text doesn't make sense")
                messages.error(
                    request,
                    t.get(
                        "msg_pitch_text_not_meaningful",
                        "The pitch text doesn't look like a real description of the startup. "
                        "Please write a meaningful description, without repetition or random text.",
                    ),
                    extra_tags=f"text:{not_meaningful_tag}",
                )
                return self._render_form_with_data(request)

            if text_file:
                allowed = (".txt", ".md", ".csv", ".pdf", ".docx")
                if not (text_file.name or "").lower().endswith(allowed):
                    t = _ui_text_for_request(request)
                    messages.error(
                        request,
                        t.get("msg_invalid_text_document", "Invalid text document. Use TXT, MD, CSV, PDF, or DOCX."),
                        extra_tags=f"text_file:{t.get('msg_invalid_format_tag', 'Invalid format')}",
                    )
                    return self._render_form_with_data(request)

            audio_file = request.FILES.get('audio')
            video_file = request.FILES.get('video')

            if audio_file:
                if not self._is_valid_audio(audio_file):
                    t = _ui_text_for_request(request)
                    messages.error(
                        request,
                        t.get("msg_invalid_audio_format", "Invalid audio format. Use MP3, WAV, or OGG."),
                        extra_tags=f"audio_file:{t.get('msg_invalid_format_tag', 'Invalid format')}",
                    )
                    return self._render_form_with_data(request)
                if audio_file.size > 50 * 1024 * 1024:
                    t = _ui_text_for_request(request)
                    messages.error(
                        request,
                        t.get("msg_audio_file_too_large", "The audio file cannot exceed 50MB."),
                        extra_tags=f"audio_file:{t.get('msg_size_exceeded_tag', 'Size exceeded')}",
                    )
                    return self._render_form_with_data(request)

            if video_file:
                if not self._is_valid_video(video_file):
                    t = _ui_text_for_request(request)
                    messages.error(
                        request,
                        t.get("msg_invalid_video_format", "Invalid video format. Use MP4, MOV, or AVI."),
                        extra_tags=f"video_file:{t.get('msg_invalid_format_tag', 'Invalid format')}",
                    )
                    return self._render_form_with_data(request)
                if video_file.size > 100 * 1024 * 1024:
                    t = _ui_text_for_request(request)
                    messages.error(
                        request,
                        t.get("msg_video_file_too_large", "The video file cannot exceed 100MB."),
                        extra_tags=f"video_file:{t.get('msg_size_exceeded_tag', 'Size exceeded')}",
                    )
                    return self._render_form_with_data(request)

            if youtube_url and not youtube_url.startswith(("https://www.youtube.com/", "https://youtu.be/")):
                t = _ui_text_for_request(request)
                messages.error(
                    request,
                    t.get("msg_invalid_youtube_link", "Invalid YouTube link."),
                    extra_tags=f"youtube_url:{t.get('msg_invalid_url_tag', 'Invalid URL')}",
                )
                return self._render_form_with_data(request)

            try:
                financial_data = {
                    'revenue': float(request.POST.get('revenue', 0)),
                    'growth_rate': float(request.POST.get('growth_rate', 0)),
                    'profit_margin': float(request.POST.get('profit_margin', 0)),
                }
                if financial_data['revenue'] < 0:
                    raise ValueError("Receita não pode ser negativa")
                if not (-100 <= financial_data['growth_rate'] <= 1000):
                    raise ValueError("Taxa de crescimento deve estar entre -100% e 1000%")
                if not (0 <= financial_data['profit_margin'] <= 100):
                    raise ValueError("Margem de lucro deve estar entre 0% e 100%")
            except ValueError as e:
                detail = f"Dados financeiros inválidos: {str(e)}"
                field = _infer_error_field(detail)
                messages.error(request, detail, extra_tags=f"{field}:{detail}")
                return self._render_form_with_data(request)

            model_source = str(request.POST.get("model_source", "local")).strip().lower()
            if model_source not in {"local", "gpt"}:
                model_source = "local"

            if request.user.is_authenticated and get_user_role(request.user) not in (ROLE_ADMIN, ROLE_ANALYST):
                gate = self._check_pitch_gates(
                    request, model_source=model_source,
                    has_audio=bool(audio_file), has_video=bool(video_file),
                    has_youtube=bool(youtube_url),
                )
                if gate is not None:
                    return gate

            model = None
            if model_source == "local":
                model = ensure_model_exists()
                if model is None:
                    logger.critical("Modelo de análise não disponível")
                    return render(request, 'analyzer/error.html', {
                        'error': 'Sistema temporariamente indisponível. Por favor, tente mais tarde.'
                    }, status=503)

            try:
                with self._create_temp_file_manager(audio_file, video_file) as file_paths:
                    audio_path, video_path = file_paths
                    pitch_data = {
                        'text': text,
                        'audio_path': audio_path,
                        'video_path': video_path,
                        'youtube_url': youtube_url,
                        'submission_date': request.POST.get('submission_date'),
                    }
                    features, metadata = prepare_features(pitch_data, financial_data)
                    metadata["analysis_engine_requested"] = model_source
                    metadata["startup_name"] = startup_name
                    metadata["industry"] = industry
                    metadata["analysis_context_id"] = str(uuid.uuid4())
                    prediction = None
                    report = None
                    engine_used = model_source
                    report_language = normalize_ui_language(getattr(request, "ui_language", None))

                    if model_source == "gpt":
                        prediction, report, engine_used = analyze_with_gpt(
                            text, financial_data, metadata, language=report_language,
                        )

                    if prediction is None:
                        if model is None:
                            model = ensure_model_exists()
                        if model is None:
                            raise RuntimeError("Modelo local indisponível para fallback")
                        prediction = predict_pitch_score(
                            model=model, pitch_data=pitch_data,
                            financial_data=financial_data, precomputed_features=features,
                        )
                        report = generate_interpretable_report(prediction, metadata, language=report_language)
                        engine_used = "local"

                    prediction = max(0, min(10, float(prediction)))
                    report = ensure_report_dict(report, prediction)
                    metadata["analysis_engine_used"] = engine_used
                    metadata["sources"] = {
                        "text_file_name": text_file.name if text_file else "",
                        "youtube_url": youtube_url,
                        "has_audio": bool(audio_file),
                        "has_video": bool(video_file),
                    }

                    analysis = self._save_analysis(
                        request=request, startup_name=startup_name, industry=industry,
                        contact_email=contact_email, text=text, text_file=text_file,
                        audio_file=audio_file, video_file=video_file,
                        financial_data=financial_data, prediction=prediction,
                        report=report, metadata=metadata,
                    )
                    if request.user.is_authenticated and get_user_role(request.user) not in (ROLE_ADMIN, ROLE_ANALYST):
                        from subscriptions.models import MonthlyUsage
                        MonthlyUsage.increment(request.user, 'analyses_count')
                    return redirect('pitch_results', analysis_id=analysis.id)

            except Exception as e:
                logger.error(f"Erro durante processamento: {str(e)}", exc_info=True)
                detail = _safe_exception_message(e)
                field = _infer_error_field(detail)
                user_msg = f"Erro durante o processamento: {detail}"
                messages.error(request, user_msg, extra_tags=f"{field}:{user_msg}")
                return self._render_form_with_data(request)

        except Exception as e:
            logger.critical(f"Erro inesperado: {str(e)}", exc_info=True)
            detail = _safe_exception_message(e)
            field = _infer_error_field(detail)
            user_msg = f"Erro inesperado na validação: {detail}"
            messages.error(request, user_msg, extra_tags=f"{field}:{user_msg}")
            return self._render_form_with_data(request)

    def _is_valid_audio(self, audio_file):
        valid_extensions = ['.mp3', '.wav', '.ogg', '.webm', '.m4a']
        ext = os.path.splitext(audio_file.name)[1].lower()
        return ext in valid_extensions

    def _is_valid_video(self, video_file):
        valid_extensions = ['.mp4', '.mov', '.avi', '.webm']
        ext = os.path.splitext(video_file.name)[1].lower()
        return ext in valid_extensions

    def _create_temp_file_manager(self, audio_file, video_file):
        class _TempFileManager:
            def __init__(self, audio, video):
                self.audio = audio
                self.video = video
                self.audio_path = None
                self.video_path = None

            def __enter__(self):
                fs = FileSystemStorage(location=tempfile.gettempdir())
                if self.audio:
                    audio_ext = os.path.splitext(self.audio.name)[1].lower() or ".bin"
                    self.audio_path = fs.save(f"pitch_audio_{tempfile.gettempprefix()}{audio_ext}", self.audio)
                if self.video:
                    video_ext = os.path.splitext(self.video.name)[1].lower() or ".bin"
                    self.video_path = fs.save(f"pitch_video_{tempfile.gettempprefix()}{video_ext}", self.video)
                return (self.audio_path, self.video_path)

            def __exit__(self, exc_type, exc_val, exc_tb):
                fs = FileSystemStorage(location=tempfile.gettempdir())
                if self.audio_path and fs.exists(self.audio_path):
                    fs.delete(self.audio_path)
                if self.video_path and fs.exists(self.video_path):
                    fs.delete(self.video_path)

        return _TempFileManager(audio_file, video_file)

    def _save_analysis(self, request, startup_name, industry, contact_email, text,
                       text_file, audio_file, video_file, financial_data, prediction, report, metadata):
        valid_industries = {choice[0] for choice in PitchAnalysis.INDUSTRY_CHOICES}
        if industry not in valid_industries:
            industry = "other"
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

        return PitchAnalysis.objects.create(
            user=request.user if request.user.is_authenticated else None,
            startup_name=startup_name or None,
            industry=industry,
            contact_email=contact_email or None,
            text=text,
            document_file=text_file,
            audio_file=audio_file,
            video_file=video_file,
            revenue=financial_data['revenue'],
            growth_rate=financial_data['growth_rate'],
            profit_margin=financial_data['profit_margin'],
            success_score=float(prediction),
            report=report,
            metadata=metadata,
            ip_address=ip,
        )

    def _check_pitch_gates(self, request, *, model_source, has_audio, has_video, has_youtube):
        allowed, _ = check_limit_access(request.user, 'analyses_per_month', 'analyses_count')
        if not allowed:
            messages.warning(request, _ui_text_for_request(request).get(
                "msg_monthly_analyses_limit_reached",
                "Monthly analyses limit reached. Upgrade to continue.",
            ))
            return redirect('subscription_plans')

        if model_source == 'gpt':
            allowed, _ = check_feature_access(request.user, 'gpt_analysis')
            if not allowed:
                messages.warning(request, _ui_text_for_request(request).get(
                    "msg_gpt_analysis_requires_upgrade", "GPT analysis requires a higher plan.",
                ))
                return redirect('subscription_plans')

        if has_audio:
            allowed, _ = check_feature_access(request.user, 'audio_upload')
            if not allowed:
                messages.warning(request, _ui_text_for_request(request).get(
                    "msg_audio_upload_requires_upgrade", "Audio upload requires a higher plan.",
                ))
                return redirect('subscription_plans')

        if has_video:
            allowed, _ = check_feature_access(request.user, 'video_upload')
            if not allowed:
                messages.warning(request, _ui_text_for_request(request).get(
                    "msg_video_upload_requires_upgrade", "Video upload requires a higher plan.",
                ))
                return redirect('subscription_plans')

        if has_youtube:
            allowed, _ = check_feature_access(request.user, 'youtube_url')
            if not allowed:
                messages.warning(request, _ui_text_for_request(request).get(
                    "msg_youtube_requires_upgrade", "YouTube processing requires a higher plan.",
                ))
                return redirect('subscription_plans')

        return None

    def _render_form_with_data(self, request):
        form_data = {
            'startup_name': request.POST.get('startup_name', ''),
            'industry': request.POST.get('industry', 'tech'),
            'contact_email': request.POST.get('contact_email', ''),
            'text': request.POST.get('text', ''),
            'youtube_url': request.POST.get('youtube_url', ''),
            'revenue': request.POST.get('revenue', ''),
            'growth_rate': request.POST.get('growth_rate', ''),
            'profit_margin': request.POST.get('profit_margin', ''),
            'model_source': request.POST.get('model_source', 'local'),
        }
        errors = {}
        general_errors = []
        storage = messages.get_messages(request)
        for message in storage:
            msg_text = str(message)
            if hasattr(message, "extra_tags") and message.extra_tags and ":" in message.extra_tags:
                field, error_msg = message.extra_tags.split(":", 1)
                field = (field or "general").strip()
                if field == "general":
                    general_errors.append(error_msg.strip() or msg_text)
                else:
                    errors[field] = error_msg.strip() or msg_text
            else:
                general_errors.append(msg_text)

        return render(request, 'analyzer/pitch_form.html', {
            'form_data': form_data,
            'errors': errors,
            'general_errors': general_errors,
            'default_date': datetime.now().strftime('%Y-%m-%d'),
            'max_file_size': 50,
            'industries': PitchAnalysis.INDUSTRY_CHOICES,
        })


class PitchResultsView(RoleRequiredMixin, View):
    allowed_roles = {ROLE_ENTREPRENEUR, ROLE_INVESTOR, ROLE_ANALYST, ROLE_ADMIN}

    def get(self, request, analysis_id):
        analysis = PitchAnalysis.objects.get(id=analysis_id)
        user_role = get_user_role(request.user)
        interests_qs = InvestorConnectionInterest.objects.filter(analysis=analysis).select_related("investor", "entrepreneur")

        my_interest = None
        if request.user.is_authenticated:
            my_interest = interests_qs.filter(investor=request.user).first()

        can_send_interest_on_pitch = (
            request.user.is_authenticated
            and user_role in {ROLE_INVESTOR, ROLE_ANALYST, ROLE_ADMIN}
            and bool(analysis.user_id)
            and analysis.user_id != request.user.id
        )
        can_view_received_interests = (
            request.user.is_authenticated
            and (
                user_role in {ROLE_ADMIN, ROLE_ANALYST}
                or (user_role == ROLE_ENTREPRENEUR and analysis.user_id == request.user.id)
            )
        )
        received_interests = list(interests_qs.order_by("-updated_at")) if can_view_received_interests else []

        last_pitch_meta = (analysis.metadata or {}).get("last_generated_pitch_payload", {})
        if not isinstance(last_pitch_meta, dict):
            last_pitch_meta = {}

        selected_video_mode = str((analysis.metadata or {}).get("explainer_video_mode", "auto") or "auto").strip().lower()
        if selected_video_mode not in {"auto", "did_only", "local_only", "canva_capcut"}:
            selected_video_mode = "auto"

        selected_presenter_gender_choice = str(
            (analysis.metadata or {}).get("explainer_video_gender_choice", "auto") or "auto"
        ).strip().lower()
        if selected_presenter_gender_choice not in {"auto", "male", "female"}:
            selected_presenter_gender_choice = "auto"

        design_template_choices = get_pitch_design_template_choices()
        selected_pitch_design_mode, selected_pitch_design_template = _resolve_pitch_design_selection(
            request,
            default_mode=str(last_pitch_meta.get("design_mode", PITCH_DESIGN_MODE_AUTO)),
            default_template=str(last_pitch_meta.get("design_template", design_template_choices[0][0] if design_template_choices else "orbit")),
        )

        active_video_job_id = (request.GET.get("video_job_id", "") or "").strip()
        if not active_video_job_id:
            active_video_job_id = str((analysis.metadata or {}).get("explainer_video_job_id", "") or "").strip()

        active_video_job = None
        if active_video_job_id:
            state = cache.get(_video_generation_cache_key(active_video_job_id))
            if (
                state
                and int(state.get("analysis_id") or 0) == int(analysis.id)
                and str(state.get("status", "")).upper() in {"PENDING", "RUNNING"}
            ):
                active_video_job = state

        return render(request, 'analyzer/result.html', {
            'analysis': analysis,
            'user_role': user_role,
            'my_interest': my_interest,
            'can_send_interest_on_pitch': can_send_interest_on_pitch,
            'can_view_received_interests': can_view_received_interests,
            'received_interests': received_interests,
            'active_video_job_id': active_video_job_id,
            'active_video_job': active_video_job or {},
            'selected_video_mode': selected_video_mode,
            'selected_presenter_gender_choice': selected_presenter_gender_choice,
            'pitch_design_mode_choices': get_pitch_design_mode_choices(),
            'pitch_design_template_choices': design_template_choices,
            'selected_pitch_design_mode': selected_pitch_design_mode,
            'selected_pitch_design_template': selected_pitch_design_template,
        })


class PitchReportPDFView(SubscriptionGate, RoleRequiredMixin, View):
    allowed_roles = {ROLE_ENTREPRENEUR, ROLE_INVESTOR, ROLE_ANALYST, ROLE_ADMIN}
    required_feature = 'pdf_report'

    def get(self, request, analysis_id):
        analysis = PitchAnalysis.objects.get(id=analysis_id)
        if (
            get_user_role(request.user) not in (ROLE_ADMIN, ROLE_ANALYST)
            and analysis.user
            and request.user.is_authenticated
            and analysis.user_id != request.user.id
        ):
            return redirect("dashboard")

        media_root = settings.MEDIA_ROOT
        try:
            os.makedirs(media_root, exist_ok=True)
        except OSError:
            media_root = os.path.join(settings.BASE_DIR, "media")
            os.makedirs(media_root, exist_ok=True)

        reports_dir = os.path.join(media_root, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        output_path = os.path.join(reports_dir, f"analysis_report_{analysis.id}.pdf")
        report_language = normalize_ui_language(getattr(request, "ui_language", None))
        include_canvas, _ = check_feature_access(request.user, 'business_model_canvas')
        export_analysis_pdf(
            analysis, output_path, language=report_language,
            include_business_canvas=include_canvas,
        )

        return FileResponse(
            open(output_path, "rb"),
            as_attachment=True,
            filename=f"relatorio_pitch_{analysis.id}.pdf",
            content_type="application/pdf",
        )


class PitchInvestorPDFView(SubscriptionGate, RoleRequiredMixin, View):
    allowed_roles = {ROLE_ENTREPRENEUR, ROLE_INVESTOR, ROLE_ANALYST, ROLE_ADMIN}
    required_feature = 'pdf_investor'

    def get(self, request, analysis_id):
        analysis = get_object_or_404(PitchAnalysis, id=analysis_id)
        if (
            get_user_role(request.user) not in (ROLE_ADMIN, ROLE_ANALYST)
            and analysis.user
            and request.user.is_authenticated
            and analysis.user_id != request.user.id
        ):
            return redirect("dashboard")

        try:
            payload = _build_pitch_payload_from_analysis(analysis)
            model_source = (request.GET.get("model_source", "") or "").strip().lower()
            if model_source not in {"local", "gpt"}:
                import os as _os
                model_source = "gpt" if _os.getenv("OPENAI_API_KEY") else "local"

            design_mode, design_template = _resolve_pitch_design_selection(
                request, default_mode=PITCH_DESIGN_MODE_AUTO, default_template="orbit"
            )
            report_language = normalize_ui_language(getattr(request, "ui_language", None))
            pitch_payload = generate_pitch_from_idea(payload, model_source=model_source, language=report_language)

            media_root = settings.MEDIA_ROOT
            try:
                os.makedirs(media_root, exist_ok=True)
            except OSError:
                media_root = os.path.join(settings.BASE_DIR, "media")
                os.makedirs(media_root, exist_ok=True)

            pitch_dir = os.path.join(media_root, "analysis_pitches")
            os.makedirs(pitch_dir, exist_ok=True)
            startup_name = analysis.startup_name or f"startup_{analysis.id}"
            safe_name = "".join(ch if ch.isalnum() else "_" for ch in startup_name).strip("_").lower() or "startup"
            output_path = os.path.join(pitch_dir, f"pitch_resultado_{safe_name}_{analysis.id}.pdf")

            export_pitch_pdf(pitch_payload, output_path, design_mode=design_mode, manual_template=design_template,
                              language=report_language)

            metadata = analysis.metadata or {}
            metadata["last_generated_pitch_payload"] = {
                "generated_at": timezone.now().isoformat(),
                "engine_used": pitch_payload.get("engine_used", model_source),
                "slide_count": len((pitch_payload.get("pitch_deck") or [])),
                "narrative_uniqueness_key": pitch_payload.get("narrative_uniqueness_key", ""),
                "design_mode": design_mode,
                "design_template": design_template,
            }
            analysis.metadata = metadata
            analysis.save(update_fields=["metadata", "updated_at"])

            return FileResponse(
                open(output_path, "rb"),
                as_attachment=True,
                filename=f"pitch_investidor_{safe_name}_{analysis.id}.pdf",
                content_type="application/pdf",
            )
        except Exception as exc:
            logger.error("Falha ao gerar pitch PDF a partir do resultado: %s", str(exc), exc_info=True)
            messages.error(request, f"Falha ao gerar pitch PDF: {_safe_exception_message(exc)}")
            return redirect("pitch_results", analysis_id=analysis.id)
