import pandas as pd
import os
from pathlib import Path
from django.conf import settings
import logging

logger = logging.getLogger(__name__)



def load_training_data():
        """Carrega os paths dos datasets padrão"""
        pitches_path = Path(settings.DATA_DIR) / 'pitches_dataset.csv'
        financials_path = Path(settings.DATA_DIR) / 'financials_dataset.csv'
        
        # Verificar existência dos arquivos
        if not all(os.path.exists(p) for p in [pitches_path, financials_path]):
            raise FileNotFoundError(
                f"Default datasets not found. Please provide paths using --pitches-data and --financials-data"
            )
        
        return pitches_path, financials_path
 


