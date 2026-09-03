import json
import logging
import os
import hashlib
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


def _build_uniqueness_key(text, financial_data, metadata):
    payload = {
        "startup_name": (metadata or {}).get("startup_name", ""),
        "industry": (metadata or {}).get("industry", ""),
        "analysis_context_id": (metadata or {}).get("analysis_context_id", ""),
        "financial_data": financial_data or {},
        "text_sample": (text or "")[:500],
        "text_len": len(text or ""),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


_GPT_UNIQUENESS_STRINGS = {
    "pt": {
        "fallback_label": "startup avaliada",
        "signature": "Analise exclusiva para {startup_label}.",
        "summary_fallback": "Avaliacao estrategica personalizada para {startup_label}. {signature}",
        "unique_line": "Construir narrativa de captacao exclusiva para {startup_label}, "
                       "com tese diferenciada de investidor ({uniqueness_key}).",
    },
    "en": {
        "fallback_label": "the evaluated startup",
        "signature": "Exclusive analysis for {startup_label}.",
        "summary_fallback": "Personalized strategic assessment for {startup_label}. {signature}",
        "unique_line": "Build an exclusive fundraising narrative for {startup_label}, "
                       "with a differentiated investor thesis ({uniqueness_key}).",
    },
    "ru": {
        "fallback_label": "оцениваемый стартап",
        "signature": "Эксклюзивный анализ для {startup_label}.",
        "summary_fallback": "Персонализированная стратегическая оценка для {startup_label}. {signature}",
        "unique_line": "Построить эксклюзивное повествование для привлечения инвестиций для {startup_label} "
                       "с уникальным инвестиционным тезисом ({uniqueness_key}).",
    },
    "de": {
        "fallback_label": "das bewertete Startup",
        "signature": "Exklusive Analyse fuer {startup_label}.",
        "summary_fallback": "Personalisierte strategische Bewertung fuer {startup_label}. {signature}",
        "unique_line": "Eine exklusive Fundraising-Erzaehlung fuer {startup_label} mit einer differenzierten "
                       "Investorenthese aufbauen ({uniqueness_key}).",
    },
    "es": {
        "fallback_label": "la startup evaluada",
        "signature": "Analisis exclusivo para {startup_label}.",
        "summary_fallback": "Evaluacion estrategica personalizada para {startup_label}. {signature}",
        "unique_line": "Construir una narrativa de captacion exclusiva para {startup_label}, "
                       "con una tesis de inversion diferenciada ({uniqueness_key}).",
    },
    "zh-hans": {
        "fallback_label": "本次评估的创业公司",
        "signature": "为{startup_label}提供的专属分析。",
        "summary_fallback": "为{startup_label}提供的个性化战略评估。{signature}",
        "unique_line": "为{startup_label}构建独特的融资叙事，并提出差异化的投资论点（{uniqueness_key}）。",
    },
    "umb": {
        "fallback_label": "startup yina yakuandiwa",
        "signature": "Elombolwilo lyokamba ku {startup_label}.",
        "summary_fallback": "Elombolwilo lyombiliko lyokamba ku {startup_label}. {signature}",
        "unique_line": "Panga etyulo lyokamba lyokwambata ombongo ku {startup_label}, "
                       "lo tese yokamba ({uniqueness_key}).",
    },
}


def _ensure_unique_report_language(report: dict, startup_name: str, uniqueness_key: str, language: str = "en"):
    strings = _GPT_UNIQUENESS_STRINGS.get(language) or _GPT_UNIQUENESS_STRINGS["en"]
    report = report if isinstance(report, dict) else {}
    summary = str(report.get("summary", "") or "").strip()
    startup_label = startup_name.strip() or strings["fallback_label"]
    signature = strings["signature"].format(startup_label=startup_label)
    if signature not in summary:
        if summary:
            summary = f"{summary} {signature}"
        else:
            summary = strings["summary_fallback"].format(startup_label=startup_label, signature=signature)
    report["summary"] = summary

    recommendations = report.get("recommendations")
    if not isinstance(recommendations, list):
        recommendations = []
    unique_line = strings["unique_line"].format(startup_label=startup_label, uniqueness_key=uniqueness_key)
    if unique_line not in recommendations:
        recommendations.insert(0, unique_line)
    report["recommendations"] = recommendations[:8]
    report["narrative_uniqueness_key"] = uniqueness_key
    return report


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
    Expands the dataset with light jitter for robustness and stability.
    """
    if df.empty:
        return df
    if factor <= 1:
        return df.copy().reset_index(drop=True)

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
    # "accuracy" treated as a prediction within ±1 point (0-10 scale)
    return float(np.mean(np.abs(y_true - y_pred) <= 1.0))


def train_and_evaluate(pitches_df, financial_df, progress_callback=None):
    """
    Trains a robust regression model for the success score (0-10).
    Returns a versioned bundle + consistency metrics.
    """
    def _progress(value, message):
        if callable(progress_callback):
            try:
                progress_callback(int(value), str(message))
            except Exception:
                pass

    _progress(5, "Unificando dados de treino")
    merged = _merge_training_frames(pitches_df, financial_df)
    if len(merged) < 5:
        raise ValueError("Dataset insuficiente para treino robusto (mínimo 5 amostras).")

    # Tries multiple augmentation levels to ensure high stability.
    best_bundle = None
    best_metrics = None
    best_r2 = -np.inf

    row_count = len(merged)
    if row_count < 200:
        factors = [20, 40, 60, 80]
    elif row_count < 1000:
        factors = [5, 10, 20]
    else:
        factors = [1, 2]

    total_iterations = max(1, len(factors) * 3)  # 3 candidates per factor
    current_iteration = 0

    for factor in factors:
        _progress(
            10 + int((current_iteration / total_iterations) * 55),
            f"Preparando dados com fator de aumento {factor}x",
        )
        augmented = _augment_dataset(merged, factor=factor, seed=42)
        train_frame = _build_modeling_frame(augmented)
        y = train_frame["success_score"].astype(float).values

        # For large datasets, we evaluate on a sample stratified by quantiles
        # to keep the training cycle time-feasible.
        eval_frame = train_frame
        if len(train_frame) > 3000:
            eval_frame = train_frame.sample(n=3000, random_state=42)
        y_eval = eval_frame["success_score"].astype(float).values

        preprocessor = _build_preprocessor()
        candidates = {
            "random_forest": RandomForestRegressor(
                n_estimators=300,
                random_state=42,
                min_samples_leaf=1,
            ),
            "extra_trees": ExtraTreesRegressor(
                n_estimators=350,
                random_state=42,
                min_samples_leaf=1,
            ),
            "gradient_boosting": GradientBoostingRegressor(
                random_state=42,
                n_estimators=250,
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
            current_iteration += 1
            pct = 12 + int((current_iteration / total_iterations) * 60)
            _progress(pct, f"Avaliando candidato: {name} (fator {factor}x)")
            pipe = Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])
            r2_scores = cross_val_score(pipe, eval_frame, y_eval, cv=cv, scoring="r2")
            mean_r2 = float(np.mean(r2_scores))
            if mean_r2 > local_best_r2:
                local_best_r2 = mean_r2
                local_best_name = name
                local_best = pipe

        _progress(75, f"Validando melhor candidato do fator {factor}x")
        local_best_pred = cross_val_predict(local_best, eval_frame, y_eval, cv=cv)
        consistency_acc = _compute_consistency_accuracy(y_eval, local_best_pred)
        _progress(82, f"Ajustando modelo final do fator {factor}x")
        local_best.fit(train_frame, y)

        metrics = {
            "rows_original": int(len(merged)),
            "rows_augmented": int(len(train_frame)),
            "rows_evaluated": int(len(eval_frame)),
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

        # Stops early once the requested target is reached.
        if metrics["consistency_accuracy"] >= 0.90:
            logger.info("Training target reached with factor=%s", factor)
            _progress(96, "Meta de consistência atingida; finalizando")
            return bundle, metrics

    _progress(96, "Finalizando seleção do melhor bundle")
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
    Prediction compatible with both the old model and the new bundle.
    """
    if isinstance(model_obj, dict) and model_obj.get("model_type") == "startupscan_bundle_v3":
        row = _build_inference_row(pitch_data, financial_data)
        pred = float(model_obj["model"].predict(row)[0])
        return float(np.clip(pred, 0.0, 10.0))

    # Fallback for the legacy model based on a numeric vector.
    if precomputed_features is None:
        from startupscan_api.utils import prepare_features  # late import to avoid circular import

        precomputed_features, _ = prepare_features(pitch_data, financial_data)

    pred = float(model_obj.predict([precomputed_features])[0])
    return float(np.clip(pred, 0.0, 10.0))


def ensure_report_dict(report, score):
    if isinstance(report, dict):
        report.setdefault("status", "ok")
        report.setdefault("summary", f"Predicted score: {float(score):.2f}/10")
        report.setdefault("recommendations", [])
        report.setdefault("category_scores", {})
        report.setdefault("final_score", round(float(score), 1))
        return report
    if isinstance(report, str):
        return {
            "status": "ok",
            "summary": report[:600],
            "recommendations": [],
            "category_scores": {},
            "final_score": round(float(score), 1),
        }
    return {
        "status": "ok",
        "summary": f"Predicted score: {float(score):.2f}/10",
        "recommendations": [],
        "category_scores": {},
        "final_score": round(float(score), 1),
    }


_GPT_OUTPUT_LANGUAGE_INSTRUCTIONS = {
    "pt": "português (Portugal/Angola), formal mas acessível",
    "en": "English, formal but approachable",
    "ru": "русский язык, официальный, но доступный стиль",
    "de": "Deutsch, formell aber zugaenglich",
    "es": "español, formal pero accesible",
    "zh-hans": "简体中文，正式但易于理解",
    "umb": "Umbundu when possible, falling back to Portuguese for technical venture-capital terms",
}


def analyze_with_gpt(text, financial_data, metadata, language: str = "en"):
    """
    Uses an existing GPT model to generate score + report.
    Returns (score, report, engine_used).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, {"status": "fallback", "summary": "OPENAI_API_KEY missing"}, "local-fallback"

    try:
        from openai import OpenAI

        model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        client = OpenAI(api_key=api_key)
        startup_name = str((metadata or {}).get("startup_name", "") or "").strip()
        uniqueness_key = _build_uniqueness_key(text, financial_data, metadata)
        output_language = _GPT_OUTPUT_LANGUAGE_INSTRUCTIONS.get(language, _GPT_OUTPUT_LANGUAGE_INSTRUCTIONS["en"])

        system_prompt = (
            "Você é um analista sênior de venture capital com 20 anos de experiência avaliando startups "
            "em rodadas Seed, Series A e B. Já avaliou mais de 500 startups e participou de comitês de "
            "investimento em fundos tier-1. Sua análise combina rigor quantitativo com visão estratégica — "
            "você identifica o que outros analistas perdem e entrega relatórios que ajudam founders a "
            "melhorar sua tese e investidores a tomar decisões fundamentadas.\n\n"
            "PRINCÍPIOS DA SUA ANÁLISE:\n"
            "1. Especificidade total: cada observação deve ser exclusiva desta startup, nunca genérica.\n"
            "2. Profundidade: vá além do óbvio — identifique riscos ocultos, oportunidades não exploradas "
            "e sinais positivos que indicam potencial real.\n"
            "3. Linguagem de VC: use PMF, unit economics, GTM, churn, LTV/CAC, burn rate, runway, moat, "
            "TAM/SAM/SOM onde pertinentes.\n"
            "4. Tom: direto, assertivo e construtivo.\n"
            f"5. Idioma de saída OBRIGATÓRIO para todos os campos de texto livre (summary, strengths, "
            f"weaknesses, recommendations, investor_pitch, market_opportunity, competitive_position): "
            f"{output_language}. Os nomes das chaves do JSON continuam em português como especificado."
        )

        user_prompt = (
            f"Analise a seguinte startup com profundidade e retorne EXCLUSIVAMENTE um JSON válido:\n\n"
            f"STARTUP: {startup_name}\n"
            f"UNIQUENESS KEY: {uniqueness_key}\n"
            f"PITCH TEXT:\n{text}\n\n"
            f"DADOS FINANCEIROS: {json.dumps(financial_data or {}, ensure_ascii=False)}\n"
            f"METADADOS: {json.dumps(metadata or {}, ensure_ascii=False)}\n\n"
            'Retorne um JSON com EXATAMENTE esta estrutura (sem markdown, sem texto fora do JSON):\n'
            '{\n'
            '  "score": <número 0.0-10.0 com uma casa decimal>,\n'
            '  "summary": "<resumo executivo em 3-4 parágrafos: (1) síntese da tese e posicionamento, '
            '(2) análise do modelo de negócio e mercado, (3) avaliação de execução e tração, '
            '(4) veredicto final com perspectiva de investimento. Mínimo 400 caracteres.>",\n'
            '  "strengths": [\n'
            '    "<ponto forte com contexto específico da startup — mínimo 80 chars cada>"\n'
            '  ],\n'
            '  "weaknesses": [\n'
            '    "<risco ou fraqueza com impacto concreto — mínimo 80 chars cada>"\n'
            '  ],\n'
            '  "recommendations": [\n'
            '    "<recomendação acionável: o que fazer, como e resultado esperado — mínimo 80 chars cada>"\n'
            '  ],\n'
            '  "category_scores": {\n'
            '    "problema_e_oportunidade": <0.0-10.0>,\n'
            '    "solucao_e_diferencial": <0.0-10.0>,\n'
            '    "mercado_e_segmentacao": <0.0-10.0>,\n'
            '    "modelo_de_negocio": <0.0-10.0>,\n'
            '    "tracao_e_validacao": <0.0-10.0>,\n'
            '    "time_e_execucao": <0.0-10.0>,\n'
            '    "vantagem_competitiva": <0.0-10.0>,\n'
            '    "potencial_de_captacao": <0.0-10.0>\n'
            '  },\n'
            '  "investor_pitch": {\n'
            '    "investment_thesis": "<tese de investimento em 3-4 frases — mínimo 200 chars>",\n'
            '    "funding_readiness": "<Early/Ready/Strong + justificativa de 2-3 frases>",\n'
            '    "suggested_ticket": "<ticket sugerido com justificativa>",\n'
            '    "key_risks_for_investor": "<2-3 riscos principais que um investidor deve monitorar>",\n'
            '    "expected_return_profile": "<perfil de retorno esperado com horizonte e múltiplo estimado>"\n'
            '  },\n'
            '  "market_opportunity": "<análise de mercado em 2-3 frases — mínimo 150 chars>",\n'
            '  "competitive_position": "<posicionamento competitivo em 2-3 frases — mínimo 150 chars>"\n'
            '}\n\n'
            "REGRAS: nunca use texto genérico; category_scores coerentes com score final; "
            "strengths/weaknesses/recommendations são listas de strings simples."
        )

        response = client.chat.completions.create(
            model=model_name,
            temperature=0.65,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content
        data = json.loads(content)

        score = float(data.get("score", 5.0))
        score = float(np.clip(score, 0.0, 10.0))
        report = {
            "status": "gpt",
            "summary": data.get("summary", "Report generated by GPT."),
            "strengths": data.get("strengths", []),
            "weaknesses": data.get("weaknesses", []),
            "recommendations": data.get("recommendations", []),
            "category_scores": data.get("category_scores", {}),
            "investor_pitch": data.get("investor_pitch", {}),
            "market_opportunity": data.get("market_opportunity", ""),
            "competitive_position": data.get("competitive_position", ""),
        }
        report = _ensure_unique_report_language(report, startup_name, uniqueness_key, language)
        return score, report, "gpt"
    except Exception as exc:
        logger.warning("GPT analysis failed, fallback to local model: %s", str(exc), exc_info=True)
        return None, {"status": "fallback", "summary": str(exc)}, "local-fallback"
