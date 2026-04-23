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
    s = idea_data
    startup_name = s.get("startup_name", "Startup")
    one_liner = (s.get("one_liner", "") or "").strip() or f"{startup_name}: solução escalável para um problema real de mercado."
    problem = (s.get("problem", "") or "").strip() or "Lacuna de eficiência operacional com impacto direto em custo e experiência do cliente."
    solution = (s.get("solution", "") or "").strip() or "Plataforma orientada por dados que automatiza processos críticos e entrega resultado mensurável."
    target_customer = (s.get("target_customer", "") or "").strip() or "Empresas de médio porte com necessidade de escalar operações sem aumentar headcount."
    market_size = (s.get("market_size", "") or "").strip() or "Mercado em expansão com crescimento acelerado e baixa penetração de soluções digitais."
    business_model = (s.get("business_model", "") or "").strip() or "SaaS com receita recorrente mensal, expansão por upsell e modelo de precificação por uso."
    competitive_advantage = (s.get("competitive_advantage", "") or "").strip() or "Combinação de dados proprietários, integração nativa com sistemas existentes e time especializado no setor."
    traction = (s.get("traction", "") or "").strip() or "Primeiros clientes ativos, feedbacks positivos e métricas de engajamento em crescimento consistente."
    team = (s.get("team", "") or "").strip() or "Equipe fundadora com experiência combinada em produto, tecnologia e desenvolvimento de negócios."
    funding_goal = (s.get("funding_goal", "") or "").strip() or "Não informado"
    use_of_funds = (s.get("use_of_funds", "") or "").strip() or "Desenvolvimento de produto, expansão comercial e fortalecimento da estrutura operacional."
    call_to_action = (s.get("call_to_action", "") or "").strip() or "Reunião para aprofundar a tese de investimento e alinhar próximos passos da rodada."

    elevator_pitch = (
        f"{startup_name} atua em um mercado onde {problem.lower().rstrip('.')} afeta diretamente a eficiência e "
        f"o crescimento das organizações. Nossa solução — {solution.lower().rstrip('.')} — foi desenvolvida "
        f"especificamente para {target_customer.lower().rstrip('.')}, entregando resultados concretos desde os "
        f"primeiros ciclos de uso. Operamos em {market_size.lower().rstrip('.')}, com {business_model.lower().rstrip('.')}, "
        f"o que nos posiciona para escalar com previsibilidade de receita e eficiência de aquisição. "
        f"{traction} Buscamos parceiros que compartilhem a visão de construir um negócio líder neste segmento."
    )

    sections = [
        {
            "title": "Problema e Oportunidade",
            "content": (
                f"{problem} Esta dor afeta diretamente {target_customer.lower()}, gerando custos operacionais, "
                f"ineficiências e perda de competitividade. O mercado atual carece de soluções que combinem "
                f"simplicidade de adoção com profundidade técnica para resolver este desafio de forma definitiva. "
                f"O momento é propício: a digitalização acelerada do setor amplia a janela de oportunidade para "
                f"quem chega com proposta de valor clara e capacidade de execução comprovada."
            ),
        },
        {
            "title": "Solução e Diferencial",
            "content": (
                f"{solution} A abordagem da {startup_name} se diferencia pela combinação de {competitive_advantage.lower().rstrip('.')}. "
                f"Diferente das alternativas existentes, a solução foi construída com foco em resultado mensurável "
                f"desde o primeiro uso, reduzindo o tempo de implementação e o custo de mudança para o cliente. "
                f"A arquitetura técnica permite escalar sem perda de qualidade ou aumento proporcional de custo, "
                f"criando vantagem estrutural sustentável no longo prazo."
            ),
        },
        {
            "title": "Mercado e Segmentação",
            "content": (
                f"{market_size} O segmento inicial de foco — {target_customer.lower().rstrip('.')} — representa "
                f"o ponto de entrada com maior densidade de problema e menor resistência de adoção. "
                f"A partir desta base, a {startup_name} planeja expansão para segmentos adjacentes, "
                f"ampliando o TAM endereçável sem abandonar o núcleo de competência já validado. "
                f"A dinâmica do setor favorece soluções que combinem especialização vertical com integração horizontal, "
                f"criando oportunidade para uma empresa definir o padrão do mercado."
            ),
        },
        {
            "title": "Modelo de Negócio e Unit Economics",
            "content": (
                f"{business_model} Este modelo foi escolhido pela previsibilidade de receita, baixo churn potencial "
                f"e capacidade de expansão de receita por conta sem aumento proporcional de CAC. "
                f"À medida que a base de clientes cresce, os efeitos de dados e rede ampliam o moat competitivo "
                f"e melhoram os indicadores de LTV/CAC, tornando o negócio mais robusto a cada ciclo de crescimento. "
                f"O caminho para margem positiva é claro e não depende de volumes extremos para ser viável."
            ),
        },
        {
            "title": "Tração e Validação",
            "content": (
                f"{traction} Estes indicadores validam não apenas a proposta de valor, mas também a capacidade "
                f"de execução do time em condições reais de mercado. O ritmo de crescimento atual evidencia que "
                f"o fit produto-mercado está sendo alcançado, e os feedbacks qualitativos dos primeiros clientes "
                f"confirmam a relevância do problema e a eficácia da solução. "
                f"O próximo ciclo de crescimento será acelerado com o capital desta rodada, transformando "
                f"validações iniciais em crescimento sustentado e previsível."
            ),
        },
        {
            "title": "Time e Capacidade de Execução",
            "content": (
                f"{team} A composição do time foi pensada para cobrir os pilares críticos desta fase: "
                f"desenvolvimento de produto, expansão comercial e gestão operacional. "
                f"A experiência combinada dos fundadores neste setor específico reduz o risco de execução "
                f"e acelera a curva de aprendizado frente a desafios que times genéricos levariam mais tempo para superar. "
                f"O time tem disciplina de métricas, cultura de iteração rápida e o comprometimento necessário "
                f"para navegar os desafios de crescimento desta fase."
            ),
        },
        {
            "title": "Estratégia de Go-to-Market",
            "content": (
                f"A estratégia GTM da {startup_name} prioriza canais com menor CAC e maior potencial de expansão orgânica. "
                f"O foco inicial em {target_customer.lower().rstrip('.')} permite construir casos de uso robustos, "
                f"referências comerciais e uma base de dados que alimenta tanto o produto quanto a argumentação de vendas. "
                f"Parcerias estratégicas com players estabelecidos no setor reduzem o custo de entrada e aceleram "
                f"o ciclo de vendas nos primeiros 12 meses. O playbook de expansão é replicável e escala "
                f"sem dependência de headcount proporcional."
            ),
        },
        {
            "title": "Vantagem Competitiva e Moat",
            "content": (
                f"{competitive_advantage} Esta vantagem se torna mais difícil de replicar à medida que a base "
                f"de clientes cresce, pois cada novo cliente enriquece os dados proprietários, melhora o produto "
                f"e fortalece os efeitos de rede. A {startup_name} está construindo um moat baseado em "
                f"conhecimento setorial profundo, integração técnica com fluxos críticos do cliente e uma "
                f"experiência de produto que gera dependência funcional positiva. "
                f"A barreira de entrada para novos competidores aumenta a cada trimestre de operação."
            ),
        },
    ]

    script_3min = [
        f"Passo 1 — Abertura (0-20s): Imagine perder receita e eficiência todos os dias por causa de {problem.lower().rstrip('.')}. É exatamente isso que acontece com {target_customer.lower().rstrip('.')} hoje — e ninguém resolveu isso de forma definitiva ainda.",
        f"Passo 2 — Problema (20-45s): {problem} Este problema custa às empresas tempo, dinheiro e competitividade. As soluções atuais são fragmentadas, caras de implementar ou foram construídas para outros segmentos — e por isso falham na entrega de resultado real.",
        f"Passo 3 — Solução (45-75s): {startup_name} resolve isso com {solution.lower().rstrip('.')}. O diferencial está em {competitive_advantage.lower().rstrip('.')} — o que nos permite entregar resultado desde o primeiro ciclo de uso, com adoção simples e sem meses de implementação.",
        f"Passo 4 — Mercado e Tração (75-110s): Estamos em {market_size.lower().rstrip('.')}. {traction} Estes números mostram que o mercado valida nossa abordagem e que estamos no ritmo certo para capturar uma posição relevante neste segmento.",
        f"Passo 5 — Time e Execução (110-140s): {team} Temos o conhecimento setorial, a disciplina de execução e o network para escalar com velocidade. Cada membro do time foi escolhido para cobrir os riscos críticos desta fase de crescimento.",
        f"Passo 6 — Ask e Próximos Passos (140-180s): Estamos captando {funding_goal} para {use_of_funds.lower().rstrip('.')}. Este capital nos leva aos milestones necessários para a próxima rodada em posição de força. {call_to_action}",
    ]

    pitch_deck = [
        {"slide": 1, "title": "Capa", "bullets": [
            one_liner,
            startup_name,
            "Pitch de Investimento — Rodada Seed",
        ]},
        {"slide": 2, "title": "O Problema", "bullets": [
            problem,
            f"Afeta diretamente: {target_customer}",
            "Soluções existentes são fragmentadas, caras ou foram construídas para outros contextos",
            "A janela de oportunidade está aberta — o mercado precisa de uma solução definitiva agora",
        ]},
        {"slide": 3, "title": "Nossa Solução", "bullets": [
            solution,
            f"Construída especificamente para {target_customer.lower()}",
            competitive_advantage,
            "Resultado mensurável desde o primeiro ciclo de uso — sem meses de implementação",
        ]},
        {"slide": 4, "title": "Mercado Endereçável", "bullets": [
            market_size,
            f"Segmento inicial de foco: {target_customer}",
            "Expansão para verticais adjacentes após consolidação da base inicial",
            "Dinâmica do setor favorece novos entrantes com produto superior e execução disciplinada",
        ]},
        {"slide": 5, "title": "Modelo de Negócio", "bullets": [
            business_model,
            "Receita previsível com potencial de expansão via upsell e cross-sell por conta",
            "LTV/CAC favorável com melhoria contínua à medida que a base de clientes cresce",
            "Margens crescentes com escala — estrutura de custo não cresce proporcionalmente à receita",
        ]},
        {"slide": 6, "title": "Tração e Validação", "bullets": [
            traction,
            "Feedback qualitativo confirma product-market fit em construção",
            "Métricas de engajamento e retenção acima da média do setor",
            "Primeiros clientes geram casos de uso, referências e dados para melhorar o produto",
        ]},
        {"slide": 7, "title": "Estratégia GTM", "bullets": [
            f"Canal principal: abordagem direta e consultiva a {target_customer.lower()}",
            "Parcerias estratégicas para reduzir CAC e acelerar o ciclo de vendas",
            "Playbook de expansão replicável após validação do segmento inicial",
            "Expansão geográfica e vertical planejada para 18-36 meses",
        ]},
        {"slide": 8, "title": "Vantagem Competitiva", "bullets": [
            competitive_advantage,
            "Moat crescente: dados proprietários e efeitos de rede com cada novo cliente",
            "Switching cost alto após integração com fluxos críticos do cliente",
            "Barreira técnica e de conhecimento setorial que aumenta com o tempo de operação",
        ]},
        {"slide": 9, "title": "Time", "bullets": [
            team,
            "Experiência setorial específica reduz risco de execução nesta fase",
            "Cultura de métricas, iteração rápida e foco implacável em resultado",
            "Network e advisory estratégico para abertura de portas e aceleração comercial",
        ]},
        {"slide": 10, "title": "Captação e Uso do Capital", "bullets": [
            f"Meta desta rodada: {funding_goal}",
            f"Alocação estratégica: {use_of_funds}",
            "Milestones claros e mensuráveis associados a cada frente de investimento",
            "Runway de 18-24 meses para alcançar métricas que suportam a próxima rodada",
        ]},
        {"slide": 11, "title": "Visão e Roadmap", "bullets": [
            f"{startup_name}: referência no segmento em 36 meses",
            "Expansão de produto guiada por dados e feedback dos primeiros clientes",
            "Internacionalização planejada após consolidação e domínio do mercado doméstico",
            "Próxima rodada preparada com KPIs comprovados e base sólida de crescimento",
        ]},
        {"slide": 12, "title": "Conclusão e Call to Action", "bullets": [
            f"{startup_name} — {one_liner}",
            "Mercado validado, time comprometido e solução com diferencial defensável",
            f"{call_to_action}",
            "O momento ideal para entrar é agora — antes da curva de aceleração",
        ]},
    ]

    closing = (
        f"{startup_name} representa uma tese clara: problema real e urgente, solução diferenciada com moat crescente, "
        f"mercado em expansão e time com capacidade de execução comprovada. "
        f"{traction} Este momento — antes da aceleração de crescimento — é a janela ideal para entrar com o maior upside potencial. "
        f"Propomos o próximo passo: {call_to_action.lower().rstrip('.')}, para que possamos aprofundar a diligência, "
        f"alinhar os termos da rodada e construir juntos um negócio de referência neste mercado."
    )

    return {
        "title": f"{startup_name} — {one_liner[:70]}{'...' if len(one_liner) > 70 else ''}",
        "slogan": one_liner,
        "sections": sections,
        "investment": {
            "funding_goal": funding_goal,
            "use_of_funds": use_of_funds,
            "runway_months": "18-24 meses",
            "key_milestones": (
                f"(1) Escalar base de clientes com métricas de retenção sólidas; "
                f"(2) Atingir break-even operacional ou receita recorrente que justifica próxima rodada; "
                f"(3) Consolidar o playbook de vendas replicável para expansão acelerada."
            ),
        },
        "elevator_pitch": elevator_pitch,
        "script_3min": script_3min,
        "pitch_deck": pitch_deck,
        "closing": closing,
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
