# startupscan/imports.py

# Base
import os
import logging
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from collections import Counter

# Modelos de ML
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    mean_squared_error,
    r2_score,
    confusion_matrix,
    ConfusionMatrixDisplay
)
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# Modelos adicionais
try:
    from xgboost import XGBRegressor
except ImportError:
    logging.warning("XGBoost não instalado. Use: pip install xgboost")

# Carregamento lazy de libs pesadas para não travar o boot do web server.
plt = None
sns = None
whisper = None
librosa = None
sf = None
sr = None
cv2 = None
mp = None
DeepFace = None
mp_editor = None
pipeline = None
textstat = None


def ensure_plot_imports():
    global plt, sns
    if plt is not None and sns is not None:
        return True
    try:
        import matplotlib.pyplot as _plt
        import seaborn as _sns
        plt = _plt
        sns = _sns
        return True
    except Exception as exc:
        logging.warning("Pacotes de visualização indisponíveis: %s", str(exc))
        return False


def ensure_audio_imports():
    global whisper, librosa, sf, sr
    if whisper is not None and librosa is not None:
        return True
    try:
        import whisper as _whisper
        import librosa as _librosa
        import soundfile as _sf
        whisper = _whisper
        librosa = _librosa
        sf = _sf
    except Exception as exc:
        logging.warning("Pacotes de áudio indisponíveis: %s", str(exc))
    try:
        import speech_recognition as _sr
        sr = _sr
    except Exception as exc:
        logging.warning("speech_recognition indisponível: %s", exc)
    return whisper is not None and librosa is not None


def ensure_video_imports():
    global cv2, mp, DeepFace, mp_editor
    if cv2 is not None and mp is not None and mp_editor is not None:
        return True
    try:
        import cv2 as _cv2
        import mediapipe as _mp
        import moviepy.editor as _mp_editor
        cv2 = _cv2
        mp = _mp
        mp_editor = _mp_editor
    except Exception as exc:
        logging.warning("Pacotes base de vídeo indisponíveis: %s", str(exc))
    try:
        from deepface import DeepFace as _DeepFace
        DeepFace = _DeepFace
    except Exception as exc:
        logging.warning(
            "DeepFace/RetinaFace indisponível (%s). "
            "Use: pip install deepface tf-keras",
            str(exc),
        )
    return cv2 is not None and mp is not None and mp_editor is not None


def ensure_nlp_imports():
    global pipeline, textstat
    if pipeline is not None and textstat is not None:
        return True
    try:
        from transformers import pipeline as _pipeline
        import textstat as _textstat
        pipeline = _pipeline
        textstat = _textstat
        return True
    except Exception as exc:
        logging.warning("Pacotes de NLP indisponíveis: %s", str(exc))
        return False

# Outros
from tqdm import tqdm
warnings.filterwarnings("ignore")

# Logging padrão
logging.basicConfig(level=logging.INFO)

# Mensagem de boas-vindas
print(f"✅ Imports base carregados - StartupScan.AI [{datetime.now().strftime('%d/%m/%Y %H:%M')}]")
