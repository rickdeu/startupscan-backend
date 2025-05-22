from celery import shared_task
import pandas as pd
import os
from django.core.cache import cache
from django.conf import settings
from .utils import prepare_features

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