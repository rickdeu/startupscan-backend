import hashlib
import logging
from ..commom_imports import np, ensure_plot_imports, plt


def generate_interpretable_report(score, metadata):
    score = float(max(0.0, min(10.0, score)))
    financial = metadata.get("financial", {}) if isinstance(metadata, dict) else {}
    revenue = float(financial.get("revenue", 0) or 0)
    growth_rate = float(financial.get("growth_rate", 0) or 0)
    profit_margin = float(financial.get("profit_margin", 0) or 0)
    text_meta = metadata.get("text", {}) if isinstance(metadata, dict) else {}
    readability = float(text_meta.get("readability", 50) or 50)
    sentiment_score = float(text_meta.get("sentiment_score", 0.5) or 0.5)
    startup_name = str((metadata or {}).get("startup_name", "") or "").strip() if isinstance(metadata, dict) else ""
    industry = str((metadata or {}).get("industry", "") or "").strip() if isinstance(metadata, dict) else ""

    uniqueness_raw = (
        f"{startup_name}|{industry}|{score:.3f}|{revenue:.2f}|{growth_rate:.2f}|{profit_margin:.2f}|"
        f"{text_meta.get('word_count', 0)}|{text_meta.get('dominant_topic', '')}"
    )
    uniqueness_key = hashlib.sha256(uniqueness_raw.encode("utf-8")).hexdigest()[:10]
    startup_label = startup_name or "startup avaliada"

    clarity = max(0.0, min(10.0, (readability / 10.0)))
    proposta_valor = max(0.0, min(10.0, score * 0.95 + sentiment_score))
    inovacao = max(0.0, min(10.0, score * 0.9 + 0.8))
    viabilidade = max(0.0, min(10.0, (growth_rate / 20.0) + (profit_margin / 18.0) + 2.5))
    escalabilidade = max(0.0, min(10.0, (growth_rate / 16.0) + 2.8))
    mercado_alvo = max(0.0, min(10.0, score * 0.8 + 1.5))
    equipe_fundadora = max(0.0, min(10.0, score * 0.75 + 1.8))
    sustentabilidade = max(0.0, min(10.0, (profit_margin / 15.0) + 3.2))

    category_scores = {
        "clareza_da_ideia": round(clarity, 1),
        "proposta_de_valor": round(proposta_valor, 1),
        "inovacao": round(inovacao, 1),
        "viabilidade_tecnica_financeira": round(viabilidade, 1),
        "escalabilidade": round(escalabilidade, 1),
        "mercado_alvo": round(mercado_alvo, 1),
        "equipe_fundadora": round(equipe_fundadora, 1),
        "sustentabilidade": round(sustentabilidade, 1),
    }

    maturity = "Inicial"
    if score >= 7.5:
        maturity = "Pronta para escala"
    elif score >= 5.0:
        maturity = "Em validação comercial"

    base_strengths = [
        f"Score preditivo de sucesso em {score:.1f}/10.",
        f"Crescimento reportado de {growth_rate:.1f}% com margem de {profit_margin:.1f}%.",
        f"Clareza do pitch estimada em {category_scores['clareza_da_ideia']:.1f}/10.",
        "Estrutura de pitch com dados financeiros objetivos.",
    ]
    base_weaknesses = [
        "Necessidade de ampliar previsibilidade de receita recorrente.",
        "Risco de execução em expansão sem governança operacional robusta.",
        "Dependência de melhoria contínua do storytelling para captação.",
    ]
    base_recommendations = [
        "Apresentar roadmap de 12 meses com marcos trimestrais e KPIs de tração.",
        "Demonstrar unit economics com CAC, LTV e payback por canal de aquisição.",
        "Priorizar investimento em receita previsível e retenção de clientes estratégicos.",
        "Reforçar o pitch com provas de mercado (pilotos, LOIs e cases de clientes).",
    ]

    narrative_angles = [
        f"Abordagem orientada a expansão comercial para {startup_label}.",
        f"Abordagem focada em eficiência operacional e retenção para {startup_label}.",
        f"Abordagem centrada em diferenciação competitiva para {startup_label}.",
    ]
    angle = narrative_angles[int(uniqueness_key, 16) % len(narrative_angles)]
    base_recommendations.insert(0, f"Assinatura narrativa única ({uniqueness_key}): {angle}")

    investment_thesis = (
        "Startup com sinais claros de escalabilidade e capacidade de geração de valor."
        if score >= 7.5
        else "Startup com potencial relevante, recomendada para rodada com metas condicionadas."
        if score >= 5
        else "Startup em estágio inicial, indicada para investimento de risco controlado."
    )
    suggested_ticket = (
        "Rodada growth/seed+ com participação estratégica"
        if score >= 7.5
        else "Rodada seed com cláusulas de performance e governança"
        if score >= 5
        else "Pré-seed com foco em validação de produto e mercado"
    )

    return {
        "status": "local_report",
        "summary": (
            f"Classificação: {maturity}. Para {startup_label}, o modelo indica score {score:.1f}/10, "
            f"com crescimento de {growth_rate:.1f}% e margem de {profit_margin:.1f}%. "
            f"Ângulo estratégico: {angle}"
        ),
        "final_score": round(score, 1),
        "narrative_uniqueness_key": uniqueness_key,
        "category_scores": category_scores,
        "strengths": base_strengths,
        "weaknesses": base_weaknesses,
        "recommendations": base_recommendations,
        "investor_pitch": {
            "investment_thesis": investment_thesis,
            "funding_readiness": maturity,
            "suggested_ticket": suggested_ticket,
            "capital_use_plan": [
                "Acelerar aquisição de clientes com foco em canais de maior ROI.",
                "Fortalecer produto para elevar retenção e expansão de receita.",
                "Estruturar governança e eficiência operacional para escala.",
            ],
            "risk_mitigation": [
                "Definir metas de unit economics com monitoramento mensal.",
                "Estabelecer ritos de governança e prestação de contas aos investidores.",
                "Validar hipóteses comerciais com experimentos controlados.",
            ],
            "investor_fit": [
                "Fundos seed/growth com atuação ativa em GTM.",
                "Investidores com experiência em SaaS/fintech B2B.",
            ],
        },
    }


def plot_feature_importance(model, feature_names):
    ensure_plot_imports()
    if plt is None:
        logging.warning("Matplotlib indisponível no runtime para plotagem.")
        return
    if hasattr(model.named_steps['regressor'], 'feature_importances_'):
        importances = model.named_steps['regressor'].feature_importances_
        indices = np.argsort(importances)[::-1]
        plt.figure(figsize=(10, 6))
        plt.title("Importância das Features")
        plt.bar(range(len(importances)), importances[indices], align="center")
        plt.xticks(range(len(importances)), [feature_names[i] for i in indices], rotation=90)
        plt.tight_layout()
        plt.show()
