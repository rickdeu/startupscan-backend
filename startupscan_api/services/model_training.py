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

    """Celery task for training the model in the background"""
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


def _is_model_ready(model_obj) -> tuple[bool, str]:
    """
    Run a synthetic prediction to validate that the loaded model is fitted.
    Avoids late errors such as 'idf vector is not fitted' in production.
    """
    try:
        probe_pitch = {
            "text": "Startup de teste para validar pipeline de inferencia.",
            "audio_path": None,
            "video_path": None,
            "youtube_url": "",
        }
        probe_financial = {
            "revenue": 1000000.0,
            "expenses": 250000.0,
            "growth_rate": 10.0,
            "customer_count": 100.0,
            "profit_margin": 20.0,
        }
        _ = predict_success_score(
            model_obj=model_obj,
            pitch_data=probe_pitch,
            financial_data=probe_financial,
            precomputed_features=None,
        )
        return True, ""
    except Exception as exc:
        return False, str(exc)


def ensure_model_exists(force_retrain: bool = False):
    """
    Ensures the model exists, training a new one if necessary.
    Returns the loaded model or None on failure.
    """
    active_model_name = get_active_model_name()
    model_path = get_model_path(active_model_name)
    
    try:
        # Try to load the existing model.
        if model_path.exists() and not force_retrain:
            try:
                loaded_model = joblib.load(model_path)
                ready, reason = _is_model_ready(loaded_model)
                if ready:
                    return loaded_model
                logger.warning(
                    "Loaded model is not ready for inference. Retraining. Reason: %s",
                    reason,
                )
                try:
                    os.remove(model_path)
                except OSError:
                    logger.warning("Could not remove invalid model file: %s", model_path)
            except Exception as load_error:
                # Incompatible/corrupted model: remove it and force retraining.
                logger.warning(
                    "Failed to load existing model. Retraining a new one. Error: %s",
                    str(load_error),
                    exc_info=True,
                )
                try:
                    os.remove(model_path)
                except OSError:
                    logger.warning("Could not remove invalid model file: %s", model_path)
        
        # If it doesn't exist (or was removed), train a new model.
        logger.info("Model not found or invalid. Training new model...")
        pitches_path, financials_path = load_training_data()
        pitches_df = pd.read_csv(pitches_path)
        financial_df = pd.read_csv(financials_path)
        
        if pitches_df is None or financial_df is None:
            logger.error("Training data not available")
            return None
            
        model, _ = train_and_evaluate(pitches_df, financial_df)
        
        # Ensure the directory exists.
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(model, model_path)
        ready, reason = _is_model_ready(model)
        if not ready:
            raise RuntimeError(f"Modelo treinado, porém inválido para inferência: {reason}")
        
        return model
        
    except Exception as e:
        logger.error(f"Failed to load or train model: {str(e)}", exc_info=True)
        return None


def predict_pitch_score(model, pitch_data, financial_data, precomputed_features=None):
    """
    Single wrapper for success-score prediction, compatible across model versions.
    """
    try:
        return predict_success_score(
            model_obj=model,
            pitch_data=pitch_data,
            financial_data=financial_data,
            precomputed_features=precomputed_features,
        )
    except Exception as exc:
        msg = str(exc).lower()
        recoverable_signals = (
            "not fitted",
            "idf vector is not fitted",
            "notfittederror",
        )
        if any(signal in msg for signal in recoverable_signals):
            logger.warning(
                "Inference model state invalid (%s). Attempting auto-retrain recovery.",
                str(exc),
                exc_info=True,
            )
            recovered_model = ensure_model_exists(force_retrain=True)
            if recovered_model is None:
                raise
            return predict_success_score(
                model_obj=recovered_model,
                pitch_data=pitch_data,
                financial_data=financial_data,
                precomputed_features=precomputed_features,
            )
        raise
