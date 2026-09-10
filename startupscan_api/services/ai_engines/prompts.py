import json

from startupscan_api.modeling import _GPT_OUTPUT_LANGUAGE_INSTRUCTIONS, _build_uniqueness_key


def build_pitch_analysis_prompts(text, financial_data, metadata, language: str = "en"):
    """
    Builds the system/user prompt pair shared by every LLM-backed analysis
    engine (GPT, DeepSeek, Ollama), so the prompt text and JSON contract only
    live in one place.

    Returns (system_prompt, user_prompt, startup_name, uniqueness_key).
    """
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

    return system_prompt, user_prompt, startup_name, uniqueness_key
