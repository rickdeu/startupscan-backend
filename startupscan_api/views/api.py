import logging
import uuid

from django.core.cache import cache
from django.conf import settings
import os

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

try:
    from celery.result import AsyncResult
except Exception:
    class AsyncResult:
        def __init__(self, task_id):
            self.id = task_id
            self.status = "UNAVAILABLE"
            self.result = None

        def ready(self):
            return False

        def failed(self):
            return False

        def successful(self):
            return False

from startupscan_api.modeling import analyze_with_gpt, ensure_report_dict
from startupscan_api.serializers import BatchAnalysisSerializer
from startupscan_api.services.model_training import ensure_model_exists, predict_pitch_score, train_model_task
from startupscan_api.services.pitch_input import extract_text_from_uploaded_file, merge_pitch_text
from startupscan_api.tasks import process_batch_analysis
from startupscan_api.util.file_management import TempFileManager
from startupscan_api.utils import generate_interpretable_report, prepare_features
from .helpers import _safe_exception_message

logger = logging.getLogger(__name__)


class StartupPitchAnalyzer(APIView):
    def post(self, request):
        try:
            text = request.data.get('text', '')
            text_file = request.FILES.get('text_file')
            audio_file = request.FILES.get('audio')
            video_file = request.FILES.get('video')
            youtube_url = (request.data.get("youtube_url", "") or "").strip()
            startup_name = (request.data.get("startup_name", "") or "").strip()
            industry = (request.data.get("industry", "") or "").strip()
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

            with TempFileManager(audio_file, video_file) as file_paths:
                audio_path, video_path = file_paths
                pitch_data = {
                    'text': text,
                    'audio_path': audio_path,
                    'video_path': video_path,
                    'youtube_url': youtube_url,
                }
                features, metadata = prepare_features(pitch_data, financial_data)
                metadata["analysis_engine_requested"] = model_source
                metadata["startup_name"] = startup_name
                metadata["industry"] = industry
                metadata["analysis_context_id"] = str(uuid.uuid4())

                prediction = None
                report = None
                engine_used = model_source

                if model_source == "gpt":
                    prediction, report, engine_used = analyze_with_gpt(text, financial_data, metadata)

                if prediction is None:
                    model = ensure_model_exists()
                    if model is None:
                        return Response(
                            {'error': 'Model not available and could not be trained'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE,
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
            detail = _safe_exception_message(e)
            return Response(
                {'error': f'An error occurred during analysis: {detail}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ModelRetrainView(APIView):
    def post(self, request):
        try:
            result = train_model_task()
            task_id = result.get("task_id") if isinstance(result, dict) else None
            return Response({
                "message": "Model training executed",
                "task_id": task_id,
                "result": result,
                "status_endpoint": f"/training/status/{task_id}/" if task_id else None,
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrainingStatusView(APIView):
    def get(self, request, task_id):
        try:
            if not task_id or str(task_id).lower() in {"none", "null"}:
                return Response({
                    "task_id": task_id,
                    "status": "COMPLETED",
                    "ready": True,
                    "result": {"message": "Training was executed synchronously"},
                }, status=status.HTTP_200_OK)

            task = AsyncResult(task_id)
            response = {"task_id": task.id, "status": task.status, "ready": task.ready()}
            if task.failed():
                response["error"] = str(task.result)
            elif task.successful():
                response["result"] = task.result
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning("Training status backend unavailable for task %s: %s", task_id, str(e))
            return Response({
                "task_id": task_id,
                "status": "UNAVAILABLE",
                "ready": False,
                "error": "Task backend unavailable in current runtime",
            }, status=status.HTTP_200_OK)


class BatchAnalysisView(APIView):
    def post(self, request):
        try:
            if request.user.is_authenticated:
                from subscriptions.mixins import check_feature_access
                from startupscan_api.roles import ROLE_ADMIN, get_user_role
                if get_user_role(request.user) != ROLE_ADMIN:
                    allowed, _ = check_feature_access(request.user, 'batch_analysis')
                    if not allowed:
                        return Response(
                            {'error': 'Batch analysis requires a higher subscription plan.'},
                            status=status.HTTP_403_FORBIDDEN,
                        )

            serializer = BatchAnalysisSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            file = serializer.validated_data['file']
            batch_id = str(uuid.uuid4())
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'batch_analysis')
            os.makedirs(temp_dir, exist_ok=True)

            temp_file_path = os.path.join(temp_dir, f"{batch_id}.csv")
            with open(temp_file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            cache_key = f'batch_analysis:{batch_id}'
            cache.set(cache_key, {
                'status': 'PENDING',
                'total_items': 0,
                'processed_items': 0,
                'results_file': None,
                'task_id': None,
            }, 86400)

            execution_mode = "async"
            try:
                task = process_batch_analysis.delay(temp_file_path, batch_id)
            except Exception:
                logger.warning("Celery broker unavailable. Running batch analysis synchronously.", exc_info=True)
                execution_mode = "sync"
                task = process_batch_analysis.apply(args=[temp_file_path, batch_id])

            status_data = cache.get(cache_key) or {}
            status_data['task_id'] = getattr(task, 'id', None)
            cache.set(cache_key, status_data, 86400)

            return Response({
                'batch_id': batch_id,
                'status_url': f'/batch/status/{batch_id}/',
                'message': 'Batch analysis started',
                'mode': execution_mode,
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BatchAnalysisStatusView(APIView):
    def get(self, request, batch_id):
        try:
            cache_key = f'batch_analysis:{batch_id}'
            status_data = cache.get(cache_key)
            if not status_data:
                return Response({'error': 'Batch ID not found'}, status=status.HTTP_404_NOT_FOUND)
            return Response(status_data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BatchAnalysisResultsView(APIView):
    def get(self, request, batch_id):
        try:
            cache_key = f'batch_analysis:{batch_id}'
            status_data = cache.get(cache_key)
            if not status_data or status_data['status'] != 'COMPLETED':
                return Response({'error': 'Results not ready'}, status=status.HTTP_404_NOT_FOUND)

            results_path = status_data['results_file']
            if not os.path.exists(results_path):
                return Response({'error': 'Results file missing'}, status=status.HTTP_404_NOT_FOUND)

            with open(results_path, 'rb') as fh:
                response = Response(fh.read(), content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="batch_results_{batch_id}.csv"'
                return response

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
