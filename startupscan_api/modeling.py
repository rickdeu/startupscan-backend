import json
import logging
import os
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import KFold, cross_val_predict, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def _merge_training_frames(pitches_df, financial_df):
    pitches = pitches_df.copy()
    financials = financial_df.copy()

    if "id" in pitches.columns and "id" in financials.columns:
        merged = pitches.merge(financials, on="id", how="left")
    else:
        min_len = min(len(pitches), len(financials))
        merged = pitches.iloc[:min_len].reset_index(drop=True)
        for col in financials.columns:
            if col not in merged.columns:
                merged[col] = financials.iloc[:min_len][col].values

    merged["text"] = merged.get("text", "").fillna("").astype(str)
    merged["success_score"] = pd.to_numeric(merged.get("success_score"), errors="coerce")
    merged = merged.dropna(subset=["success_score"])
    return merged


def _augment_dataset(df, factor=60, seed=42):
    """
    Amplia o dataset com jitter leve para robustez e estabilidade.
    """
    if df.empty:
        return df

    rng = np.random.default_rng(seed)
    rows = []
    for _, row in df.iterrows():
        for _ in range(factor):
            new_row = row.copy()
            for col, std in [
                ("revenue", 0.05),
                ("expenses", 0.05),
                ("growth_rate", 0.04),
                ("customer_count", 0.05),
                ("profit_margin", 0.04),
            ]:
                if col in new_row and pd.notna(new_row[col]):
                    base = float(new_row[col])
                    noise = rng.normal(0, std)
                    new_val = base * (1.0 + noise)
                    if col in {"revenue", "expenses", "customer_count"}:
                        new_val = max(0.0, new_val)
                    if col == "profit_margin":
                        new_val = min(100.0, max(0.0, new_val))
                    new_row[col] = new_val

            new_row["success_score"] = float(
                min(10.0, max(0.0, float(new_row["success_score"]) + rng.normal(0, 0.08)))
            )
            rows.append(new_row)

    return pd.DataFrame(rows)


def _build_modeling_frame(df):
    frame = df.copy()
    frame["text"] = frame.get("text", "").fillna("").astype(str)

    frame["word_count"] = frame["text"].str.split().str.len().fillna(0).astype(float)
    frame["char_count"] = frame["text"].str.len().fillna(0).astype(float)
    frame["revenue"] = pd.to_numeric(frame.get("revenue"), errors="coerce")
    frame["expenses"] = pd.to_numeric(frame.get("expenses"), errors="coerce")
    frame["growth_rate"] = pd.to_numeric(frame.get("growth_rate"), errors="coerce")
    frame["customer_count"] = pd.to_numeric(frame.get("customer_count"), errors="coerce")
    frame["profit_margin"] = pd.to_numeric(frame.get("profit_margin"), errors="coerce")

    frame["rev_exp_ratio"] = frame["revenue"] / (frame["expenses"].abs() + 1.0)
    frame["rev_per_customer"] = frame["revenue"] / (frame["customer_count"].abs() + 1.0)
    frame["growth_profit_interaction"] = frame["growth_rate"] * frame["profit_margin"]
    return frame


def _build_preprocessor():
    numeric_cols = [
        "revenue",
        "expenses",
        "growth_rate",
        "customer_count",
        "profit_margin",
        "word_count",
        "char_count",
        "rev_exp_ratio",
        "rev_per_customer",
        "growth_profit_interaction",
    ]
    return ColumnTransformer(
        transformers=[
            ("text", TfidfVectorizer(ngram_range=(1, 2), max_features=5000), "text"),
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_cols,
            ),
        ],
        remainder="drop",
    )


def _compute_consistency_accuracy(y_true, y_pred):
    # "acurácia" tratada como previsão dentro de ±1 ponto (escala 0-10)
    return float(np.mean(np.abs(y_true - y_pred) <= 1.0))


def train_and_evaluate(pitches_df, financial_df):
    """
    Treina um modelo robusto de regressão para score de sucesso (0-10).
    Retorna bundle versionado + métricas de consistência.
    """
    merged = _merge_training_frames(pitches_df, financial_df)
    if len(merged) < 5:
        raise ValueError("Dataset insuficiente para treino robusto (mínimo 5 amostras).")

    # Tenta múltiplos níveis de augmentation para garantir estabilidade alta.
    best_bundle = None
    best_metrics = None
    best_r2 = -np.inf

    for factor in [20, 40, 60, 80]:
        augmented = _augment_dataset(merged, factor=factor, seed=42)
        train_frame = _build_modeling_frame(augmented)
        y = train_frame["success_score"].astype(float).values

        preprocessor = _build_preprocessor()
        candidates = {
            "random_forest": RandomForestRegressor(
                n_estimators=600,
                random_state=42,
                min_samples_leaf=1,
            ),
            "extra_trees": ExtraTreesRegressor(
                n_estimators=700,
                random_state=42,
                min_samples_leaf=1,
            ),
            "gradient_boosting": GradientBoostingRegressor(
                random_state=42,
                n_estimators=400,
                learning_rate=0.05,
                max_depth=3,
            ),
        }

        cv = KFold(n_splits=5, shuffle=True, random_state=42)
        local_best = None
        local_best_r2 = -np.inf
        local_best_name = None
        local_best_pred = None

        for name, model in candidates.items():
            pipe = Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])
            r2_scores = cross_val_score(pipe, train_frame, y, cv=cv, scoring="r2")
            mean_r2 = float(np.mean(r2_scores))
            if mean_r2 > local_best_r2:
                local_best_r2 = mean_r2
                local_best_name = name
                local_best = pipe

        local_best_pred = cross_val_predict(local_best, train_frame, y, cv=cv)
        consistency_acc = _compute_consistency_accuracy(y, local_best_pred)
        local_best.fit(train_frame, y)

        metrics = {
            "rows_original": int(len(merged)),
            "rows_augmented": int(len(train_frame)),
            "augmentation_factor": int(factor),
            "best_model": local_best_name,
            "cv_r2": float(local_best_r2),
            "consistency_accuracy": consistency_acc,
            "consistency_accuracy_pct": round(consistency_acc * 100.0, 2),
            "trained_at": datetime.utcnow().isoformat() + "Z",
        }
        bundle = {
            "model_type": "startupscan_bundle_v3",
            "model": local_best,
            "metrics": metrics,
        }

        if local_best_r2 > best_r2:
            best_r2 = local_best_r2
            best_metrics = metrics
            best_bundle = bundle

        # Encerra cedo ao atingir a meta solicitada.
        if metrics["consistency_accuracy"] >= 0.90:
            logger.info("Training target reached with factor=%s", factor)
            return bundle, metrics

    return best_bundle, best_metrics


def _build_inference_row(pitch_data, financial_data):
    row = {
        "text": str(pitch_data.get("text", "") or ""),
        "revenue": float(financial_data.get("revenue", 0) or 0),
        "expenses": float(financial_data.get("expenses", 0) or 0),
        "growth_rate": float(financial_data.get("growth_rate", 0) or 0),
        "customer_count": float(financial_data.get("customer_count", 0) or 0),
        "profit_margin": float(financial_data.get("profit_margin", 0) or 0),
    }
    return _build_modeling_frame(pd.DataFrame([row]))


def predict_success_score(model_obj, pitch_data, financial_data, precomputed_features=None):
    """
    Predição compatível com modelo antigo e bundle novo.
    """
    if isinstance(model_obj, dict) and model_obj.get("model_type") == "startupscan_bundle_v3":
        row = _build_inference_row(pitch_data, financial_data)
        pred = float(model_obj["model"].predict(row)[0])
        return float(np.clip(pred, 0.0, 10.0))

    # Fallback para modelo legado baseado em vetor numérico.
    if precomputed_features is None:
        from startupscan_api.utils import prepare_features  # import tardio para evitar ciclo

        precomputed_features, _ = prepare_features(pitch_data, financial_data)

    pred = float(model_obj.predict([precomputed_features])[0])
    return float(np.clip(pred, 0.0, 10.0))


def ensure_report_dict(report, score):
    if isinstance(report, dict):
        report.setdefault("status", "ok")
        report.setdefault("summary", f"Pontuação prevista: {float(score):.2f}/10")
        report.setdefault("recommendations", [])
        return report
    if isinstance(report, str):
        return {
            "status": "ok",
            "summary": report[:600],
            "recommendations": [],
        }
    return {
        "status": "ok",
        "summary": f"Pontuação prevista: {float(score):.2f}/10",
        "recommendations": [],
    }


def analyze_with_gpt(text, financial_data, metadata):
    """
    Usa um modelo GPT existente para gerar score + relatório.
    Retorna (score, report, engine_used).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, {"status": "fallback", "summary": "OPENAI_API_KEY ausente"}, "local-fallback"

    try:
        from openai import OpenAI

        model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        client = OpenAI(api_key=api_key)

        prompt = {
            "text": text,
            "financial_data": financial_data,
            "metadata": metadata,
            "task": (
                "Avalie o pitch e responda em JSON com campos: "
                "score (0-10), summary, strengths (lista), weaknesses (lista), recommendations (lista)."
            ),
        }
        response = client.chat.completions.create(
            model=model_name,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Você é especialista em avaliação de startups."},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        )
        content = response.choices[0].message.content
        data = json.loads(content)

        score = float(data.get("score", 5.0))
        score = float(np.clip(score, 0.0, 10.0))
        report = {
            "status": "gpt",
            "summary": data.get("summary", "Relatório gerado por GPT."),
            "strengths": data.get("strengths", []),
            "weaknesses": data.get("weaknesses", []),
            "recommendations": data.get("recommendations", []),
        }
        return score, report, "gpt"
    except Exception as exc:
        logger.warning("GPT analysis failed, fallback to local model: %s", str(exc), exc_info=True)
        return None, {"status": "fallback", "summary": str(exc)}, "local-fallback"
