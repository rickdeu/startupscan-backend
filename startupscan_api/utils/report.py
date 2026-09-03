import hashlib
import logging
from ..commom_imports import np, ensure_plot_imports, plt

CATEGORY_KEYS = [
    "idea_clarity",
    "value_proposition",
    "innovation",
    "technical_financial_feasibility",
    "scalability",
    "target_market",
    "founding_team",
    "sustainability",
]

CATEGORY_LABELS = {
    "pt": {
        "idea_clarity": "Clareza da Ideia",
        "value_proposition": "Proposta de Valor",
        "innovation": "Inovacao",
        "technical_financial_feasibility": "Viabilidade Tecnica e Financeira",
        "scalability": "Escalabilidade",
        "target_market": "Mercado-Alvo",
        "founding_team": "Equipa Fundadora",
        "sustainability": "Sustentabilidade",
    },
    "en": {
        "idea_clarity": "Idea Clarity",
        "value_proposition": "Value Proposition",
        "innovation": "Innovation",
        "technical_financial_feasibility": "Technical & Financial Feasibility",
        "scalability": "Scalability",
        "target_market": "Target Market",
        "founding_team": "Founding Team",
        "sustainability": "Sustainability",
    },
    "ru": {
        "idea_clarity": "Ясность идеи",
        "value_proposition": "Ценностное предложение",
        "innovation": "Инновационность",
        "technical_financial_feasibility": "Техническая и финансовая целесообразность",
        "scalability": "Масштабируемость",
        "target_market": "Целевой рынок",
        "founding_team": "Команда основателей",
        "sustainability": "Устойчивость",
    },
    "de": {
        "idea_clarity": "Klarheit der Idee",
        "value_proposition": "Wertversprechen",
        "innovation": "Innovation",
        "technical_financial_feasibility": "Technische und finanzielle Machbarkeit",
        "scalability": "Skalierbarkeit",
        "target_market": "Zielmarkt",
        "founding_team": "Gruenderteam",
        "sustainability": "Nachhaltigkeit",
    },
    "es": {
        "idea_clarity": "Claridad de la Idea",
        "value_proposition": "Propuesta de Valor",
        "innovation": "Innovacion",
        "technical_financial_feasibility": "Viabilidad Tecnica y Financiera",
        "scalability": "Escalabilidad",
        "target_market": "Mercado Objetivo",
        "founding_team": "Equipo Fundador",
        "sustainability": "Sostenibilidad",
    },
    "zh-hans": {
        "idea_clarity": "创意清晰度",
        "value_proposition": "价值主张",
        "innovation": "创新性",
        "technical_financial_feasibility": "技术与财务可行性",
        "scalability": "可扩展性",
        "target_market": "目标市场",
        "founding_team": "创始团队",
        "sustainability": "可持续性",
    },
    "umb": {
        "idea_clarity": "Ombulembo yosapo",
        "value_proposition": "Etyulo lyoku eyi",
        "innovation": "Ombakumbi",
        "technical_financial_feasibility": "Okuhasa kwondaka kutya",
        "scalability": "Okukula",
        "target_market": "Ombuavo yosapo",
        "founding_team": "Onduko yeutu",
        "sustainability": "Okusongela",
    },
}

_DEFAULT_LANGUAGE = "en"


def _category_label(key: str, language: str) -> str:
    labels = CATEGORY_LABELS.get(language) or CATEGORY_LABELS[_DEFAULT_LANGUAGE]
    return labels.get(key, key.replace("_", " ").title())


# Static narrative building blocks used by the local (non-GPT) report engine.
# Kept separate from startupscan_api/i18n.py because this content is a set of
# report-writing sentence templates, not general UI copy.
REPORT_STRINGS = {
    "pt": {
        "startup_fallback_label": "startup avaliada",
        "maturity_initial": "Inicial",
        "maturity_validation": "Em validacao comercial",
        "maturity_scale": "Pronta para escala",
        "summary": "Classificacao: {maturity}. Para {startup_label}, o modelo indica score {score:.1f}/10, "
                   "com crescimento de {growth_rate:.1f}% e margem de {profit_margin:.1f}%. "
                   "Angulo estrategico: {angle}",
        "strengths": [
            "Score preditivo de sucesso em {score:.1f}/10.",
            "Crescimento reportado de {growth_rate:.1f}% com margem de {profit_margin:.1f}%.",
            "Clareza do pitch estimada em {clarity:.1f}/10.",
            "Estrutura de pitch com dados financeiros objetivos.",
        ],
        "weaknesses": [
            "Necessidade de ampliar previsibilidade de receita recorrente.",
            "Risco de execucao em expansao sem governanca operacional robusta.",
            "Dependencia de melhoria continua do storytelling para captacao.",
        ],
        "recommendations": [
            "Apresentar roadmap de 12 meses com marcos trimestrais e KPIs de tracao.",
            "Demonstrar unit economics com CAC, LTV e payback por canal de aquisicao.",
            "Priorizar investimento em receita previsivel e retencao de clientes estrategicos.",
            "Reforcar o pitch com provas de mercado (pilotos, LOIs e cases de clientes).",
        ],
        "recommendation_signature": "Assinatura narrativa unica ({key}): {angle}",
        "narrative_angles": [
            "Abordagem orientada a expansao comercial para {startup_label}.",
            "Abordagem focada em eficiencia operacional e retencao para {startup_label}.",
            "Abordagem centrada em diferenciacao competitiva para {startup_label}.",
        ],
        "thesis_high": "Startup com sinais claros de escalabilidade e capacidade de geracao de valor.",
        "thesis_mid": "Startup com potencial relevante, recomendada para rodada com metas condicionadas.",
        "thesis_low": "Startup em estagio inicial, indicada para investimento de risco controlado.",
        "ticket_high": "Rodada growth/seed+ com participacao estrategica",
        "ticket_mid": "Rodada seed com clausulas de performance e governanca",
        "ticket_low": "Pre-seed com foco em validacao de produto e mercado",
        "capital_use_plan": [
            "Acelerar aquisicao de clientes com foco em canais de maior ROI.",
            "Fortalecer produto para elevar retencao e expansao de receita.",
            "Estruturar governanca e eficiencia operacional para escala.",
        ],
        "risk_mitigation": [
            "Definir metas de unit economics com monitoramento mensal.",
            "Estabelecer ritos de governanca e prestacao de contas aos investidores.",
            "Validar hipoteses comerciais com experimentos controlados.",
        ],
        "investor_fit": [
            "Fundos seed/growth com atuacao ativa em GTM.",
            "Investidores com experiencia em SaaS/fintech B2B.",
        ],
    },
    "en": {
        "startup_fallback_label": "the evaluated startup",
        "maturity_initial": "Early stage",
        "maturity_validation": "In commercial validation",
        "maturity_scale": "Ready to scale",
        "summary": "Classification: {maturity}. For {startup_label}, the model indicates a score of {score:.1f}/10, "
                   "with {growth_rate:.1f}% growth and a {profit_margin:.1f}% margin. "
                   "Strategic angle: {angle}",
        "strengths": [
            "Predictive success score of {score:.1f}/10.",
            "Reported growth of {growth_rate:.1f}% with a {profit_margin:.1f}% margin.",
            "Pitch clarity estimated at {clarity:.1f}/10.",
            "Pitch structure backed by objective financial data.",
        ],
        "weaknesses": [
            "Needs to build more predictable recurring revenue.",
            "Execution risk in expansion without robust operational governance.",
            "Depends on continuously improving fundraising storytelling.",
        ],
        "recommendations": [
            "Present a 12-month roadmap with quarterly milestones and traction KPIs.",
            "Demonstrate unit economics with CAC, LTV, and payback per acquisition channel.",
            "Prioritize investment in predictable revenue and strategic customer retention.",
            "Strengthen the pitch with market proof (pilots, LOIs, and customer case studies).",
        ],
        "recommendation_signature": "Unique narrative signature ({key}): {angle}",
        "narrative_angles": [
            "Approach oriented toward commercial expansion for {startup_label}.",
            "Approach focused on operational efficiency and retention for {startup_label}.",
            "Approach centered on competitive differentiation for {startup_label}.",
        ],
        "thesis_high": "Startup with clear signs of scalability and value-generation capacity.",
        "thesis_mid": "Startup with meaningful potential, recommended for a round with conditional milestones.",
        "thesis_low": "Early-stage startup, suited for controlled-risk investment.",
        "ticket_high": "Growth/seed+ round with strategic participation",
        "ticket_mid": "Seed round with performance and governance clauses",
        "ticket_low": "Pre-seed focused on product and market validation",
        "capital_use_plan": [
            "Accelerate customer acquisition focused on the highest-ROI channels.",
            "Strengthen the product to increase retention and revenue expansion.",
            "Structure governance and operational efficiency for scale.",
        ],
        "risk_mitigation": [
            "Define unit-economics targets with monthly monitoring.",
            "Establish governance rituals and investor accountability reporting.",
            "Validate commercial hypotheses through controlled experiments.",
        ],
        "investor_fit": [
            "Seed/growth funds with active GTM involvement.",
            "Investors experienced in B2B SaaS/fintech.",
        ],
    },
    "ru": {
        "startup_fallback_label": "оцениваемый стартап",
        "maturity_initial": "Начальная стадия",
        "maturity_validation": "На стадии коммерческой валидации",
        "maturity_scale": "Готов к масштабированию",
        "summary": "Классификация: {maturity}. Для {startup_label} модель показывает оценку {score:.1f}/10, "
                   "с ростом {growth_rate:.1f}% и маржой {profit_margin:.1f}%. "
                   "Стратегический угол: {angle}",
        "strengths": [
            "Прогнозный балл успеха {score:.1f}/10.",
            "Заявленный рост {growth_rate:.1f}% с маржой {profit_margin:.1f}%.",
            "Ясность презентации оценена в {clarity:.1f}/10.",
            "Структура презентации подкреплена объективными финансовыми данными.",
        ],
        "weaknesses": [
            "Необходимо повысить предсказуемость регулярного дохода.",
            "Риск исполнения при расширении без надежного операционного управления.",
            "Зависимость от постоянного улучшения повествования для привлечения инвестиций.",
        ],
        "recommendations": [
            "Представить дорожную карту на 12 месяцев с квартальными этапами и KPI роста.",
            "Показать unit-экономику с CAC, LTV и сроком окупаемости по каналу привлечения.",
            "Сделать приоритетом предсказуемый доход и удержание стратегических клиентов.",
            "Усилить презентацию рыночными доказательствами (пилоты, LOI, кейсы клиентов).",
        ],
        "recommendation_signature": "Уникальная сигнатура повествования ({key}): {angle}",
        "narrative_angles": [
            "Подход, ориентированный на коммерческое расширение для {startup_label}.",
            "Подход, ориентированный на операционную эффективность и удержание для {startup_label}.",
            "Подход, ориентированный на конкурентную дифференциацию для {startup_label}.",
        ],
        "thesis_high": "Стартап с явными признаками масштабируемости и способности создавать ценность.",
        "thesis_mid": "Стартап со значительным потенциалом, рекомендуется раунд с условными целями.",
        "thesis_low": "Стартап на начальной стадии, подходит для инвестиций с контролируемым риском.",
        "ticket_high": "Раунд growth/seed+ со стратегическим участием",
        "ticket_mid": "Seed-раунд с условиями по эффективности и управлению",
        "ticket_low": "Pre-seed с фокусом на валидацию продукта и рынка",
        "capital_use_plan": [
            "Ускорить привлечение клиентов через каналы с наибольшим ROI.",
            "Усилить продукт для повышения удержания и роста дохода.",
            "Выстроить управление и операционную эффективность для масштабирования.",
        ],
        "risk_mitigation": [
            "Определить цели unit-экономики с ежемесячным мониторингом.",
            "Установить ритуалы управления и отчетности перед инвесторами.",
            "Проверить коммерческие гипотезы через контролируемые эксперименты.",
        ],
        "investor_fit": [
            "Seed/growth фонды с активным участием в GTM.",
            "Инвесторы с опытом в B2B SaaS/финтех.",
        ],
    },
    "de": {
        "startup_fallback_label": "das bewertete Startup",
        "maturity_initial": "Fruehphase",
        "maturity_validation": "In kommerzieller Validierung",
        "maturity_scale": "Bereit zur Skalierung",
        "summary": "Einstufung: {maturity}. Fuer {startup_label} zeigt das Modell einen Score von {score:.1f}/10, "
                   "mit {growth_rate:.1f}% Wachstum und {profit_margin:.1f}% Marge. "
                   "Strategischer Ansatz: {angle}",
        "strengths": [
            "Prognostizierter Erfolgs-Score von {score:.1f}/10.",
            "Berichtetes Wachstum von {growth_rate:.1f}% mit {profit_margin:.1f}% Marge.",
            "Pitch-Klarheit geschaetzt auf {clarity:.1f}/10.",
            "Pitch-Struktur gestuetzt auf objektive Finanzdaten.",
        ],
        "weaknesses": [
            "Muss vorhersagbare wiederkehrende Umsaetze weiter ausbauen.",
            "Ausfuehrungsrisiko bei Expansion ohne robuste operative Governance.",
            "Abhaengig von kontinuierlicher Verbesserung des Fundraising-Storytellings.",
        ],
        "recommendations": [
            "12-Monats-Roadmap mit vierteljaehrlichen Meilensteinen und Traction-KPIs vorlegen.",
            "Unit Economics mit CAC, LTV und Payback pro Akquisitionskanal zeigen.",
            "Investitionen in vorhersagbaren Umsatz und strategische Kundenbindung priorisieren.",
            "Pitch mit Marktbeweisen staerken (Pilotprojekte, LOIs und Kundenreferenzen).",
        ],
        "recommendation_signature": "Einzigartige Erzaehlsignatur ({key}): {angle}",
        "narrative_angles": [
            "Ansatz mit Fokus auf kommerzielle Expansion fuer {startup_label}.",
            "Ansatz mit Fokus auf operative Effizienz und Kundenbindung fuer {startup_label}.",
            "Ansatz mit Fokus auf Wettbewerbsdifferenzierung fuer {startup_label}.",
        ],
        "thesis_high": "Startup mit klaren Anzeichen fuer Skalierbarkeit und Wertschoepfungsfaehigkeit.",
        "thesis_mid": "Startup mit relevantem Potenzial, empfohlen fuer eine Runde mit bedingten Zielen.",
        "thesis_low": "Startup in der Fruehphase, geeignet fuer Investitionen mit kontrolliertem Risiko.",
        "ticket_high": "Growth-/Seed+-Runde mit strategischer Beteiligung",
        "ticket_mid": "Seed-Runde mit Performance- und Governance-Klauseln",
        "ticket_low": "Pre-Seed mit Fokus auf Produkt- und Marktvalidierung",
        "capital_use_plan": [
            "Kundenakquise mit Fokus auf die Kanaele mit dem hoechsten ROI beschleunigen.",
            "Produkt staerken, um Kundenbindung und Umsatzwachstum zu erhoehen.",
            "Governance und operative Effizienz fuer die Skalierung strukturieren.",
        ],
        "risk_mitigation": [
            "Unit-Economics-Ziele mit monatlichem Monitoring definieren.",
            "Governance-Rituale und Berichterstattung an Investoren etablieren.",
            "Geschaeftliche Hypothesen durch kontrollierte Experimente validieren.",
        ],
        "investor_fit": [
            "Seed-/Growth-Fonds mit aktivem GTM-Engagement.",
            "Investoren mit Erfahrung in B2B-SaaS/Fintech.",
        ],
    },
    "es": {
        "startup_fallback_label": "la startup evaluada",
        "maturity_initial": "Etapa inicial",
        "maturity_validation": "En validacion comercial",
        "maturity_scale": "Lista para escalar",
        "summary": "Clasificacion: {maturity}. Para {startup_label}, el modelo indica un score de {score:.1f}/10, "
                   "con un crecimiento de {growth_rate:.1f}% y un margen de {profit_margin:.1f}%. "
                   "Angulo estrategico: {angle}",
        "strengths": [
            "Score predictivo de exito de {score:.1f}/10.",
            "Crecimiento reportado de {growth_rate:.1f}% con margen de {profit_margin:.1f}%.",
            "Claridad del pitch estimada en {clarity:.1f}/10.",
            "Estructura del pitch respaldada por datos financieros objetivos.",
        ],
        "weaknesses": [
            "Necesidad de ampliar la previsibilidad de ingresos recurrentes.",
            "Riesgo de ejecucion en la expansion sin una gobernanza operativa solida.",
            "Dependencia de la mejora continua del storytelling para la captacion de fondos.",
        ],
        "recommendations": [
            "Presentar una hoja de ruta de 12 meses con hitos trimestrales y KPIs de traccion.",
            "Demostrar la economia unitaria con CAC, LTV y payback por canal de adquisicion.",
            "Priorizar la inversion en ingresos previsibles y retencion de clientes estrategicos.",
            "Reforzar el pitch con pruebas de mercado (pilotos, LOIs y casos de clientes).",
        ],
        "recommendation_signature": "Firma narrativa unica ({key}): {angle}",
        "narrative_angles": [
            "Enfoque orientado a la expansion comercial para {startup_label}.",
            "Enfoque centrado en la eficiencia operativa y la retencion para {startup_label}.",
            "Enfoque centrado en la diferenciacion competitiva para {startup_label}.",
        ],
        "thesis_high": "Startup con senales claras de escalabilidad y capacidad de generacion de valor.",
        "thesis_mid": "Startup con potencial relevante, recomendada para una ronda con metas condicionadas.",
        "thesis_low": "Startup en etapa inicial, indicada para inversion de riesgo controlado.",
        "ticket_high": "Ronda growth/seed+ con participacion estrategica",
        "ticket_mid": "Ronda seed con clausulas de rendimiento y gobernanza",
        "ticket_low": "Pre-seed enfocada en la validacion de producto y mercado",
        "capital_use_plan": [
            "Acelerar la adquisicion de clientes centrandose en los canales de mayor ROI.",
            "Fortalecer el producto para aumentar la retencion y la expansion de ingresos.",
            "Estructurar la gobernanza y la eficiencia operativa para escalar.",
        ],
        "risk_mitigation": [
            "Definir objetivos de economia unitaria con seguimiento mensual.",
            "Establecer ritos de gobernanza y rendicion de cuentas a los inversores.",
            "Validar hipotesis comerciales con experimentos controlados.",
        ],
        "investor_fit": [
            "Fondos seed/growth con participacion activa en GTM.",
            "Inversores con experiencia en SaaS/fintech B2B.",
        ],
    },
    "zh-hans": {
        "startup_fallback_label": "本次评估的创业公司",
        "maturity_initial": "早期阶段",
        "maturity_validation": "商业验证阶段",
        "maturity_scale": "已具备规模化条件",
        "summary": "分类：{maturity}。对于{startup_label}，模型给出的评分为{score:.1f}/10，"
                   "增长率为{growth_rate:.1f}%，利润率为{profit_margin:.1f}%。"
                   "战略角度：{angle}",
        "strengths": [
            "预测成功评分为{score:.1f}/10。",
            "报告增长率为{growth_rate:.1f}%，利润率为{profit_margin:.1f}%。",
            "路演清晰度评分为{clarity:.1f}/10。",
            "路演结构有客观财务数据支撑。",
        ],
        "weaknesses": [
            "需要提升经常性收入的可预测性。",
            "在缺乏健全运营治理的情况下扩张存在执行风险。",
            "融资叙事需要持续打磨。",
        ],
        "recommendations": [
            "提出以季度为节点、包含增长KPI的12个月路线图。",
            "展示按获客渠道计算的CAC、LTV和回本周期等单位经济模型。",
            "优先投入可预测收入和战略客户留存。",
            "以市场证明（试点、意向书和客户案例）强化路演内容。",
        ],
        "recommendation_signature": "独特叙事签名（{key}）：{angle}",
        "narrative_angles": [
            "面向{startup_label}的商业扩张导向方案。",
            "面向{startup_label}的运营效率与留存导向方案。",
            "面向{startup_label}的竞争差异化导向方案。",
        ],
        "thesis_high": "该创业公司展现出明确的可扩展性和价值创造能力。",
        "thesis_mid": "该创业公司具有可观潜力，建议在设定条件目标后进行融资。",
        "thesis_low": "该创业公司处于早期阶段，适合进行风险可控的投资。",
        "ticket_high": "带有战略参与的成长期/种子+轮融资",
        "ticket_mid": "附带业绩与治理条款的种子轮融资",
        "ticket_low": "专注于产品与市场验证的预种子轮融资",
        "capital_use_plan": [
            "聚焦投资回报率最高的渠道加速获客。",
            "强化产品以提升留存和收入增长。",
            "构建面向规模化的治理体系和运营效率。",
        ],
        "risk_mitigation": [
            "设定单位经济目标并进行月度监控。",
            "建立治理机制并定期向投资人报告。",
            "通过可控实验验证商业假设。",
        ],
        "investor_fit": [
            "在GTM方面积极参与的种子/成长期基金。",
            "在B2B SaaS/金融科技领域有经验的投资人。",
        ],
    },
    "umb": {
        "startup_fallback_label": "startup yina yakuandiwa",
        "maturity_initial": "Etambi lyotete",
        "maturity_validation": "Kokwenda kwa comercial",
        "maturity_scale": "Yapongoluka oku kula",
        "summary": "Otyipo: {maturity}. Ku {startup_label}, omodelo yalombolola score {score:.1f}/10, "
                   "lokukula kwa {growth_rate:.1f}% lomangisi wa {profit_margin:.1f}%. "
                   "Onjila yombiliko: {angle}",
        "strengths": [
            "Score yombiliko yesuceso {score:.1f}/10.",
            "Okukula kwalombolwiwa {growth_rate:.1f}% lomangisi wa {profit_margin:.1f}%.",
            "Elomboluilo lyapitch lyahandeka {clarity:.1f}/10.",
            "Ombangulo yapitch yina osapo yondaka yokolele.",
        ],
        "weaknesses": [
            "Sukila okuyongola oyiwikilo yombongo yokwiya lwapikangisiwa.",
            "Onganji yoku linga ongongo okuenda pokati kuhali governança yolutilo.",
            "Osukila oku pandekela storytelling okwambata ombongo.",
        ],
        "recommendations": [
            "Lomba roadmap yosanu yekwi lwomikanda lwotyipo kimwe kimwe lo KPI yokukula.",
            "Sonehisa unit economics lo CAC, LTV, lo payback konjila yokupanga akunyi.",
            "Kola oyipilamo ombongo yalombolwiwa lo okusongela akunyi vakolele.",
            "Pandekela pitch lo osapo yombuavo (pilotos, LOIs, lo cases yakunyi).",
        ],
        "recommendation_signature": "Etyulo lyokamba liokulisa ({key}): {angle}",
        "narrative_angles": [
            "Onjila yina yombiliko yokukula komercial ku {startup_label}.",
            "Onjila yina yombiliko yefeciencia lonjongo yokusongela ku {startup_label}.",
            "Onjila yina yombiliko yediferenciação komercial ku {startup_label}.",
        ],
        "thesis_high": "Startup lina otyimbo tyaholoka tyokukula lokulinga etyulo.",
        "thesis_mid": "Startup lina etyulo lyokahandeka, yalombolwiwa oku rodada lomitangi yakwatisiwa.",
        "thesis_low": "Startup yotete, yapongoluka oku investimento yonganji yakwatisiwa.",
        "ticket_high": "Rodada growth/seed+ lokwendisa kombiliko",
        "ticket_mid": "Rodada seed lomikanda yombiliko lo governança",
        "ticket_low": "Pre-seed yina ombiliko yokusonehisa oyisapo",
        "capital_use_plan": [
            "Vilisako okuandiwa kwakunyi konjila ya ROI yakilu.",
            "Pandekesa osapo oku kutumbika okusongela lokukula kwombongo.",
            "Ombangulo governança lo efeciencia okwenda kokukula.",
        ],
        "risk_mitigation": [
            "Lomba oyipilamo unit economics lokutalako kosanu.",
            "Kola governança lo okutumbula ku ovangantuve.",
            "Sonehisa oyihipotesis komercial lo oyiteste yakwatisiwa.",
        ],
        "investor_fit": [
            "Osapo seed/growth lina ombiliko ku GTM.",
            "Ovangantuve lina osapo mu SaaS/fintech B2B.",
        ],
    },
}


def _pick_by_hash(items, uniqueness_key):
    return items[int(uniqueness_key, 16) % len(items)]


def generate_interpretable_report(score, metadata, language: str = _DEFAULT_LANGUAGE):
    language = language if language in REPORT_STRINGS else _DEFAULT_LANGUAGE
    strings = REPORT_STRINGS[language]

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
    startup_label = startup_name or strings["startup_fallback_label"]

    clarity = max(0.0, min(10.0, (readability / 10.0)))
    value_proposition = max(0.0, min(10.0, score * 0.95 + sentiment_score))
    innovation = max(0.0, min(10.0, score * 0.9 + 0.8))
    feasibility = max(0.0, min(10.0, (growth_rate / 20.0) + (profit_margin / 18.0) + 2.5))
    scalability = max(0.0, min(10.0, (growth_rate / 16.0) + 2.8))
    target_market = max(0.0, min(10.0, score * 0.8 + 1.5))
    founding_team = max(0.0, min(10.0, score * 0.75 + 1.8))
    sustainability = max(0.0, min(10.0, (profit_margin / 15.0) + 3.2))

    category_scores = {
        "idea_clarity": round(clarity, 1),
        "value_proposition": round(value_proposition, 1),
        "innovation": round(innovation, 1),
        "technical_financial_feasibility": round(feasibility, 1),
        "scalability": round(scalability, 1),
        "target_market": round(target_market, 1),
        "founding_team": round(founding_team, 1),
        "sustainability": round(sustainability, 1),
    }

    if score >= 7.5:
        maturity = strings["maturity_scale"]
    elif score >= 5.0:
        maturity = strings["maturity_validation"]
    else:
        maturity = strings["maturity_initial"]

    base_strengths = [
        s.format(score=score, growth_rate=growth_rate, profit_margin=profit_margin, clarity=clarity)
        for s in strings["strengths"]
    ]
    base_weaknesses = list(strings["weaknesses"])
    base_recommendations = [s.format() if "{" not in s else s for s in strings["recommendations"]]

    angle = _pick_by_hash(strings["narrative_angles"], uniqueness_key).format(startup_label=startup_label)
    base_recommendations.insert(
        0, strings["recommendation_signature"].format(key=uniqueness_key, angle=angle)
    )

    if score >= 7.5:
        investment_thesis = strings["thesis_high"]
        suggested_ticket = strings["ticket_high"]
    elif score >= 5:
        investment_thesis = strings["thesis_mid"]
        suggested_ticket = strings["ticket_mid"]
    else:
        investment_thesis = strings["thesis_low"]
        suggested_ticket = strings["ticket_low"]

    return {
        "status": "local_report",
        "language": language,
        "summary": strings["summary"].format(
            maturity=maturity, startup_label=startup_label, score=score,
            growth_rate=growth_rate, profit_margin=profit_margin, angle=angle,
        ),
        "final_score": round(score, 1),
        "narrative_uniqueness_key": uniqueness_key,
        "category_scores": category_scores,
        "category_labels": {key: _category_label(key, language) for key in CATEGORY_KEYS},
        "strengths": base_strengths,
        "weaknesses": base_weaknesses,
        "recommendations": base_recommendations,
        "investor_pitch": {
            "investment_thesis": investment_thesis,
            "funding_readiness": maturity,
            "suggested_ticket": suggested_ticket,
            "capital_use_plan": list(strings["capital_use_plan"]),
            "risk_mitigation": list(strings["risk_mitigation"]),
            "investor_fit": list(strings["investor_fit"]),
        },
    }


def plot_feature_importance(model, feature_names):
    ensure_plot_imports()
    if plt is None:
        logging.warning("Matplotlib unavailable at runtime for plotting.")
        return
    if hasattr(model.named_steps['regressor'], 'feature_importances_'):
        importances = model.named_steps['regressor'].feature_importances_
        indices = np.argsort(importances)[::-1]
        plt.figure(figsize=(10, 6))
        plt.title("Feature Importance")
        plt.bar(range(len(importances)), importances[indices], align="center")
        plt.xticks(range(len(importances)), [feature_names[i] for i in indices], rotation=90)
        plt.tight_layout()
        plt.show()
