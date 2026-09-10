"""
Built-in default prompt text, used to seed startupscan_api_prompttemplate on
first migrate and as the runtime fallback whenever no active DB row exists
for a given (engine, purpose) pair (e.g. right after a fresh `migrate` but
before the data migration below has run, or if a row was deactivated).

This module must stay free of Django model imports so it can be imported
both from the model module and from migrations without any risk of a
circular import.
"""

from startupscan_api.engines import AnalysisEngine

PURPOSE_ANALYSIS_SYSTEM = "analysis_system"
PURPOSE_ANALYSIS_USER = "analysis_user"
PURPOSE_GENERATION_SYSTEM = "generation_system"
PURPOSE_GENERATION_USER = "generation_user"

PURPOSE_CHOICES = [
    (PURPOSE_ANALYSIS_SYSTEM, "Analysis — system prompt"),
    (PURPOSE_ANALYSIS_USER, "Analysis — user prompt"),
    (PURPOSE_GENERATION_SYSTEM, "Pitch generation — system prompt"),
    (PURPOSE_GENERATION_USER, "Pitch generation — user prompt"),
]
PURPOSE_VALUES = [value for value, _ in PURPOSE_CHOICES]

# Local doesn't call an LLM (it's the sklearn model), so it has no prompts.
PROMPT_ENGINE_CHOICES = [choice for choice in AnalysisEngine.choices if choice[0] != AnalysisEngine.LOCAL]
PROMPT_ENGINE_VALUES = [value for value, _ in PROMPT_ENGINE_CHOICES]

# Placeholders use Python `string.Template` ($name / ${name}) rather than
# str.format() specifically so admins can freely include literal JSON
# examples (curly braces) in the text without ever needing to escape them.

DEFAULT_ANALYSIS_SYSTEM_PROMPT = (
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
    "5. Idioma de saída OBRIGATÓRIO para todos os campos de texto livre (summary, strengths, "
    "weaknesses, recommendations, investor_pitch, market_opportunity, competitive_position): "
    "$output_language. Os nomes das chaves do JSON continuam em português como especificado."
)

DEFAULT_ANALYSIS_USER_PROMPT = (
    "Analise a seguinte startup com profundidade e retorne EXCLUSIVAMENTE um JSON válido:\n\n"
    "STARTUP: $startup_name\n"
    "UNIQUENESS KEY: $uniqueness_key\n"
    "PITCH TEXT:\n$text\n\n"
    "DADOS FINANCEIROS: $financial_data_json\n"
    "METADADOS: $metadata_json\n\n"
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

DEFAULT_GENERATION_SYSTEM_PROMPT = (
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
    "7. Idioma de saida OBRIGATORIO para todo o texto gerado: $output_language. "
    "Os nomes das chaves do JSON continuam conforme especificado no prompt do utilizador."
)

DEFAULT_GENERATION_USER_PROMPT = (
    "Gere o pitch profissional completo para a seguinte startup:\n\n"
    "STARTUP: $startup_name\n"
    "ONE-LINER: $one_liner\n"
    "PROBLEMA: $problem\n"
    "SOLUÇÃO: $solution\n"
    "CLIENTE-ALVO: $target_customer\n"
    "TAMANHO DE MERCADO: $market_size\n"
    "MODELO DE NEGÓCIO: $business_model\n"
    "VANTAGEM COMPETITIVA: $competitive_advantage\n"
    "TRAÇÃO ATUAL: $traction\n"
    "TIME: $team\n"
    "META DE CAPTAÇÃO: $funding_goal\n"
    "USO DOS RECURSOS: $use_of_funds\n"
    "CALL TO ACTION: $call_to_action\n"
    "UNIQUENESS KEY: $uniqueness_key\n\n"
    "\nRETORNE ESTRITAMENTE um JSON com esta estrutura (sem markdown, sem explicações fora do JSON):\n\n"
    "{\n"
    '  "title": "string — título executivo do pitch. Formato: \'[Startup] — [Proposta de valor em 6-10 palavras]\'",\n'
    '  "slogan": "string — tagline memorável, 10-18 palavras, que capture a essência do negócio e provoque curiosidade no investidor",\n'
    '  "elevator_pitch": "string — 4 a 6 frases. Abertura com o problema + impacto quantificado, apresentação da solução com diferencial real, posicionamento de mercado, sinal de tração, convite à conversa. Mínimo 280 caracteres.",\n'
    '  "sections": [\n'
    "    {\n"
    '      "title": "Problema e Oportunidade",\n'
    '      "content": "string — 3-4 frases: descreva a dor com dados de mercado, quem sofre, quanto custa o problema (tempo/dinheiro), por que ainda não foi resolvido adequadamente. Mínimo 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Solução e Diferencial",\n'
    '      "content": "string — 3-4 frases: como a solução resolve a dor, o que a torna defensável (tecnologia, dados, rede, regulação), por que agora é o momento certo. Mínimo 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Mercado e Segmentação",\n'
    '      "content": "string — 3-4 frases: TAM/SAM/SOM com lógica de cálculo, segmento inicial e caminho para expansão, dinâmica de crescimento do setor. Mínimo 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Modelo de Negócio e Unit Economics",\n'
    '      "content": "string — 3-4 frases: como a startup ganha dinheiro, estrutura de receita (recorrente/transacional/marketplace), drivers de margem, perspectiva de LTV/CAC se aplicável. Mínimo 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Tração e Validação",\n'
    '      "content": "string — 3-4 frases: evidências concretas de mercado (clientes, receita, usuários, pilotos, parcerias), velocidade de crescimento, indicador mais relevante do estágio atual. Mínimo 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Time e Capacidade de Execução",\n'
    '      "content": "string — 3-4 frases: credenciais relevantes dos fundadores para este problema específico, complementaridade da equipe, advisory e network. Mínimo 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Estratégia de Go-to-Market",\n'
    '      "content": "string — 3-4 frases: canal principal de aquisição, custo de aquisição esperado, parceiros estratégicos, playbook de expansão geográfica ou vertical. Mínimo 200 chars."\n'
    "    },\n"
    "    {\n"
    '      "title": "Vantagem Competitiva e Moat",\n'
    '      "content": "string — 3-4 frases: análise do landscape competitivo, o que torna a posição defensável no longo prazo (dados proprietários, efeitos de rede, switching cost, regulação, IP). Mínimo 200 chars."\n'
    "    }\n"
    "  ],\n"
    '  "investment": {\n'
    '    "funding_goal": "string — valor pedido com round stage (ex: \'R$ 3M — Rodada Seed\')",\n'
    '    "use_of_funds": "string — alocação em 3-4 frentes prioritárias com percentual ou valor aproximado e milestones associados. Ex: \'40% produto (MVP v2 + mobile), 35% comercial (10 enterprise clientes), 25% operações (18 meses runway)\'",\n'
    '    "runway_months": "string — estimativa de runway com esse capital (ex: \'18-22 meses\')",\n'
    '    "key_milestones": "string — 2-3 milestones concretos que serão atingidos com esse capital e que preparam a próxima rodada"\n'
    "  },\n"
    '  "script_3min": [\n'
    '    "string — Passo 1: Abertura (0-20s): gancho emocional ou dado surpreendente sobre o problema",\n'
    '    "string — Passo 2: Problema (20-45s): a dor específica e quem está sofrendo com ela hoje",\n'
    '    "string — Passo 3: Solução (45-75s): como funciona, o diferencial técnico/comercial e por que agora",\n'
    '    "string — Passo 4: Mercado e Tração (75-110s): tamanho do prêmio e evidências de que já está funcionando",\n'
    '    "string — Passo 5: Time e Credibilidade (110-140s): por que este time vai ganhar este mercado",\n'
    '    "string — Passo 6: Ask e Próximos Passos (140-180s): o que está pedindo, para quê e o convite direto"\n'
    "  ],\n"
    '  "pitch_deck": [\n'
    '    {"slide": 1, "title": "Capa", "bullets": ["tagline", "nome do founder", "data e contexto do pitch"]},\n'
    '    {"slide": 2, "title": "O Problema", "bullets": ["3-4 bullets com dados específicos sobre a dor"]},\n'
    '    {"slide": 3, "title": "Nossa Solução", "bullets": ["3-4 bullets descrevendo funcionamento e diferencial"]},\n'
    '    {"slide": 4, "title": "Mercado Endereçável", "bullets": ["TAM/SAM/SOM com lógica de cálculo", "driver de crescimento do setor"]},\n'
    '    {"slide": 5, "title": "Modelo de Negócio", "bullets": ["fluxo de receita principal", "unit economics chave", "caminho para escala"]},\n'
    '    {"slide": 6, "title": "Tração e Validação", "bullets": ["métricas mais relevantes", "clientes ou pilotos ativos", "velocidade de crescimento"]},\n'
    '    {"slide": 7, "title": "Estratégia GTM", "bullets": ["canal principal", "custo de aquisição estimado", "expansão planejada"]},\n'
    '    {"slide": 8, "title": "Vantagem Competitiva", "bullets": ["diferencial vs. alternativas", "moat de longo prazo", "por que difícil de copiar"]},\n'
    '    {"slide": 9, "title": "Time", "bullets": ["fundadores com credenciais relevantes", "advisors estratégicos"]},\n'
    '    {"slide": 10, "title": "Captação e Uso do Capital", "bullets": ["valor pedido e round stage", "alocação por frente", "milestones e runway"]},\n'
    '    {"slide": 11, "title": "Visão e Roadmap", "bullets": ["onde estará em 18 meses", "expansão de produto ou mercado", "próxima rodada preparada"]},\n'
    '    {"slide": 12, "title": "Conclusão e Call to Action", "bullets": ["resumo da tese de investimento", "convite direto e próximos passos"]}\n'
    "  ],\n"
    '  "closing": "string — 3-4 frases finais de impacto: síntese da tese de investimento, por que esta startup vai vencer neste mercado, e um convite claro e confiante para o próximo passo. Mínimo 180 chars."\n'
    "}\n\n"
    "REGRAS CRÍTICAS:\n"
    "- Todos os campos \"content\" e textos longos devem refletir EXCLUSIVAMENTE os dados desta startup.\n"
    "- Nunca use texto genérico como 'grande mercado', 'solução inovadora', 'equipe experiente'.\n"
    "- Cada bullet do pitch_deck deve ser uma frase completa e específica (não apenas uma palavra ou label).\n"
    "- O script_3min deve soar como o founder falando ao vivo — não como um roteiro corporativo.\n"
    "- Use os dados fornecidos como base; onde faltam dados, faça inferências plausíveis baseadas no setor."
)

DEFAULT_PROMPTS = {
    PURPOSE_ANALYSIS_SYSTEM: DEFAULT_ANALYSIS_SYSTEM_PROMPT,
    PURPOSE_ANALYSIS_USER: DEFAULT_ANALYSIS_USER_PROMPT,
    PURPOSE_GENERATION_SYSTEM: DEFAULT_GENERATION_SYSTEM_PROMPT,
    PURPOSE_GENERATION_USER: DEFAULT_GENERATION_USER_PROMPT,
}
