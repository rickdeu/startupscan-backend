import os
import json
import logging
import tempfile
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.shortcuts import render, redirect
from django.views import View
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.contrib.auth import login
from startupscan_api.forms import RegisterForm
from startupscan_api.models import PitchAnalysis
from startupscan_api.services.model_training import (
    ensure_model_exists,
    predict_pitch_score,
    train_model_task,
)
from startupscan_api.modeling import analyze_with_gpt, ensure_report_dict
from startupscan_api.util.file_management import TempFileManager
from startupscan_api.services.model_registry import (
    get_active_model_name,
    get_meta_path,
    get_metrics_path,
    get_model_path,
    set_active_model,
)
from startupscan_api.services.pitch_input import extract_text_from_uploaded_file, merge_pitch_text
from startupscan_api.services.report_export import export_analysis_pdf

import joblib
from celery.result import AsyncResult
from django.core.management import call_command
from django.db.models import Avg, Count, Max
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.http import FileResponse

from .utils import (
    prepare_features,
    generate_interpretable_report
)

logger = logging.getLogger(__name__)


def _safe_slug_model_name(raw_name):
    name = (raw_name or "").strip().lower()
    sanitized = []
    for ch in name:
        if ch.isalnum() or ch in {"-", "_"}:
            sanitized.append(ch)
        else:
            sanitized.append("-")
    cleaned = "".join(sanitized).strip("-_")
    if not cleaned:
        cleaned = "pitch-model"
    if not cleaned.endswith(".pkl"):
        cleaned = f"{cleaned}.pkl"
    return cleaned


def _read_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json_file(path, payload):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _list_available_models():
    os.makedirs(settings.AI_MODELS_DIR, exist_ok=True)
    active_model = get_active_model_name()
    models = []

    for file_path in sorted(Path(settings.AI_MODELS_DIR).glob("*.pkl")):
        model_name = file_path.name
        metrics = _read_json_file(get_metrics_path(model_name))
        meta = _read_json_file(get_meta_path(model_name))
        consistency = metrics.get("consistency_accuracy_pct")
        cv_r2 = metrics.get("cv_r2")
        models.append(
            {
                "name": model_name,
                "display_name": meta.get("display_name", model_name.replace(".pkl", "").replace("-", " ").title()),
                "description": meta.get("description", ""),
                "is_active": model_name == active_model,
                "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                "updated_at": datetime.fromtimestamp(file_path.stat().st_mtime),
                "metrics": metrics,
                "consistency_accuracy_pct": consistency if consistency is not None else None,
                "cv_r2_pct": round(float(cv_r2) * 100, 2) if cv_r2 is not None else None,
            }
        )
    return models


def _run_training_for_model(model_name, dataset_source="default"):
    model_path = get_model_path(model_name)
    cmd_args = ["--model-output", str(model_path)]

    if dataset_source == "enhanced":
        pitches = Path(settings.DATA_DIR) / "pitches_dataset_enhanced.csv"
        financials = Path(settings.DATA_DIR) / "financials_dataset_enhanced.csv"
        if pitches.exists() and financials.exists():
            cmd_args.extend(["--pitches-data", str(pitches), "--financials-data", str(financials)])

    call_command("train_model", *cmd_args)
    return model_path


class StartupPitchAnalyzer(APIView):
    """
    Endpoint para análise multimodal de pitches de startups
    """
    
    def post(self, request):
        try:
            # Extrair dados da requisição
            text = request.data.get('text', '')
            text_file = request.FILES.get('text_file')
            audio_file = request.FILES.get('audio')
            video_file = request.FILES.get('video')
            youtube_url = (request.data.get("youtube_url", "") or "").strip()
            financial_data = request.data.get('financial_data', {})
            model_source = str(request.data.get("model_source", "local")).strip().lower()
            if model_source not in {"local", "gpt"}:
                model_source = "local"

            extracted_text = extract_text_from_uploaded_file(text_file)
            text = merge_pitch_text(text, extracted_text, youtube_url)
            if not text:
                return Response(
                    {"error": "Pitch text not provided. Send text or upload a document."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # 2. Processar arquivos temporários (context manager recomendado)
            with TempFileManager(audio_file, video_file) as file_paths:
                audio_path, video_path = file_paths
                
                # 3. Preparar dados para análise
                pitch_data = {
                    'text': text,
                    'audio_path': audio_path,
                    'video_path': video_path,
                    'youtube_url': youtube_url,
                }
                
                # 4. Extrair features
                features, metadata = prepare_features(pitch_data, financial_data)
                metadata["analysis_engine_requested"] = model_source

                prediction = None
                report = None
                engine_used = model_source

                # 5. Fazer previsão por GPT quando solicitado
                if model_source == "gpt":
                    prediction, report, engine_used = analyze_with_gpt(text, financial_data, metadata)

                # 6. Fallback para modelo local treinado
                if prediction is None:
                    model = ensure_model_exists()
                    if model is None:
                        return Response(
                            {'error': 'Model not available and could not be trained'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE
                        )
                    prediction = predict_pitch_score(
                        model=model,
                        pitch_data=pitch_data,
                        financial_data=financial_data,
                        precomputed_features=features,
                    )
                    report = generate_interpretable_report(prediction, metadata)
                    engine_used = "local"

                report = ensure_report_dict(report, prediction)
                metadata["analysis_engine_used"] = engine_used
                metadata["sources"] = {
                    "text_file_name": text_file.name if text_file else "",
                    "youtube_url": youtube_url,
                    "has_audio": bool(audio_file),
                    "has_video": bool(video_file),
                }
                
                return Response({
                    'success_score': float(prediction),
                    'category_scores': report.get("category_scores", {}),
                    'report': report,
                    'metadata': metadata,
                    'engine_used': engine_used,
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing pitch: {str(e)}", exc_info=True)
            return Response(
                {'error': 'An error occurred during analysis'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )





class ModelRetrainView(APIView):
    """Endpoint apenas para disparar o retreinamento em background"""
    
    def post(self, request):
        try:
            # Execução síncrona no ambiente atual.
            result = train_model_task()
            task_id = result.get("task_id") if isinstance(result, dict) else None

            return Response(
                {
                    "message": "Model training executed",
                    "task_id": task_id,
                    "result": result,
                    "status_endpoint": f"/training/status/{task_id}/" if task_id else None
                },
                status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




class TrainingStatusView(APIView):
    """Endpoint para verificar status do treinamento"""
    
    def get(self, request, task_id):
        try:
            if not task_id or str(task_id).lower() in {"none", "null"}:
                return Response(
                    {
                        "task_id": task_id,
                        "status": "COMPLETED",
                        "ready": True,
                        "result": {"message": "Training was executed synchronously"}
                    },
                    status=status.HTTP_200_OK
                )

            task = AsyncResult(task_id)
            
            response = {
                "task_id": task.id,
                "status": task.status,
                "ready": task.ready()
            }
            
            if task.failed():
                response["error"] = str(task.result)
            elif task.successful():
                response["result"] = task.result
                
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning("Training status backend unavailable for task %s: %s", task_id, str(e))
            return Response(
                {
                    "task_id": task_id,
                    "status": "UNAVAILABLE",
                    "ready": False,
                    "error": "Task backend unavailable in current runtime"
                },
                status=status.HTTP_200_OK
            )





import pandas as pd
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.conf import settings
import uuid
import os
from .tasks import process_batch_analysis
from .serializers import BatchAnalysisSerializer

class BatchAnalysisView(APIView):
    """Endpoint para análise em lote de múltiplos pitches"""
    
    def post(self, request):
        try:
            # 1. Validar entrada
            serializer = BatchAnalysisSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            file = serializer.validated_data['file']
            
            # 2. Criar ID único para o lote
            batch_id = str(uuid.uuid4())
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'batch_analysis')
            os.makedirs(temp_dir, exist_ok=True)
            
            # 3. Salvar arquivo temporário
            temp_file_path = os.path.join(temp_dir, f"{batch_id}.csv")
            with open(temp_file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            cache_key = f'batch_analysis:{batch_id}'
            # 4. Armazenar metadados iniciais no cache (expira em 24h)
            cache.set(cache_key, {
                'status': 'PENDING',
                'total_items': 0,
                'processed_items': 0,
                'results_file': None,
                'task_id': None
            }, 86400)  # 24 horas

            # 5. Iniciar tarefa assíncrona, com fallback síncrono sem broker
            execution_mode = "async"
            try:
                task = process_batch_analysis.delay(temp_file_path, batch_id)
            except Exception:
                logger.warning(
                    "Celery broker unavailable. Running batch analysis synchronously.",
                    exc_info=True
                )
                execution_mode = "sync"
                task = process_batch_analysis.apply(args=[temp_file_path, batch_id])

            status_data = cache.get(cache_key) or {}
            status_data['task_id'] = getattr(task, 'id', None)
            cache.set(cache_key, status_data, 86400)
            
            return Response({
                'batch_id': batch_id,
                'status_url': f'/batch/status/{batch_id}/',
                'message': 'Batch analysis started',
                'mode': execution_mode
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BatchAnalysisStatusView(APIView):
    """Endpoint para verificar status do processamento em lote"""
    
    def get(self, request, batch_id):
        try:
            cache_key = f'batch_analysis:{batch_id}'
            status_data = cache.get(cache_key)
            
            if not status_data:
                return Response(
                    {'error': 'Batch ID not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(status_data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BatchAnalysisResultsView(APIView):
    """Endpoint para download dos resultados"""
    
    def get(self, request, batch_id):
        try:
            cache_key = f'batch_analysis:{batch_id}'
            status_data = cache.get(cache_key)
            
            if not status_data or status_data['status'] != 'COMPLETED':
                return Response(
                    {'error': 'Results not ready'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            results_path = status_data['results_file']
            
            if not os.path.exists(results_path):
                return Response(
                    {'error': 'Results file missing'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Retornar o arquivo para download
            with open(results_path, 'rb') as fh:
                response = Response(fh.read(), content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="batch_results_{batch_id}.csv"'
                return response
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DashboardView(View):
    """Dashboard inicial"""
    def get(self, request):
        try:
            min_score = float(request.GET.get("min_score", 0) or 0)
        except ValueError:
            min_score = 0.0
        try:
            max_score = float(request.GET.get("max_score", 10) or 10)
        except ValueError:
            max_score = 10.0
        try:
            days = int(request.GET.get("days", 90) or 90)
        except ValueError:
            days = 90
        engine = str(request.GET.get("engine", "all")).strip().lower()
        if engine not in {"all", "local", "gpt"}:
            engine = "all"

        min_score = max(0.0, min(10.0, min_score))
        max_score = max(0.0, min(10.0, max_score))
        if max_score < min_score:
            max_score = min_score

        all_scored = PitchAnalysis.objects.exclude(success_score__isnull=True)
        if days > 0:
            all_scored = all_scored.filter(created_at__gte=timezone.now() - timedelta(days=days))
        if engine != "all":
            all_scored = all_scored.filter(metadata__analysis_engine_requested=engine)
        all_scored = all_scored.filter(success_score__gte=min_score, success_score__lte=max_score)

        if not request.user.is_authenticated:
            recent_analyses = PitchAnalysis.objects.none()
        else:
            recent_qs = (
                PitchAnalysis.objects.filter(user=request.user, success_score__isnull=False)
                .filter(success_score__gte=min_score, success_score__lte=max_score)
            )
            if engine != "all":
                recent_qs = recent_qs.filter(metadata__analysis_engine_requested=engine)
            recent_analyses = recent_qs.order_by('-created_at')[:8]
            
        global_stats = all_scored.aggregate(
            avg_score=Avg("success_score"),
            total=Count("id"),
            best=Max("success_score"),
        )
        models = _list_available_models()
        active_model = next((m for m in models if m["is_active"]), None)

        history = list(all_scored.order_by("-created_at")[:24])
        history.reverse()
        chart_labels = [f"#{item.id}" for item in history]
        chart_ids = [item.id for item in history]
        chart_scores = [float(item.success_score or 0) for item in history]
        chart_revenues = [float(item.revenue or 0) for item in history]
        chart_growth = [float(item.growth_rate or 0) for item in history]
        score_distribution = [
            all_scored.filter(success_score__lt=5).count(),
            all_scored.filter(success_score__gte=5, success_score__lt=7.5).count(),
            all_scored.filter(success_score__gte=7.5).count(),
        ]

        industry_labels_map = dict(PitchAnalysis.INDUSTRY_CHOICES)
        sector_rows = list(
            all_scored.values("industry").annotate(avg_score=Avg("success_score"), total=Count("id")).order_by("-avg_score")
        )
        sector_labels = [industry_labels_map.get(row["industry"], row["industry"]) for row in sector_rows]
        sector_avg_scores = [round(float(row["avg_score"] or 0), 2) for row in sector_rows]
        sector_totals = [int(row["total"] or 0) for row in sector_rows]

        user_sector_comparison = {}
        if request.user.is_authenticated and recent_analyses:
            latest = recent_analyses[0]
            sector_avg = all_scored.filter(industry=latest.industry).aggregate(avg=Avg("success_score")).get("avg") or 0
            user_sector_comparison = {
                "industry_label": industry_labels_map.get(latest.industry, latest.industry),
                "latest_score": round(float(latest.success_score or 0), 2),
                "sector_avg": round(float(sector_avg), 2),
            }
        
        return render(request, 'analyzer/dashboard.html', {
            'recent_analyses': recent_analyses,
            'global_stats': global_stats,
            'active_model': active_model,
            'models_count': len(models),
            'chart_labels_json': json.dumps(chart_labels),
            'chart_ids_json': json.dumps(chart_ids),
            'chart_scores_json': json.dumps(chart_scores),
            'chart_revenues_json': json.dumps(chart_revenues),
            'chart_growth_json': json.dumps(chart_growth),
            'chart_distribution_json': json.dumps(score_distribution),
            'chart_sector_labels_json': json.dumps(sector_labels),
            'chart_sector_avg_json': json.dumps(sector_avg_scores),
            'chart_sector_total_json': json.dumps(sector_totals),
            'filter_min_score': min_score,
            'filter_max_score': max_score,
            'filter_days': days,
            'filter_engine': engine,
            'user_sector_comparison': user_sector_comparison,
        })

class PitchFormView(View):
    """Formulário para análise de pitch com tratamento completo de erros"""
    
    def get(self, request):
        """Exibe o formulário vazio"""
        context = {
            'default_date': datetime.now().strftime('%Y-%m-%d'),
            'max_file_size': 50,  # MB
            'industries': PitchAnalysis.INDUSTRY_CHOICES,
            'form_data': {'model_source': 'local'},
        }
        return render(request, 'analyzer/pitch_form.html', context)

    def post(self, request):
        """Processa o formulário submetido"""
        try:
            # 1. Validação inicial dos dados obrigatórios
            startup_name = request.POST.get("startup_name", "").strip()
            contact_email = request.POST.get("contact_email", "").strip()
            industry = request.POST.get("industry", "tech").strip() or "tech"

            raw_text = request.POST.get('text', '').strip()
            text_file = request.FILES.get("text_file")
            youtube_url = request.POST.get("youtube_url", "").strip()
            extracted_text = extract_text_from_uploaded_file(text_file)
            text = merge_pitch_text(raw_text, extracted_text, youtube_url)

            if not text or len(text) < 100:
                messages.error(request, "O texto do pitch deve ter pelo menos 100 caracteres.", extra_tags="text:Texto muito curto")
                return self._render_form_with_data(request)

            if text_file:
                allowed = (".txt", ".md", ".csv", ".pdf", ".docx")
                lower_name = (text_file.name or "").lower()
                if not lower_name.endswith(allowed):
                    messages.error(
                        request,
                        "Documento de texto inválido. Use TXT, MD, CSV, PDF ou DOCX.",
                        extra_tags="text_file:Formato inválido",
                    )
                    return self._render_form_with_data(request)

            # Na validação do áudio
            # 2. Validação dos arquivos
            audio_file = request.FILES.get('audio')
            video_file = request.FILES.get('video')
            if audio_file:
                if not self._is_valid_audio(audio_file):
                    messages.error(request, "Formato de áudio inválido. Use MP3, WAV ou OGG.", extra_tags="audio_file:Formato inválido")
                    return self._render_form_with_data(request)
                
                if audio_file.size > 50 * 1024 * 1024:
                    messages.error(request, "O arquivo de áudio não pode exceder 50MB.", extra_tags="audio_file:Tamanho excedido")
                    return self._render_form_with_data(request)

            # Na validação do vídeo
            if video_file:
                if not self._is_valid_video(video_file):
                    messages.error(request, "Formato de vídeo inválido. Use MP4, MOV ou AVI.", extra_tags="video_file:Formato inválido")
                    return self._render_form_with_data(request)
                
                if video_file.size > 100 * 1024 * 1024:
                    messages.error(request, "O arquivo de vídeo não pode exceder 100MB.", extra_tags="video_file:Tamanho excedido")
                    return self._render_form_with_data(request)

            if youtube_url and not youtube_url.startswith(("https://www.youtube.com/", "https://youtu.be/")):
                messages.error(
                    request,
                    "Link do YouTube inválido.",
                    extra_tags="youtube_url:URL inválida"
                )
                return self._render_form_with_data(request)

            if not video_file and not youtube_url:
                # vídeo é opcional, mas indicamos na UX quando nenhum envio de vídeo existe
                pass
           
           
           
            # 3. Validação dos dados financeiros
            try:
                financial_data = {
                    'revenue': float(request.POST.get('revenue', 0)),
                    'growth_rate': float(request.POST.get('growth_rate', 0)),
                    'profit_margin': float(request.POST.get('profit_margin', 0))
                }
                
                if financial_data['revenue'] < 0:
                    raise ValueError("Receita não pode ser negativa")
                if not (-100 <= financial_data['growth_rate'] <= 1000):
                    raise ValueError("Taxa de crescimento deve estar entre -100% e 1000%")
                if not (0 <= financial_data['profit_margin'] <= 100):
                    raise ValueError("Margem de lucro deve estar entre 0% e 100%")
                    
            except ValueError as e:
                messages.error(request, f"Dados financeiros inválidos: {str(e)}")
                return self._render_form_with_data(request)
            
            # 4. Estratégia de análise escolhida pelo usuário
            model_source = str(request.POST.get("model_source", "local")).strip().lower()
            if model_source not in {"local", "gpt"}:
                model_source = "local"

            model = None
            if model_source == "local":
                model = ensure_model_exists()
                if model is None:
                    logger.critical("Modelo de análise não disponível")
                    return render(request, 'analyzer/error.html', {
                        'error': 'Sistema temporariamente indisponível. Por favor, tente mais tarde.'
                    }, status=503)
            
            # 5. Processamento dos arquivos temporários
            try:
                with self._create_temp_file_manager(audio_file, video_file) as file_paths:
                    audio_path, video_path = file_paths
                    
                    # 6. Preparação dos dados para análise
                    pitch_data = {
                        'text': text,
                        'audio_path': audio_path,
                        'video_path': video_path,
                        'youtube_url': youtube_url,
                        'submission_date': request.POST.get('submission_date')
                    }
                    
                    # 7. Extração de features
                    features, metadata = prepare_features(pitch_data, financial_data)
                    
                    metadata["analysis_engine_requested"] = model_source
                    prediction = None
                    report = None
                    engine_used = model_source

                    # 8. Realização da predição com GPT (quando solicitado)
                    if model_source == "gpt":
                        prediction, report, engine_used = analyze_with_gpt(text, financial_data, metadata)

                    # 9. Fallback local para garantir resposta consistente
                    if prediction is None:
                        if model is None:
                            model = ensure_model_exists()
                        if model is None:
                            raise RuntimeError("Modelo local indisponível para fallback")

                        prediction = predict_pitch_score(
                            model=model,
                            pitch_data=pitch_data,
                            financial_data=financial_data,
                            precomputed_features=features,
                        )
                        report = generate_interpretable_report(prediction, metadata)
                        engine_used = "local"

                    prediction = max(0, min(10, float(prediction)))  # Garante score entre 0-10
                    report = ensure_report_dict(report, prediction)
                    metadata["analysis_engine_used"] = engine_used
                    metadata["sources"] = {
                        "text_file_name": text_file.name if text_file else "",
                        "youtube_url": youtube_url,
                        "has_audio": bool(audio_file),
                        "has_video": bool(video_file),
                    }
                     
                    # 10. Salvamento da análise
                    analysis = self._save_analysis(
                        request=request,
                        startup_name=startup_name,
                        industry=industry,
                        contact_email=contact_email,
                        text=text,
                        audio_file=audio_file,
                        video_file=video_file,
                        financial_data=financial_data,
                        prediction=prediction,
                        report=report,
                        metadata=metadata
                    )
                    
                    # 11. Redirecionamento para resultados
                    return redirect('pitch_results', analysis_id=analysis.id)
                    
            except Exception as e:
                logger.error(f"Erro durante processamento: {str(e)}", exc_info=True)
                messages.error(request, "Erro durante o processamento dos arquivos. Verifique os formatos.")
                return self._render_form_with_data(request)
                
        except Exception as e:
            logger.critical(f"Erro inesperado: {str(e)}", exc_info=True)
            return render(request, 'analyzer/error.html', {
                'error': 'Ocorreu um erro inesperado. Nossa equipe foi notificada.'
            }, status=500)

    # Métodos auxiliares
    def _is_valid_audio(self, audio_file):
        """Valida o formato do arquivo de áudio"""
        valid_extensions = ['.mp3', '.wav', '.ogg', '.webm', '.m4a']
        ext = os.path.splitext(audio_file.name)[1].lower()
        return ext in valid_extensions

    def _is_valid_video(self, video_file):
        """Valida o formato do arquivo de vídeo"""
        valid_extensions = ['.mp4', '.mov', '.avi', '.webm']
        ext = os.path.splitext(video_file.name)[1].lower()
        return ext in valid_extensions

    def _create_temp_file_manager(self, audio_file, video_file):
        """Cria gerenciador de arquivos temporários"""
        class TempFileManager:
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
        
        return TempFileManager(audio_file, video_file)

    def _save_analysis(self, request, startup_name, industry, contact_email, text, audio_file, video_file, 
                      financial_data, prediction, report, metadata):
        """Salva a análise no banco de dados"""
        valid_industries = {choice[0] for choice in PitchAnalysis.INDUSTRY_CHOICES}
        if industry not in valid_industries:
            industry = "other"

        return PitchAnalysis.objects.create(
            user=request.user if request.user.is_authenticated else None,
            startup_name=startup_name or None,
            industry=industry,
            contact_email=contact_email or None,
            text=text,
            audio_file=audio_file,
            video_file=video_file,
            revenue=financial_data['revenue'],
            growth_rate=financial_data['growth_rate'],
            profit_margin=financial_data['profit_margin'],
            success_score=float(prediction),
            report=report,
            metadata=metadata,
            ip_address=self._get_client_ip(request)
        )

    def _get_client_ip(self, request):
        """Obtém o IP do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')


    def _render_form_with_data(self, request):
        """Re-renderiza o formulário com os dados submetidos e mensagens de erro"""
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
            'text_file': request.FILES.get('text_file'),
            'audio_file': request.FILES.get('audio'),
            'video_file': request.FILES.get('video')
        }
        
        # Extrair erros das mensagens
        errors = {}
        storage = messages.get_messages(request)
        for message in storage:
            if hasattr(message, 'extra_tags') and message.extra_tags:
                field, error_msg = message.extra_tags.split(':', 1)
                errors[field] = error_msg
        
        context = {
            'form_data': form_data,
            'errors': errors,
            'default_date': datetime.now().strftime('%Y-%m-%d'),
            'max_file_size': 50,  # MB
            'industries': PitchAnalysis.INDUSTRY_CHOICES,
        }
        return render(request, 'analyzer/pitch_form.html', context)

class PitchResultsView(View):
    """Página de resultados da análise"""
    def get(self, request, analysis_id):
        analysis = PitchAnalysis.objects.get(id=analysis_id)
        return render(request, 'analyzer/result.html', {
            'analysis': analysis
        })


class PitchReportPDFView(View):
    """Exporta relatório de análise em PDF."""

    def get(self, request, analysis_id):
        analysis = PitchAnalysis.objects.get(id=analysis_id)
        if analysis.user and request.user.is_authenticated and analysis.user_id != request.user.id:
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
        export_analysis_pdf(analysis, output_path)

        return FileResponse(
            open(output_path, "rb"),
            as_attachment=True,
            filename=f"relatorio_pitch_{analysis.id}.pdf",
            content_type="application/pdf",
        )


class ModelManagementView(LoginRequiredMixin, View):
    """Painel para gestão de modelos treinados"""

    def get(self, request):
        models = _list_available_models()
        context = {
            "models": models,
            "active_model": get_active_model_name(),
            "enhanced_available": (
                (Path(settings.DATA_DIR) / "pitches_dataset_enhanced.csv").exists()
                and (Path(settings.DATA_DIR) / "financials_dataset_enhanced.csv").exists()
            ),
        }
        return render(request, "analyzer/model_management.html", context)

    def post(self, request):
        action = request.POST.get("action", "").strip()

        try:
            if action == "fetch_external":
                call_command("fetch_external_dataset", "--combine-with-default", "--output-prefix", "enhanced")
                messages.success(request, "Dataset externo importado e combinado com sucesso.")

            elif action == "train_new":
                model_name = _safe_slug_model_name(request.POST.get("model_name"))
                dataset_source = request.POST.get("dataset_source", "default")
                _run_training_for_model(model_name, dataset_source=dataset_source)
                set_active_model(model_name)
                messages.success(request, f"Novo modelo treinado e ativado: {model_name}")

            elif action == "retrain":
                model_name = request.POST.get("model_name", "")
                dataset_source = request.POST.get("dataset_source", "default")
                if not model_name:
                    raise ValueError("Modelo não informado para retreino.")
                _run_training_for_model(model_name, dataset_source=dataset_source)
                messages.success(request, f"Modelo retreinado com sucesso: {model_name}")

            elif action == "set_active":
                model_name = request.POST.get("model_name", "")
                if not model_name:
                    raise ValueError("Modelo não informado para ativação.")
                if not get_model_path(model_name).exists():
                    raise FileNotFoundError(f"Modelo não encontrado: {model_name}")
                set_active_model(model_name)
                messages.success(request, f"Modelo ativo atualizado para: {model_name}")

            elif action == "save_meta":
                model_name = request.POST.get("model_name", "")
                display_name = request.POST.get("display_name", "").strip()
                description = request.POST.get("description", "").strip()
                if not model_name:
                    raise ValueError("Modelo não informado para edição.")
                meta_path = get_meta_path(model_name)
                payload = _read_json_file(meta_path)
                payload["display_name"] = display_name
                payload["description"] = description
                _write_json_file(meta_path, payload)
                messages.success(request, f"Metadados atualizados para {model_name}.")

            elif action == "delete":
                model_name = request.POST.get("model_name", "")
                if not model_name:
                    raise ValueError("Modelo não informado para exclusão.")

                models = _list_available_models()
                if len(models) <= 1:
                    raise ValueError("Não é possível excluir o único modelo disponível.")

                file_paths = [
                    get_model_path(model_name),
                    get_metrics_path(model_name),
                    get_meta_path(model_name),
                ]
                for file_path in file_paths:
                    try:
                        if Path(file_path).exists():
                            os.remove(file_path)
                    except OSError:
                        pass

                if get_active_model_name() == model_name:
                    remaining = _list_available_models()
                    if remaining:
                        set_active_model(remaining[0]["name"])

                messages.success(request, f"Modelo removido: {model_name}")

            else:
                messages.error(request, "Ação inválida no painel de modelos.")

        except Exception as exc:
            logger.error("Model management action failed: %s", str(exc), exc_info=True)
            messages.error(request, f"Falha ao executar ação: {str(exc)}")

        return redirect("model_management")


class InvestorDashboardView(View):
    """Dashboard público para investidores visualizarem potenciais de startups"""

    def get(self, request):
        try:
            min_score = float(request.GET.get("min_score", 0) or 0)
        except ValueError:
            min_score = 0.0
        try:
            max_score = float(request.GET.get("max_score", 10) or 10)
        except ValueError:
            max_score = 10.0
        try:
            days = int(request.GET.get("days", 180) or 180)
        except ValueError:
            days = 180
        engine = str(request.GET.get("engine", "all")).strip().lower()
        if engine not in {"all", "local", "gpt"}:
            engine = "all"

        min_score = max(0.0, min(10.0, min_score))
        max_score = max(0.0, min(10.0, max_score))
        if max_score < min_score:
            max_score = min_score

        analyses = PitchAnalysis.objects.exclude(success_score__isnull=True)
        if days > 0:
            analyses = analyses.filter(created_at__gte=timezone.now() - timedelta(days=days))
        if engine != "all":
            analyses = analyses.filter(metadata__analysis_engine_requested=engine)
        analyses = analyses.filter(success_score__gte=min_score, success_score__lte=max_score).order_by("-created_at")
        top_analyses = list(analyses[:12])

        for analysis in top_analyses:
            report = analysis.report or {}
            investor_pitch = report.get("investor_pitch", {}) if isinstance(report, dict) else {}
            if not investor_pitch:
                score = float(analysis.success_score or 0.0)
                thesis = "Oportunidade em monitoramento"
                if score >= 8:
                    thesis = "Tese de alto crescimento com potencial de escala acelerada"
                elif score >= 6:
                    thesis = "Tese com boa tração e espaço para ganho de eficiência"

                investor_pitch = {
                    "investment_thesis": thesis,
                    "funding_readiness": "Alta" if score >= 7.5 else ("Média" if score >= 5 else "Inicial"),
                    "capital_use_plan": [
                        "Expansão comercial orientada por dados",
                        "Fortalecimento de produto e retenção de clientes",
                        "Otimização de operações e margem",
                    ],
                }
            analysis.investor_pitch = investor_pitch

        total = analyses.count()
        summary = analyses.aggregate(
            avg_score=Avg("success_score"),
            max_score=Max("success_score"),
        )
        high_potential = analyses.filter(success_score__gte=7.5).count()

        recent_investor = list(analyses[:20])
        investor_labels = [f"#{a.id}" for a in recent_investor]
        investor_ids = [a.id for a in recent_investor]
        investor_scores = [float(a.success_score or 0) for a in recent_investor]
        investor_revenue = [float(a.revenue or 0) for a in recent_investor]
        investor_growth = [float(a.growth_rate or 0) for a in recent_investor]

        context = {
            "analyses": top_analyses,
            "kpi_total": total,
            "kpi_high_potential": high_potential,
            "kpi_avg_score": round(float(summary["avg_score"] or 0), 2),
            "kpi_max_score": round(float(summary["max_score"] or 0), 2),
            "active_model": get_active_model_name(),
            "investor_labels_json": json.dumps(investor_labels),
            "investor_ids_json": json.dumps(investor_ids),
            "investor_scores_json": json.dumps(investor_scores),
            "investor_revenue_json": json.dumps(investor_revenue),
            "investor_growth_json": json.dumps(investor_growth),
            "filter_min_score": min_score,
            "filter_max_score": max_score,
            "filter_days": days,
            "filter_engine": engine,
        }
        return render(request, "analyzer/investor_dashboard.html", context)





def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registro realizado com sucesso!")
            return redirect('dashboard')
    else:
        form = RegisterForm()
    
    return render(request, 'analyzer/register.html', {'form': form})



