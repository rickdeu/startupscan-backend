import hashlib
import json
import os

from .enricher import enrich_pitch_payload


def _build_pitch_uniqueness_key(idea_data: dict) -> str:
    raw = json.dumps(
        {
            "startup_name": idea_data.get("startup_name", ""),
            "problem": idea_data.get("problem", ""),
            "solution": idea_data.get("solution", ""),
            "target_customer": idea_data.get("target_customer", ""),
            "business_model": idea_data.get("business_model", ""),
            "model_source": idea_data.get("model_source", ""),
            "created_hint": idea_data.get("created_at", ""),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _build_gpt_system_prompt() -> str:
    return (
        "Você é um estrategista sênior de captação de investimentos com 15 anos de experiência "
        "assessorando startups em rodadas Seed, Series A e B em fundos como Softbank, Kaszek e Sequoia. "
        "Sua especialidade é transformar ideias de negócio em narrativas de investimento precisas, "
        "convincentes e altamente personalizadas — sem clichês, sem texto genérico.\n\n"
        "PRINCÍPIOS INEGOCIÁVEIS:\n"
        "1. Especificidade total: cada frase deve refletir esta startup em particular, nunca outra.\n"
        "2. Linguagem de investidor: use termos como TAM/SAM, unit economics, GTM, churn, LTV/CAC, "
        "burn rate, runway, moat, milestone — onde pertinentes ao contexto.\n"
        "3. Narrativa causal: problema → solução → mercado → tração → escala → retorno. "
        "Cada bloco deve preparar o próximo logicamente.\n"
        "4. Quantifique sempre que possível: substitua 'grande mercado' por uma estimativa com contexto, "
        "'bom crescimento' por tendência específica, 'equipe experiente' por credenciais reais se fornecidas.\n"
        "5. Elimine clichês: proibido usar 'disruptivo', 'revolucionário', 'game-changer', "
        "'solução inovadora', 'mundo melhor', 'exponencial' sem justificativa concreta.\n"
        "6. Tom: assertivo e executivo — como um CEO experiente falando com um comitê de investimentos, "
        "não como um estudante explicando um projeto.\n"
        "7. Idioma: responda integralmente em português do Brasil, linguagem formal mas não burocrática."
    )


def _build_gpt_user_prompt(idea_data: dict, uniqueness_key: str) -> str:
    s = idea_data
    startup_name = s.get("startup_name", "Startup")

    data_block = "\n".join([
        f"STARTUP: {startup_name}",
        f"ONE-LINER: {s.get('one_liner', '')}",
        f"PROBLEMA: {s.get('problem', '')}",
        f"SOLUÇÃO: {s.get('solution', '')}",
        f"CLIENTE-ALVO: {s.get('target_customer', '')}",
        f"TAMANHO DE MERCADO: {s.get('market_size', '')}",
        f"MODELO DE NEGÓCIO: {s.get('business_model', '')}",
        f"VANTAGEM COMPETITIVA: {s.get('competitive_advantage', '')}",
        f"TRAÇÃO ATUAL: {s.get('traction', '')}",
        f"TIME: {s.get('team', '')}",
        f"META DE CAPTAÇÃO: {s.get('funding_goal', '')}",
        f"USO DOS RECURSOS: {s.get('use_of_funds', '')}",
        f"CALL TO ACTION: {s.get('call_to_action', '')}",
        f"UNIQUENESS KEY: {uniqueness_key}",
    ])

    schema = """
RETORNE ESTRITAMENTE um JSON com esta estrutura (sem markdown, sem explicações fora do JSON):

{
  "title": "string — título executivo do pitch. Formato: '[Startup] — [Proposta de valor em 6-10 palavras]'",
  "slogan": "string — tagline memorável, 10-18 palavras, que capture a essência do negócio e provoque curiosidade no investidor",
  "elevator_pitch": "string — 4 a 6 frases. Abertura com o problema + impacto quantificado, apresentação da solução com diferencial real, posicionamento de mercado, sinal de tração, convite à conversa. Mínimo 280 caracteres.",
  "sections": [
    {
      "title": "Problema e Oportunidade",
      "content": "string — 3-4 frases: descreva a dor com dados de mercado, quem sofre, quanto custa o problema (tempo/dinheiro), por que ainda não foi resolvido adequadamente. Mínimo 200 chars."
    },
    {
      "title": "Solução e Diferencial",
      "content": "string — 3-4 frases: como a solução resolve a dor, o que a torna defensável (tecnologia, dados, rede, regulação), por que agora é o momento certo. Mínimo 200 chars."
    },
    {
      "title": "Mercado e Segmentação",
      "content": "string — 3-4 frases: TAM/SAM/SOM com lógica de cálculo, segmento inicial e caminho para expansão, dinâmica de crescimento do setor. Mínimo 200 chars."
    },
    {
      "title": "Modelo de Negócio e Unit Economics",
      "content": "string — 3-4 frases: como a startup ganha dinheiro, estrutura de receita (recorrente/transacional/marketplace), drivers de margem, perspectiva de LTV/CAC se aplicável. Mínimo 200 chars."
    },
    {
      "title": "Tração e Validação",
      "content": "string — 3-4 frases: evidências concretas de mercado (clientes, receita, usuários, pilotos, parcerias), velocidade de crescimento, indicador mais relevante do estágio atual. Mínimo 200 chars."
    },
    {
      "title": "Time e Capacidade de Execução",
      "content": "string — 3-4 frases: credenciais relevantes dos fundadores para este problema específico, complementaridade da equipe, advisory e network. Mínimo 200 chars."
    },
    {
      "title": "Estratégia de Go-to-Market",
      "content": "string — 3-4 frases: canal principal de aquisição, custo de aquisição esperado, parceiros estratégicos, playbook de expansão geográfica ou vertical. Mínimo 200 chars."
    },
    {
      "title": "Vantagem Competitiva e Moat",
      "content": "string — 3-4 frases: análise do landscape competitivo, o que torna a posição defensável no longo prazo (dados proprietários, efeitos de rede, switching cost, regulação, IP). Mínimo 200 chars."
    }
  ],
  "investment": {
    "funding_goal": "string — valor pedido com round stage (ex: 'R$ 3M — Rodada Seed')",
    "use_of_funds": "string — alocação em 3-4 frentes prioritárias com percentual ou valor aproximado e milestones associados. Ex: '40% produto (MVP v2 + mobile), 35% comercial (10 enterprise clientes), 25% operações (18 meses runway)'",
    "runway_months": "string — estimativa de runway com esse capital (ex: '18-22 meses')",
    "key_milestones": "string — 2-3 milestones concretos que serão atingidos com esse capital e que preparam a próxima rodada"
  },
  "script_3min": [
    "string — Passo 1: Abertura (0-20s): gancho emocional ou dado surpreendente sobre o problema",
    "string — Passo 2: Problema (20-45s): a dor específica e quem está sofrendo com ela hoje",
    "string — Passo 3: Solução (45-75s): como funciona, o diferencial técnico/comercial e por que agora",
    "string — Passo 4: Mercado e Tração (75-110s): tamanho do prêmio e evidências de que já está funcionando",
    "string — Passo 5: Time e Credibilidade (110-140s): por que este time vai ganhar este mercado",
    "string — Passo 6: Ask e Próximos Passos (140-180s): o que está pedindo, para quê e o convite direto"
  ],
  "pitch_deck": [
    {"slide": 1, "title": "Capa", "bullets": ["tagline", "nome do founder", "data e contexto do pitch"]},
    {"slide": 2, "title": "O Problema", "bullets": ["3-4 bullets com dados específicos sobre a dor"]},
    {"slide": 3, "title": "Nossa Solução", "bullets": ["3-4 bullets descrevendo funcionamento e diferencial"]},
    {"slide": 4, "title": "Mercado Endereçável", "bullets": ["TAM/SAM/SOM com lógica de cálculo", "driver de crescimento do setor"]},
    {"slide": 5, "title": "Modelo de Negócio", "bullets": ["fluxo de receita principal", "unit economics chave", "caminho para escala"]},
    {"slide": 6, "title": "Tração e Validação", "bullets": ["métricas mais relevantes", "clientes ou pilotos ativos", "velocidade de crescimento"]},
    {"slide": 7, "title": "Estratégia GTM", "bullets": ["canal principal", "custo de aquisição estimado", "expansão planejada"]},
    {"slide": 8, "title": "Vantagem Competitiva", "bullets": ["diferencial vs. alternativas", "moat de longo prazo", "por que difícil de copiar"]},
    {"slide": 9, "title": "Time", "bullets": ["fundadores com credenciais relevantes", "advisors estratégicos"]},
    {"slide": 10, "title": "Captação e Uso do Capital", "bullets": ["valor pedido e round stage", "alocação por frente", "milestones e runway"]},
    {"slide": 11, "title": "Visão e Roadmap", "bullets": ["onde estará em 18 meses", "expansão de produto ou mercado", "próxima rodada preparada"]},
    {"slide": 12, "title": "Conclusão e Call to Action", "bullets": ["resumo da tese de investimento", "convite direto e próximos passos"]}
  ],
  "closing": "string — 3-4 frases finais de impacto: síntese da tese de investimento, por que esta startup vai vencer neste mercado, e um convite claro e confiante para o próximo passo. Mínimo 180 chars."
}

REGRAS CRÍTICAS:
- Todos os campos "content" e textos longos devem refletir EXCLUSIVAMENTE os dados desta startup.
- Nunca use texto genérico como 'grande mercado', 'solução inovadora', 'equipe experiente'.
- Cada bullet do pitch_deck deve ser uma frase completa e específica (não apenas uma palavra ou label).
- O script_3min deve soar como o founder falando ao vivo — não como um roteiro corporativo.
- Use os dados fornecidos como base; onde faltam dados, faça inferências plausíveis baseadas no setor.
"""

    return f"Gere o pitch profissional completo para a seguinte startup:\n\n{data_block}\n\n{schema}"


def _local_pitch_fallback(idea_data: dict) -> dict:
    startup_name = idea_data.get("startup_name", "Startup")
    one_liner = idea_data.get("one_liner", "").strip() or (
        f"{startup_name} resolve um problema real com uma solucao escalável."
    )
    problem = idea_data.get("problem", "Dor latente com impacto direto no mercado-alvo.")
    solution = idea_data.get("solution", "Solucao orientada por dados e validada com usuarios reais.")
    target_customer = idea_data.get("target_customer", "Empresas ou consumidores com necessidade especifica.")
    market_size = idea_data.get("market_size", "Mercado em expansao com espaco para lideranca vertical.")
    business_model = idea_data.get("business_model", "Modelo de receita recorrente com margens crescentes.")
    competitive_advantage = idea_data.get("competitive_advantage", "Diferenciais tecnicos e operacionais claros.")
    traction = idea_data.get("traction", "Primeiras validacoes e metricas de engajamento em evolucao.")
    team = idea_data.get("team", "Equipe com expertise combinada em produto, tecnologia e go-to-market.")
    funding_goal = idea_data.get("funding_goal", "Nao informado")
    use_of_funds = idea_data.get("use_of_funds", "Produto, comercial e operacoes.")

    return {
        "title": f"Pitch de Negócio - {startup_name}",
        "slogan": one_liner,
        "sections": [
            {"title": "Problema", "content": problem},
            {"title": "Solucao", "content": solution},
            {"title": "Cliente-Alvo", "content": target_customer},
            {"title": "Tamanho de Mercado", "content": market_size},
            {"title": "Modelo de Negocio", "content": business_model},
            {"title": "Vantagem Competitiva", "content": competitive_advantage},
            {"title": "Tracao", "content": traction},
            {"title": "Time", "content": team},
        ],
        "investment": {
            "funding_goal": funding_goal,
            "use_of_funds": use_of_funds,
        },
        "elevator_pitch": (
            f"{startup_name} resolve {problem} entregando {solution} para {target_customer}, "
            f"operando em {market_size} com {business_model}."
        ),
        "script_3min": [],
        "pitch_deck": [],
        "closing": (
            f"Obrigado pela atencao. {startup_name} esta pronta para escalar com o suporte certo. "
            "Propomos o proximo passo: uma reuniao para revisar a tese e os milestones da rodada."
        ),
        "narrative_uniqueness_key": _build_pitch_uniqueness_key(idea_data),
        "engine_used": "local",
    }


def _normalize_payload(data: dict, engine_used: str, *, enrich: bool = True) -> dict:
    data = data if isinstance(data, dict) else {}
    data.setdefault("title", "Pitch de Negócio")
    data.setdefault("slogan", "")
    data.setdefault("sections", [])
    data.setdefault("investment", {})
    data.setdefault("closing", "")
    data.setdefault("elevator_pitch", "")
    data.setdefault("script_3min", [])
    data.setdefault("pitch_deck", [])
    data.setdefault("narrative_uniqueness_key", "")
    data.setdefault("engine_used", engine_used)
    if enrich:
        return enrich_pitch_payload(data)
    return data


def generate_pitch_from_idea(idea_data: dict, model_source: str = "local") -> dict:
    model_source = (model_source or "local").strip().lower()
    if model_source not in {"local", "gpt"}:
        model_source = "local"

    if model_source == "gpt":
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI

                model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
                client = OpenAI(api_key=api_key)
                uniqueness_key = _build_pitch_uniqueness_key(idea_data)

                response = client.chat.completions.create(
                    model=model_name,
                    temperature=0.72,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": _build_gpt_system_prompt()},
                        {"role": "user", "content": _build_gpt_user_prompt(idea_data, uniqueness_key)},
                    ],
                )
                data = json.loads(response.choices[0].message.content)
                if isinstance(data, dict):
                    data["narrative_uniqueness_key"] = uniqueness_key
                    # GPT already produces rich content — skip filler enrichment
                    return _normalize_payload(data, "gpt", enrich=False)
            except Exception:
                pass

    return _normalize_payload(_local_pitch_fallback(idea_data), "local", enrich=True)
