# startupscan/imports.py

# Base
import os
import logging
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from collections import Counter

# Visualização
import matplotlib.pyplot as plt
import seaborn as sns

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

# Audio
try:
    import whisper
    import librosa
    import soundfile as sf
except ImportError:
    logging.warning("Pacotes de áudio não instalados. Use: pip install whisper librosa soundfile")
    import speech_recognition as sr  # fallback

# Vídeo
try:
    import cv2
    import mediapipe as mp
    from deepface import DeepFace
    import moviepy.editor as mp_editor
except ImportError:
    logging.warning("Pacotes de vídeo não instalados. Use: pip install opencv-python mediapipe deepface moviepy")

# NLP
try:
    from transformers import pipeline
    import textstat
except ImportError:
    logging.warning("Pacotes de NLP não instalados. Use: pip install transformers textstat")

# Outros
from tqdm import tqdm
warnings.filterwarnings("ignore")

# Logging padrão
logging.basicConfig(level=logging.INFO)

# Mensagem de boas-vindas
print(f"✅ Imports carregados - StartupScan.AI [{datetime.now().strftime('%d/%m/%Y %H:%M')}]")
