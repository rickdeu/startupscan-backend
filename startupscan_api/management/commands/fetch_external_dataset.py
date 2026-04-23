import os
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand


DEFAULT_SOURCE_URL = (
    "https://huggingface.co/datasets/jeffboudier/yc-companies-august-2025/"
    "resolve/main/yc-companies-august-2025.csv?download=true"
)


class Command(BaseCommand):
    help = "Fetch external startup dataset and convert to training CSVs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-url",
            type=str,
            default=DEFAULT_SOURCE_URL,
            help="Public CSV URL for external startup data",
        )
        parser.add_argument(
            "--output-prefix",
            type=str,
            default="enhanced",
            help="Prefix for generated training CSV files",
        )
        parser.add_argument(
            "--combine-with-default",
            action="store_true",
            help="Combine generated rows with default project datasets",
        )

    def handle(self, *args, **options):
        source_url = options["source_url"]
        output_prefix = options["output_prefix"]
        combine_with_default = bool(options["combine_with_default"])

        self.stdout.write(f"Fetching dataset from: {source_url}")
        raw_df = pd.read_csv(source_url)
        if raw_df.empty:
            raise ValueError("External dataset is empty.")

        pitches_df, financial_df = self._convert_to_training_frames(raw_df)

        if combine_with_default:
            pitches_default = pd.read_csv(Path(settings.DATA_DIR) / "pitches_dataset.csv")
            financial_default = pd.read_csv(Path(settings.DATA_DIR) / "financials_dataset.csv")
            pitches_df = self._concat_frames(
                pitches_default,
                pitches_df,
                required_cols=["id", "text", "audio_url", "video_url", "success_score"],
            )
            financial_df = self._concat_frames(
                financial_default,
                financial_df,
                required_cols=["id", "revenue", "expenses", "growth_rate", "customer_count", "profit_margin"],
            )

        os.makedirs(settings.DATA_DIR, exist_ok=True)
        pitches_path = Path(settings.DATA_DIR) / f"pitches_dataset_{output_prefix}.csv"
        financials_path = Path(settings.DATA_DIR) / f"financials_dataset_{output_prefix}.csv"
        pitches_df.to_csv(pitches_path, index=False)
        financial_df.to_csv(financials_path, index=False)

        self.stdout.write(self.style.SUCCESS("External dataset successfully converted."))
        self.stdout.write(f"- Pitches: {pitches_path} ({len(pitches_df)} rows)")
        self.stdout.write(f"- Financials: {financials_path} ({len(financial_df)} rows)")

    def _concat_frames(self, base_df: pd.DataFrame, ext_df: pd.DataFrame, required_cols: Iterable[str]) -> pd.DataFrame:
        base = base_df.copy()
        ext = ext_df.copy()
        for col in required_cols:
            if col not in base.columns:
                base[col] = np.nan
            if col not in ext.columns:
                ext[col] = np.nan
        merged = pd.concat([base[list(required_cols)], ext[list(required_cols)]], ignore_index=True)
        merged["id"] = np.arange(1, len(merged) + 1)
        return merged

    def _find_col(self, df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
        cols_lower = {c.lower(): c for c in df.columns}
        for cand in candidates:
            if cand.lower() in cols_lower:
                return cols_lower[cand.lower()]

        for col in df.columns:
            col_l = col.lower()
            if any(cand.lower() in col_l for cand in candidates):
                return col
        return None

    def _safe_numeric(self, series: pd.Series, default: float = 0.0) -> pd.Series:
        out = pd.to_numeric(series, errors="coerce")
        return out.fillna(default).astype(float)

    def _convert_to_training_frames(self, df: pd.DataFrame):
        work = df.copy()

        name_col = self._find_col(work, ["name", "company", "company_name", "startup_name"])
        desc_col = self._find_col(work, ["one_liner", "description", "summary", "headline"])
        industry_col = self._find_col(work, ["industry", "vertical", "category", "sector"])
        status_col = self._find_col(work, ["status", "company_status", "startup_status"])
        stage_col = self._find_col(work, ["stage", "funding_stage"])
        funding_col = self._find_col(work, ["funding_total", "raised", "total_funding", "amount_raised"])
        revenue_col = self._find_col(work, ["arr", "revenue", "annual_revenue"])
        burn_col = self._find_col(work, ["burn_rate", "monthly_burn", "expenses"])
        growth_col = self._find_col(work, ["growth_rate", "yoy_growth", "growth"])
        team_col = self._find_col(work, ["team_size", "employees", "employee_count"])

        def get_col_or_empty(col_name):
            if col_name and col_name in work.columns:
                return work[col_name].fillna("").astype(str)
            return pd.Series([""] * len(work))

        text = (
            get_col_or_empty(name_col)
            + ". "
            + get_col_or_empty(desc_col)
            + ". Setor: "
            + get_col_or_empty(industry_col)
            + ". Stage: "
            + get_col_or_empty(stage_col)
        ).str.strip()

        funding = self._safe_numeric(work[funding_col], default=500000) if funding_col else pd.Series([500000.0] * len(work))
        revenue = self._safe_numeric(work[revenue_col], default=0.0) if revenue_col else (funding * 0.15)
        expenses = self._safe_numeric(work[burn_col], default=0.0) if burn_col else (funding * 0.08)
        growth = self._safe_numeric(work[growth_col], default=20.0) if growth_col else pd.Series([20.0] * len(work))
        customer_count = self._safe_numeric(work[team_col], default=20.0) if team_col else pd.Series([20.0] * len(work))

        # Heurística de score baseada em status + funding + finanças.
        score = pd.Series([5.0] * len(work), dtype=float)
        if status_col:
            status_lower = work[status_col].fillna("").astype(str).str.lower()
            score += np.where(status_lower.str.contains("ipo|acquired|exit|unicorn"), 2.0, 0.0)
            score += np.where(status_lower.str.contains("active|operating|live"), 1.0, 0.0)
            score -= np.where(status_lower.str.contains("closed|dead|inactive|shutdown"), 2.0, 0.0)

        funding_norm = np.log1p(np.maximum(funding, 0.0))
        funding_norm = (funding_norm - funding_norm.min()) / (funding_norm.max() - funding_norm.min() + 1e-9)
        score += funding_norm * 1.5
        score += np.clip(growth / 100.0, -1.0, 2.0)

        profit_margin = ((revenue - expenses) / (np.maximum(revenue, 1.0))) * 100.0
        score += np.clip(profit_margin / 100.0, -0.8, 0.8)
        score = np.clip(score, 0.0, 10.0)

        out_id = np.arange(1, len(work) + 1)
        pitches_df = pd.DataFrame(
            {
                "id": out_id,
                "text": text,
                "audio_url": "",
                "video_url": "",
                "success_score": np.round(score, 2),
            }
        )

        financial_df = pd.DataFrame(
            {
                "id": out_id,
                "revenue": np.round(np.maximum(revenue, 0.0), 2),
                "expenses": np.round(np.maximum(expenses, 0.0), 2),
                "growth_rate": np.round(growth, 2),
                "customer_count": np.round(np.maximum(customer_count, 1.0)).astype(int),
                "profit_margin": np.round(np.clip(profit_margin, 0.0, 100.0), 2),
            }
        )

        return pitches_df, financial_df
