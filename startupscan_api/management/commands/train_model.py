import os
import json
import joblib
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from startupscan_api.modeling import train_and_evaluate
from startupscan_api.services.model_registry import get_metrics_path
import pandas as pd




class Command(BaseCommand):
    help = 'Train the pitch evaluation model with predefined datasets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model-output',
            type=str,
            default=os.path.join(settings.AI_MODELS_DIR, 'pitch_model.pkl'),
            help='Output path for trained model'
        )
        parser.add_argument(
            '--pitches-data',
            type=str,
            help='Custom path to pitches dataset CSV'
        )
        parser.add_argument(
            '--financials-data',
            type=str,
            help='Custom path to financial data CSV'
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting model training...")
        
        try:
            # 1. Load datasets
            if options['pitches_data'] and options['financials_data']:
                # Use custom paths if provided
                pitches_path = options['pitches_data']
                financials_path = options['financials_data']
            else:
                # Use default paths
                pitches_path, financials_path = self.load_training_data()

            self.stdout.write(f"Loading data from:\n- Pitches: {pitches_path}\n- Financials: {financials_path}")

            # 2. Read the datasets
            pitches_df = pd.read_csv(pitches_path)
            financial_df = pd.read_csv(financials_path)

            # 3. Train model
            model, metrics = train_and_evaluate(pitches_df, financial_df)

            # 4. Save model
            model_path = options['model_output']
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            joblib.dump(model, model_path)

            # 5. Save metrics alongside the model
            metrics_path = get_metrics_path(os.path.basename(model_path))
            with open(metrics_path, "w", encoding="utf-8") as fh:
                json.dump(metrics, fh, ensure_ascii=False, indent=2)
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ Model successfully trained and saved to {model_path}")
            )
            self.stdout.write(f"Metrics file: {metrics_path}")
            self.stdout.write(f"Training metrics:\n{metrics}")
            
            return "Training completed successfully"
            
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"❌ Error during training: {str(e)}")
            )
            raise e
    
    def load_training_data(self):
        """Loads the default dataset paths"""
        pitches_path = Path(settings.DATA_DIR) / 'pitches_dataset.csv'
        financials_path = Path(settings.DATA_DIR) / 'financials_dataset.csv'

        # Check that the files exist
        if not all(os.path.exists(p) for p in [pitches_path, financials_path]):
            raise FileNotFoundError(
                f"Default datasets not found. Please provide paths using --pitches-data and --financials-data"
            )
        
        return pitches_path, financials_path