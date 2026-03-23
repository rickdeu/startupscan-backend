import os
import uuid
from django.conf import settings
from startupscan_api.data_loader import load_training_data
from startupscan_api.modeling import train_and_evaluate, predict_success_score
from startupscan_api.services.model_registry import (
    get_active_model_name,
    get_metrics_path,
    get_model_path,
    set_active_model,
    write_json,
)
import logging
import joblib
import pickle
import pandas as pd

logger = logging.getLogger(__name__)

#@shared_task(bind=True)
#def train_model_task(self):
def train_model_task():

    """Tarefa Celery para treinamento do modelo em background"""
    try:
        logger.info("Iniciando treinamento do modelo em background...")

        active_model_name = get_active_model_name()
        model_path = get_model_path(active_model_name)
        pitches_path, financials_path = load_training_data()
        pitches_df = pd.read_csv(pitches_path)
        financial_df = pd.read_csv(financials_path)

        model, metrics = train_and_evaluate(pitches_df, financial_df)
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(model, model_path)
        write_json(get_metrics_path(active_model_name), metrics)
        set_active_model(active_model_name)

        return {
            "status": "completed",
            "message": "Model trained successfully",
            "task_id": str(uuid.uuid4()),
            "model_name": active_model_name,
            "metrics": metrics,
        }
    except Exception as e:
        logger.error(f"Erro no treinamento: {str(e)}")
        raise
        #raise self.retry(exc=e, countdown=60)


def ensure_model_exists():
    """
    Garante que o modelo existe, treinando um novo se necessário.
    Retorna o modelo carregado ou None em caso de falha.
    """
    active_model_name = get_active_model_name()
    model_path = get_model_path(active_model_name)
    
    try:
        # Tentar carregar modelo existente.
        if model_path.exists():
            try:
                return joblib.load(model_path)
            except Exception as load_error:
                # Modelo incompatível/corrompido: remove e força retreino.
                logger.warning(
                    "Failed to load existing model. Retraining a new one. Error: %s",
                    str(load_error),
                    exc_info=True,
                )
                try:
                    os.remove(model_path)
                except OSError:
                    logger.warning("Could not remove invalid model file: %s", model_path)
        
        # Se não existir (ou foi removido), treinar novo modelo.
        logger.info("Model not found or invalid. Training new model...")
        pitches_path, financials_path = load_training_data()
        pitches_df = pd.read_csv(pitches_path)
        financial_df = pd.read_csv(financials_path)
        
        if pitches_df is None or financial_df is None:
            logger.error("Training data not available")
            return None
            
        model, _ = train_and_evaluate(pitches_df, financial_df)
        
        # Garantir que o diretório existe.
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(model, model_path)
        
        return model
        
    except Exception as e:
        logger.error(f"Failed to load or train model: {str(e)}", exc_info=True)
        return None


def predict_pitch_score(model, pitch_data, financial_data, precomputed_features=None):
    """
    Wrapper único para predição do score de sucesso, compatível com versões de modelo.
    """
    return predict_success_score(
        model_obj=model,
        pitch_data=pitch_data,
        financial_data=financial_data,
        precomputed_features=precomputed_features,
    )





def ensure_model_exists_backuo():
    model_path = os.path.join(settings.AI_MODELS_DIR, 'pitch_model.pkl')
    
    try:
        # Verificação robusta do arquivo
        if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
            try:
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                    # Verificação básica do modelo carregado
                    if hasattr(model, 'predict'):  # Verifica se é um modelo válido
                        return model
            except Exception as load_error:
                logger.warning(f"Failed to load existing model, will retrain: {load_error}")
                os.remove(model_path)  # Remove o arquivo corrompido
        
        # Treinar novo modelo se o carregamento falhar
        logger.info("Training new model...")
        pitches_path, financials_path = load_training_data()

        pitches_df = pd.read_csv(pitches_path)
        financial_df = pd.read_csv(financials_path)
        
        
        if pitches_df is None or financial_df is None:
            logger.error("Training data not available")
            return None
            
        model, _ = train_and_evaluate(pitches_df, financial_df)
        
        # Garantir que o diretório existe
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Salvar com verificação
        temp_path = model_path + '.tmp'
        with open(temp_path, 'wb') as f:
            pickle.dump(model, f, protocol=4)
        
        # Verificar se o novo arquivo é válido
        try:
            with open(temp_path, 'rb') as f:
                pickle.load(f)  # Testar carregamento
            os.replace(temp_path, model_path)  # Substitui o arquivo antigo
        except Exception as verify_error:
            logger.error(f"Failed to verify new model: {verify_error}")
            os.remove(temp_path)
            return None
        
        return model
        
    except Exception as e:
        logger.error(f"Failed to load or train model: {str(e)}", exc_info=True)
        return None