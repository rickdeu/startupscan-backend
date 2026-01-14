import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from startupscan_api.forms import RegisterForm
from startupscan_api.models import PitchAnalysis
from startupscan_api.services.model_training import ensure_model_exists, train_model_task
from startupscan_api.util.file_management import TempFileManager

import joblib
from celery.result import AsyncResult
from django.conf import settings

from .utils import (
    process_audio,
    process_video,
    analyze_text,
    prepare_features,
    train_and_evaluate,
    generate_interpretable_report
)

logger = logging.getLogger(__name__)



class StartupPitchAnalyzer(APIView):
    """
    Endpoint para análise multimodal de pitches de startups
    """
    
    def post(self, request):
        try:
            # Extrair dados da requisição
            text = request.data.get('text', '')
            audio_file = request.FILES.get('audio')
            video_file = request.FILES.get('video')
            financial_data = request.data.get('financial_data', {})
            
            # 1. Garantir que o modelo existe
            model = ensure_model_exists()
            if model is None:
                return Response(
                    {'error': 'Model not available and could not be trained'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # 2. Processar arquivos temporários (context manager recomendado)
            with TempFileManager(audio_file, video_file) as file_paths:
                audio_path, video_path = file_paths
                
                # 3. Preparar dados para análise
                pitch_data = {
                    'text': text,
                    'audio_path': audio_path,
                    'video_path': video_path
                }
                
                # 4. Extrair features
                features, metadata = prepare_features(pitch_data, financial_data)
                 
                # 5. Fazer previsão
                prediction = model.predict([features])[0]
                
                # 6. Gerar relatório
                report = generate_interpretable_report(prediction, metadata)
                
                return Response({
                    'success_score': float(prediction),
                    'report': report,
                    'metadata': metadata
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
            # Disparar tarefa assíncrona
            task = train_model_task() #.delay()
            
            return Response(
                {
                    "message": "Model training started in background",
                    "task_id": task,
                    "status_endpoint": f"/api/training/status/{task}/"
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
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            
            # 4. Iniciar tarefa assíncrona
            task = process_batch_analysis.delay(temp_file_path, batch_id)
            
            # 5. Armazenar metadados no cache (expira em 24h)
            cache.set(f'batch_analysis:{batch_id}', {
                'status': 'PENDING',
                'total_items': 0,
                'processed_items': 0,
                'results_file': None,
                'task_id': task.id
            }, 86400)  # 24 horas
            
            return Response({
                'batch_id': batch_id,
                'status_url': f'/api/batch/status/{batch_id}/',
                'message': 'Batch analysis started'
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

# web form
from django.shortcuts import render, redirect
from django.views import View

class DashboardView(View):
    """Dashboard inicial"""
    def get(self, request):
        if not request.user.is_authenticated:
            recent_analyses = PitchAnalysis.objects.none()
        else:
            recent_analyses = PitchAnalysis.objects.filter(user=request.user).order_by('-created_at')[:5]
        
        return render(request, 'analyzer/dashboard.html', {
            'recent_analyses': recent_analyses
        })

class PitchFormView(View):
    """Formulário para inserção de dados do pitch"""
    def get(self, request):
        return render(request, 'analyzer/pitch_form.html')

    def post(self, request):
        try:
            # Extrair dados do formulário
            text = request.POST.get('text', '')
            audio_file = request.FILES.get('audio')
            video_file = request.FILES.get('video')
            
            # Dados financeiros
            financial_data = {
                'revenue': float(request.POST.get('revenue', 0)),
                'growth_rate': float(request.POST.get('growth_rate', 0)),
                'profit_margin': float(request.POST.get('profit_margin', 0))
            }
            
            # Garantir que o modelo existe
            model = ensure_model_exists()
            if model is None:
                return render(request, 'analyzer/error.html', {
                    'error': 'Modelo não disponível e não pôde ser treinado'
                }, status=503)
            
            # Processar arquivos temporários
            with TempFileManager(audio_file, video_file) as file_paths:
                audio_path, video_path = file_paths
                
                # Preparar dados para análise
                pitch_data = {
                    'text': text,
                    'audio_path': audio_path,
                    'video_path': video_path
                }
                
                # Extrair features
                features, metadata = prepare_features(pitch_data, financial_data)
                
                # Fazer previsão
                prediction = model.predict([features])[0]
                
                # Gerar relatório
                report = generate_interpretable_report(prediction, metadata)
                
                # Salvar análise no banco de dados
                analysis = PitchAnalysis.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    text=text,
                    audio_file=audio_file,
                    video_file=video_file,
                    revenue=financial_data['revenue'],
                    growth_rate=financial_data['growth_rate'],
                    profit_margin=financial_data['profit_margin'],
                    success_score=float(prediction),
                    report=report,
                    metadata=metadata
                )
                
                return redirect('pitch_results', analysis_id=analysis.id)
            
        except Exception as e:
            logger.error(f"Error processing pitch: {str(e)}", exc_info=True)
            return render(request, 'analyzer/error.html', {
                'error': 'Ocorreu um erro durante a análise'
            }, status=500)




from django.shortcuts import render, redirect
from django.views import View
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
import logging
from .models import PitchAnalysis
import tempfile
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class PitchFormView(View):
    """Formulário para análise de pitch com tratamento completo de erros"""
    
    def get(self, request):
        """Exibe o formulário vazio"""
        context = {
            'default_date': datetime.now().strftime('%Y-%m-%d'),
            'max_file_size': 50  # MB
        }
        return render(request, 'analyzer/pitch_form.html', context)

    def post(self, request):
        """Processa o formulário submetido"""
        try:
            # 1. Validação inicial dos dados obrigatórios
                        # Na validação do texto
            text = request.POST.get('text', '').strip()
            if not text or len(text) < 100:
                messages.error(request, "O texto do pitch deve ter pelo menos 100 caracteres.", extra_tags="text:Texto muito curto")
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
            
            # 4. Verificação do modelo
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
                        'submission_date': request.POST.get('submission_date')
                    }
                    
                    # 7. Extração de features
                    features, metadata = prepare_features(pitch_data, financial_data)
                    
                    # 8. Realização da predição
                    prediction = model.predict([features])[0]
                    prediction = max(0, min(10, prediction))  # Garante score entre 0-10
                    
                    # 9. Geração do relatório
                    report = generate_interpretable_report(prediction, metadata)
                     
                    # 10. Salvamento da análise
                    analysis = self._save_analysis(
                        request=request,
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
        valid_extensions = ['.mp3', '.wav', '.ogg']
        ext = os.path.splitext(audio_file.name)[1].lower()
        return ext in valid_extensions

    def _is_valid_video(self, video_file):
        """Valida o formato do arquivo de vídeo"""
        valid_extensions = ['.mp4', '.mov', '.avi']
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
                    self.audio_path = fs.save(f"pitch_audio_{tempfile.gettempprefix()}", self.audio)
                if self.video:
                    self.video_path = fs.save(f"pitch_video_{tempfile.gettempprefix()}", self.video)
                return (self.audio_path, self.video_path)
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                fs = FileSystemStorage(location=tempfile.gettempdir())
                if self.audio_path and fs.exists(self.audio_path):
                    fs.delete(self.audio_path)
                if self.video_path and fs.exists(self.video_path):
                    fs.delete(self.video_path)
        
        return TempFileManager(audio_file, video_file)

    def _save_analysis(self, request, text, audio_file, video_file, 
                      financial_data, prediction, report, metadata):
        """Salva a análise no banco de dados"""
        return PitchAnalysis.objects.create(
            user=request.user if request.user.is_authenticated else None,
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
            'text': request.POST.get('text', ''),
            'revenue': request.POST.get('revenue', ''),
            'growth_rate': request.POST.get('growth_rate', ''),
            'profit_margin': request.POST.get('profit_margin', ''),
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
            'max_file_size': 50  # MB
        }
        return render(request, 'analyzer/pitch_form.html', context)

class PitchResultsView(View):
    """Página de resultados da análise"""
    def get(self, request, analysis_id):
        analysis = PitchAnalysis.objects.get(id=analysis_id)
        return render(request, 'analyzer/result.html', {
            'analysis': analysis
        })





# analyzer/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages

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



