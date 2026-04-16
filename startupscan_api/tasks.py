from celery import shared_task
import logging
import pandas as pd
import os
from django.core.cache import cache
from django.conf import settings
from .utils import prepare_features

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def reprocess_pitch_analysis(self, analysis_id):
    """Reprocessa uma análise de pitch existente, recalculando score e relatório."""
    from .models import PitchAnalysis
    from .services.model_training import predict_pitch_score
    from .utils import generate_interpretable_report

    try:
        analysis = PitchAnalysis.objects.get(pk=analysis_id)
    except PitchAnalysis.DoesNotExist:
        logger.error("reprocess_pitch_analysis: análise %s não encontrada", analysis_id)
        return

    try:
        analysis.status = "processing"
        analysis.save(update_fields=["status", "updated_at"])

        features_dict = {
            "revenue": float(analysis.revenue or 0),
            "growth_rate": float(analysis.growth_rate or 0),
            "profit_margin": float(analysis.profit_margin or 0),
            "burn_rate": float(analysis.burn_rate or 0),
        }
        score, confidence = predict_pitch_score(features_dict)
        report = generate_interpretable_report(features_dict, score)

        analysis.success_score = score
        analysis.confidence = confidence
        analysis.report = report
        analysis.status = "completed"
        analysis.save(update_fields=["success_score", "confidence", "report", "status", "updated_at"])
        logger.info("reprocess_pitch_analysis: análise %s reprocessada com sucesso", analysis_id)

    except Exception as exc:
        logger.exception("reprocess_pitch_analysis: erro ao reprocessar análise %s", analysis_id)
        analysis.status = "failed"
        analysis.save(update_fields=["status", "updated_at"])
        raise self.retry(exc=exc, countdown=60)

@shared_task(bind=True)
def process_batch_analysis(self, file_path, batch_id):
    """Tarefa Celery para processamento em lote"""
    cache_key = f'batch_analysis:{batch_id}'
    results = []
    
    try:
        # 1. Ler arquivo CSV com chunks para evitar problemas de memória
        chunksize = 100  # Processar 100 registros por vez
        total_rows = sum(1 for _ in pd.read_csv(file_path, chunksize=chunksize))
        
        # Atualizar status com total de itens
        cache.set(cache_key, {
            'status': 'PROCESSING',
            'total_items': total_rows,
            'processed_items': 0,
            'results_file': None,
            'task_id': self.request.id
        }, 86400)
        
        # 2. Processar em chunks
        processed_count = 0
        temp_results = []
        
        for chunk in pd.read_csv(file_path, chunksize=chunksize):
            chunk_results = []
            
            for _, row in chunk.iterrows():
                try:
                    features, metadata = prepare_features(row.to_dict(), {})
                    chunk_results.append({
                        'id': row.get('id'),
                        'features': features.tolist(),
                        'metadata': metadata
                    })
                except Exception as e:
                    chunk_results.append({
                        'id': row.get('id'),
                        'error': str(e)
                    })
                
                processed_count += 1
                
                # Atualizar progresso a cada 10%
                if processed_count % max(1, total_rows//10) == 0:
                    cache.set(cache_key, {
                        'status': 'PROCESSING',
                        'total_items': total_rows,
                        'processed_items': processed_count,
                        'results_file': None,
                        'task_id': self.request.id
                    }, 86400)
            
            temp_results.extend(chunk_results)
        
        # 3. Salvar resultados
        results_dir = os.path.join(settings.MEDIA_ROOT, 'batch_results')
        os.makedirs(results_dir, exist_ok=True)
        results_path = os.path.join(results_dir, f'results_{batch_id}.csv')
        
        pd.DataFrame(temp_results).to_csv(results_path, index=False)
        
        # 4. Atualizar status final
        cache.set(cache_key, {
            'status': 'COMPLETED',
            'total_items': total_rows,
            'processed_items': processed_count,
            'results_file': results_path,
            'task_id': self.request.id
        }, 86400)
        
        # 5. Limpar arquivo temporário de entrada
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return True
        
    except Exception as e:
        # Atualizar status com erro
        cache.set(cache_key, {
            'status': 'FAILED',
            'error': str(e),
            'task_id': self.request.id
        }, 86400)
        
        # Limpar arquivo temporário em caso de erro
        if os.path.exists(file_path):
            os.remove(file_path)
        
        raise self.retry(exc=e, countdown=60)