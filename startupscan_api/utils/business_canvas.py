"""
Generates Business Model Canvas content for the Pro-tier PDF report.

The canvas is derived from the pitch analysis itself (financials, industry,
category scores, investor thesis) rather than calling an external LLM, so it
is available offline and at no extra cost, consistent with the local report
engine in startupscan_api/utils/report.py.
"""

BLOCK_KEYS = [
    "key_partners",
    "key_activities",
    "key_resources",
    "value_propositions",
    "customer_relationships",
    "channels",
    "customer_segments",
    "cost_structure",
    "revenue_streams",
]

BLOCK_TITLES = {
    "pt": {
        "key_partners": "Parcerias Chave",
        "key_activities": "Atividades Chave",
        "key_resources": "Recursos Chave",
        "value_propositions": "Proposta de Valor",
        "customer_relationships": "Relacionamento com Clientes",
        "channels": "Canais",
        "customer_segments": "Segmentos de Clientes",
        "cost_structure": "Estrutura de Custos",
        "revenue_streams": "Fontes de Receita",
    },
    "en": {
        "key_partners": "Key Partners",
        "key_activities": "Key Activities",
        "key_resources": "Key Resources",
        "value_propositions": "Value Propositions",
        "customer_relationships": "Customer Relationships",
        "channels": "Channels",
        "customer_segments": "Customer Segments",
        "cost_structure": "Cost Structure",
        "revenue_streams": "Revenue Streams",
    },
    "ru": {
        "key_partners": "Ключевые партнеры",
        "key_activities": "Ключевые виды деятельности",
        "key_resources": "Ключевые ресурсы",
        "value_propositions": "Ценностные предложения",
        "customer_relationships": "Отношения с клиентами",
        "channels": "Каналы сбыта",
        "customer_segments": "Сегменты клиентов",
        "cost_structure": "Структура издержек",
        "revenue_streams": "Потоки доходов",
    },
    "de": {
        "key_partners": "Schluesselpartner",
        "key_activities": "Schluesselaktivitaeten",
        "key_resources": "Schluesselressourcen",
        "value_propositions": "Wertversprechen",
        "customer_relationships": "Kundenbeziehungen",
        "channels": "Kanaele",
        "customer_segments": "Kundensegmente",
        "cost_structure": "Kostenstruktur",
        "revenue_streams": "Einnahmequellen",
    },
    "es": {
        "key_partners": "Socios Clave",
        "key_activities": "Actividades Clave",
        "key_resources": "Recursos Clave",
        "value_propositions": "Propuesta de Valor",
        "customer_relationships": "Relacion con Clientes",
        "channels": "Canales",
        "customer_segments": "Segmentos de Clientes",
        "cost_structure": "Estructura de Costos",
        "revenue_streams": "Fuentes de Ingresos",
    },
    "zh-hans": {
        "key_partners": "关键合作伙伴",
        "key_activities": "关键业务",
        "key_resources": "核心资源",
        "value_propositions": "价值主张",
        "customer_relationships": "客户关系",
        "channels": "渠道通路",
        "customer_segments": "客户细分",
        "cost_structure": "成本结构",
        "revenue_streams": "收入来源",
    },
    "umb": {
        "key_partners": "Ovanepange Vakolele",
        "key_activities": "Oyilinga Yokolele",
        "key_resources": "Osapo Yokolele",
        "value_propositions": "Etyulo lyoku Eyi",
        "customer_relationships": "Ombangulo ku Akunyi",
        "channels": "Onjila Yokusongela",
        "customer_segments": "Osapo ya Akunyi",
        "cost_structure": "Ombangulo yombongo",
        "revenue_streams": "Osapo yombongo",
    },
}

SECTION_TITLE = {
    "pt": "Modelo de Negocio (Business Model Canvas)",
    "en": "Business Model Canvas",
    "ru": "Канва бизнес-модели",
    "de": "Business Model Canvas",
    "es": "Lienzo de Modelo de Negocio (Business Model Canvas)",
    "zh-hans": "商业模式画布",
    "umb": "Modelo yeutu wombongo (Business Model Canvas)",
}

SECTION_INTRO = {
    "pt": "Estrutura estrategica de {startup_label} organizada nos nove blocos classicos do Business Model Canvas, com base nos dados financeiros, na industria e na analise submetida.",
    "en": "Strategic structure of {startup_label} organized across the nine classic Business Model Canvas blocks, based on the submitted financial data, industry, and analysis.",
    "ru": "Стратегическая структура {startup_label}, организованная по девяти классическим блокам Business Model Canvas на основе представленных финансовых данных, отрасли и анализа.",
    "de": "Strategische Struktur von {startup_label}, gegliedert in die neun klassischen Bloecke des Business Model Canvas, basierend auf den eingereichten Finanzdaten, der Branche und der Analyse.",
    "es": "Estructura estrategica de {startup_label} organizada en los nueve bloques clasicos del Business Model Canvas, basada en los datos financieros, la industria y el analisis presentados.",
    "zh-hans": "基于所提交的财务数据、所属行业及分析结果，围绕商业模式画布的九大经典模块梳理{startup_label}的战略结构。",
    "umb": "Ombangulo yombiliko ya {startup_label} yina yalombolwiwa mu tyipo tyivali tya Business Model Canvas, okuenda kosapo yombongo, industria, lo elombolwilo lyasonehiwa.",
}

_TEMPLATES = {
    "pt": {
        "key_partners": [
            "Fornecedores de tecnologia e infraestrutura que reduzem o tempo de lancamento de {startup_label}.",
            "Parceiros de distribuicao e canal alinhados com a cadeia de valor do setor {industry_label}.",
            "Parceiros financeiros e de pagamento que suportam o volume reportado de {revenue:,.0f} AOA.",
        ],
        "key_activities": [
            "Desenvolvimento continuo de produto guiado pela proposta de valor apresentada no pitch.",
            "Aquisicao e retencao de clientes, sustentando o crescimento reportado de {growth_rate:.1f}%.",
            "Execucao operacional para manter uma margem de {profit_margin:.1f}% a escala.",
        ],
        "key_resources": [
            "Capacidades da equipa fundadora destacadas na analise (score: {founding_team_score:.1f}/10).",
            "Ativos de produto, marca e tracao inicial descritos na submissao.",
            "Capital de giro para suportar {revenue:,.0f} AOA em operacoes reportadas.",
        ],
        "value_propositions": [
            "Proposta de valor central de {startup_label} (avaliada em {value_prop_score:.1f}/10), endereçando um problema claro no setor {industry_label}.",
            "Posicionamento diferenciado face a alternativas estabelecidas no setor.",
            "Resultados mensuraveis para os clientes, sustentados pela narrativa do pitch.",
        ],
        "customer_relationships": [
            "Envolvimento e suporte direto durante a aquisicao inicial de clientes.",
            "Taticas de confianca e comunidade adequadas ao setor {industry_label}.",
            "Programas de retencao alinhados com o perfil de mercado-alvo (score: {target_market_score:.1f}/10).",
        ],
        "channels": [
            "Canal(is) principal(is) de go-to-market implicados pelo pitch e pelas normas do setor.",
            "Canais digitais e/ou presenciais adequados para alcancar o mercado-alvo.",
            "Distribuicao via parcerias para ampliar alcance sem aumento proporcional de custo.",
        ],
        "customer_segments": [
            "Segmento primario: clientes e organizacoes do setor {industry_label} com o problema descrito no pitch.",
            "Segmento secundario: compradores adjacentes que beneficiam da mesma proposta de valor.",
        ],
        "cost_structure": [
            "Base de custos consistente com a margem de lucro reportada de {profit_margin:.1f}%.",
            "Principais fatores de custo: equipa, tecnologia/infraestrutura e aquisicao de clientes.",
            "Consideracoes de burn rate mensal relevantes para escalar de forma sustentavel.",
        ],
        "revenue_streams": [
            "Fonte de receita primaria reflectida nos {revenue:,.0f} AOA reportados.",
            "Trajetoria de crescimento de {growth_rate:.1f}% conforme submetido na analise.",
            "Potenciais fontes de receita secundarias a medida que o negocio escala (ticket sugerido: {suggested_ticket}).",
        ],
    },
    "en": {
        "key_partners": [
            "Technology and infrastructure vendors that reduce time-to-market for {startup_label}.",
            "Distribution and channel partners aligned with the {industry_label} value chain.",
            "Financial and payment partners supporting the reported {revenue:,.0f} AOA in volume.",
        ],
        "key_activities": [
            "Continuous product development guided by the value proposition stated in the pitch.",
            "Customer acquisition and retention activities sustaining the reported {growth_rate:.1f}% growth.",
            "Operational execution to sustain a {profit_margin:.1f}% margin at scale.",
        ],
        "key_resources": [
            "Founding team capabilities highlighted in the analysis (score: {founding_team_score:.1f}/10).",
            "Product, brand, and early-traction assets described in the submission.",
            "Working capital to support the reported {revenue:,.0f} AOA in operations.",
        ],
        "value_propositions": [
            "{startup_label}'s core value proposition (scored {value_prop_score:.1f}/10), addressing a clear problem in {industry_label}.",
            "Differentiated positioning versus established alternatives in the sector.",
            "Measurable outcomes for customers, supported by the pitch narrative.",
        ],
        "customer_relationships": [
            "Direct engagement and support during early customer acquisition.",
            "Trust- and community-building tactics suited to the {industry_label} sector.",
            "Retention programs aligned with the target-market profile (score: {target_market_score:.1f}/10).",
        ],
        "channels": [
            "Primary go-to-market channel(s) implied by the submitted pitch and industry norms.",
            "Digital and/or field channels appropriate for reaching the target market.",
            "Partnership-driven distribution to extend reach without a proportional cost increase.",
        ],
        "customer_segments": [
            "Primary segment: customers and organizations in {industry_label} facing the problem described in the pitch.",
            "Secondary segment: adjacent buyers who benefit from the same value proposition.",
        ],
        "cost_structure": [
            "Cost base consistent with the reported {profit_margin:.1f}% profit margin.",
            "Key cost drivers: team, technology/infrastructure, and customer acquisition.",
            "Monthly burn-rate considerations relevant to scaling sustainably.",
        ],
        "revenue_streams": [
            "Primary revenue stream reflected in the reported {revenue:,.0f} AOA.",
            "Growth trajectory of {growth_rate:.1f}% as submitted in the analysis.",
            "Potential secondary revenue streams as the business scales (suggested ticket: {suggested_ticket}).",
        ],
    },
    "ru": {
        "key_partners": [
            "Поставщики технологий и инфраструктуры, сокращающие время выхода на рынок для {startup_label}.",
            "Партнеры по дистрибуции и каналам, соответствующие цепочке создания стоимости в отрасли {industry_label}.",
            "Финансовые и платежные партнеры, поддерживающие заявленный объем в {revenue:,.0f} AOA.",
        ],
        "key_activities": [
            "Непрерывная разработка продукта на основе ценностного предложения из презентации.",
            "Привлечение и удержание клиентов, поддерживающие заявленный рост {growth_rate:.1f}%.",
            "Операционная деятельность для поддержания маржи {profit_margin:.1f}% при масштабировании.",
        ],
        "key_resources": [
            "Возможности команды основателей, отмеченные в анализе (оценка: {founding_team_score:.1f}/10).",
            "Продукт, бренд и активы раннего роста, описанные в заявке.",
            "Оборотный капитал для поддержания заявленных операций на {revenue:,.0f} AOA.",
        ],
        "value_propositions": [
            "Основное ценностное предложение {startup_label} (оценка {value_prop_score:.1f}/10), решающее конкретную проблему в отрасли {industry_label}.",
            "Дифференцированное позиционирование по сравнению с существующими альтернативами в отрасли.",
            "Измеримые результаты для клиентов, подтвержденные повествованием презентации.",
        ],
        "customer_relationships": [
            "Прямое взаимодействие и поддержка на этапе привлечения первых клиентов.",
            "Тактики построения доверия и сообщества, подходящие для отрасли {industry_label}.",
            "Программы удержания, соответствующие профилю целевого рынка (оценка: {target_market_score:.1f}/10).",
        ],
        "channels": [
            "Основной(ые) канал(ы) выхода на рынок, подразумеваемый(ые) презентацией и нормами отрасли.",
            "Цифровые и/или прямые каналы для охвата целевого рынка.",
            "Партнерское распространение для расширения охвата без пропорционального роста затрат.",
        ],
        "customer_segments": [
            "Основной сегмент: клиенты и организации в отрасли {industry_label}, сталкивающиеся с проблемой из презентации.",
            "Дополнительный сегмент: смежные покупатели, получающие выгоду от того же ценностного предложения.",
        ],
        "cost_structure": [
            "Структура затрат, соответствующая заявленной марже прибыли {profit_margin:.1f}%.",
            "Основные статьи расходов: команда, технологии/инфраструктура и привлечение клиентов.",
            "Учет ежемесячного расхода средств, важный для устойчивого масштабирования.",
        ],
        "revenue_streams": [
            "Основной источник дохода отражен в заявленных {revenue:,.0f} AOA.",
            "Траектория роста {growth_rate:.1f}%, указанная в анализе.",
            "Потенциальные дополнительные источники дохода по мере масштабирования (рекомендуемый чек: {suggested_ticket}).",
        ],
    },
    "de": {
        "key_partners": [
            "Technologie- und Infrastrukturanbieter, die die Time-to-Market fuer {startup_label} verkuerzen.",
            "Vertriebs- und Kanalpartner entlang der Wertschoepfungskette der Branche {industry_label}.",
            "Finanz- und Zahlungspartner zur Unterstuetzung des gemeldeten Volumens von {revenue:,.0f} AOA.",
        ],
        "key_activities": [
            "Kontinuierliche Produktentwicklung entlang des im Pitch dargestellten Wertversprechens.",
            "Kundengewinnung und -bindung zur Unterstuetzung des gemeldeten Wachstums von {growth_rate:.1f}%.",
            "Operative Umsetzung zur Aufrechterhaltung einer Marge von {profit_margin:.1f}% bei Skalierung.",
        ],
        "key_resources": [
            "In der Analyse hervorgehobene Faehigkeiten des Gruenderteams (Score: {founding_team_score:.1f}/10).",
            "In der Einreichung beschriebene Produkt-, Marken- und Traction-Assets.",
            "Betriebskapital zur Unterstuetzung der gemeldeten {revenue:,.0f} AOA im operativen Geschaeft.",
        ],
        "value_propositions": [
            "Kernwertversprechen von {startup_label} (bewertet mit {value_prop_score:.1f}/10), das ein klares Problem in {industry_label} loest.",
            "Differenzierte Positionierung gegenueber etablierten Alternativen in der Branche.",
            "Messbare Ergebnisse fuer Kunden, gestuetzt durch die Pitch-Erzaehlung.",
        ],
        "customer_relationships": [
            "Direkte Betreuung und Unterstuetzung waehrend der fruehen Kundengewinnung.",
            "Vertrauens- und Community-Aufbau passend zur Branche {industry_label}.",
            "Bindungsprogramme abgestimmt auf das Zielmarktprofil (Score: {target_market_score:.1f}/10).",
        ],
        "channels": [
            "Primaere Go-to-Market-Kanaele, die sich aus Pitch und Branchennormen ergeben.",
            "Digitale und/oder persoenliche Kanaele zur Erreichung des Zielmarkts.",
            "Partnerschaftsgestuetzter Vertrieb zur Reichweitensteigerung ohne proportionale Kostensteigerung.",
        ],
        "customer_segments": [
            "Primaeres Segment: Kunden und Organisationen in {industry_label} mit dem im Pitch beschriebenen Problem.",
            "Sekundaeres Segment: angrenzende Kaeufer, die vom gleichen Wertversprechen profitieren.",
        ],
        "cost_structure": [
            "Kostenbasis im Einklang mit der gemeldeten Gewinnmarge von {profit_margin:.1f}%.",
            "Wesentliche Kostentreiber: Team, Technologie/Infrastruktur und Kundengewinnung.",
            "Monatliche Burn-Rate-Ueberlegungen fuer nachhaltiges Skalieren.",
        ],
        "revenue_streams": [
            "Primaere Einnahmequelle, abgebildet in den gemeldeten {revenue:,.0f} AOA.",
            "Wachstumsverlauf von {growth_rate:.1f}% gemaess Analyse.",
            "Potenzielle zusaetzliche Einnahmequellen bei Skalierung (empfohlenes Ticket: {suggested_ticket}).",
        ],
    },
    "es": {
        "key_partners": [
            "Proveedores de tecnologia e infraestructura que reducen el tiempo de lanzamiento de {startup_label}.",
            "Socios de distribucion y canal alineados con la cadena de valor del sector {industry_label}.",
            "Socios financieros y de pago que respaldan el volumen reportado de {revenue:,.0f} AOA.",
        ],
        "key_activities": [
            "Desarrollo continuo de producto guiado por la propuesta de valor presentada en el pitch.",
            "Adquisicion y retencion de clientes que sostienen el crecimiento reportado de {growth_rate:.1f}%.",
            "Ejecucion operativa para mantener un margen de {profit_margin:.1f}% al escalar.",
        ],
        "key_resources": [
            "Capacidades del equipo fundador destacadas en el analisis (puntuacion: {founding_team_score:.1f}/10).",
            "Activos de producto, marca y traccion inicial descritos en la presentacion.",
            "Capital de trabajo para sostener {revenue:,.0f} AOA en operaciones reportadas.",
        ],
        "value_propositions": [
            "Propuesta de valor central de {startup_label} (puntuada en {value_prop_score:.1f}/10), que aborda un problema claro en {industry_label}.",
            "Posicionamiento diferenciado frente a alternativas establecidas en el sector.",
            "Resultados medibles para los clientes, respaldados por la narrativa del pitch.",
        ],
        "customer_relationships": [
            "Compromiso y apoyo directo durante la adquisicion inicial de clientes.",
            "Tacticas de confianza y comunidad adecuadas para el sector {industry_label}.",
            "Programas de retencion alineados con el perfil de mercado objetivo (puntuacion: {target_market_score:.1f}/10).",
        ],
        "channels": [
            "Canal(es) principal(es) de salida al mercado implicados por el pitch y las normas del sector.",
            "Canales digitales y/o presenciales adecuados para alcanzar el mercado objetivo.",
            "Distribucion mediante alianzas para ampliar el alcance sin aumento proporcional de costos.",
        ],
        "customer_segments": [
            "Segmento primario: clientes y organizaciones del sector {industry_label} con el problema descrito en el pitch.",
            "Segmento secundario: compradores adyacentes que se benefician de la misma propuesta de valor.",
        ],
        "cost_structure": [
            "Base de costos consistente con el margen de utilidad reportado de {profit_margin:.1f}%.",
            "Principales impulsores de costos: equipo, tecnologia/infraestructura y adquisicion de clientes.",
            "Consideraciones de burn rate mensual relevantes para escalar de forma sostenible.",
        ],
        "revenue_streams": [
            "Fuente de ingresos principal reflejada en los {revenue:,.0f} AOA reportados.",
            "Trayectoria de crecimiento de {growth_rate:.1f}% segun lo presentado en el analisis.",
            "Posibles fuentes de ingresos secundarias a medida que el negocio escala (ticket sugerido: {suggested_ticket}).",
        ],
    },
    "zh-hans": {
        "key_partners": [
            "能够缩短{startup_label}上市时间的技术与基础设施供应商。",
            "与{industry_label}行业价值链相匹配的分销与渠道合作伙伴。",
            "支持所报告{revenue:,.0f}AOA交易量的金融与支付合作伙伴。",
        ],
        "key_activities": [
            "围绕路演中提出的价值主张持续进行产品开发。",
            "支撑所报告{growth_rate:.1f}%增长率的获客与留存活动。",
            "在规模化过程中维持{profit_margin:.1f}%利润率的运营执行。",
        ],
        "key_resources": [
            "分析中重点提及的创始团队能力（评分：{founding_team_score:.1f}/10）。",
            "申报材料中描述的产品、品牌及早期增长资产。",
            "支持所报告{revenue:,.0f}AOA运营规模的营运资金。",
        ],
        "value_propositions": [
            "{startup_label}的核心价值主张（评分{value_prop_score:.1f}/10），解决了{industry_label}行业中的一个明确问题。",
            "相较于行业内现有替代方案的差异化定位。",
            "由路演叙述支撑、可衡量的客户成果。",
        ],
        "customer_relationships": [
            "在早期获客阶段提供直接互动与支持。",
            "适合{industry_label}行业的信任与社群建设策略。",
            "与目标市场画像相匹配的留存计划（评分：{target_market_score:.1f}/10）。",
        ],
        "channels": [
            "由路演内容及行业惯例所隐含的主要市场进入渠道。",
            "适合触达目标市场的数字和/或线下渠道。",
            "以合作伙伴驱动的分销方式在不成比例增加成本的情况下扩大覆盖面。",
        ],
        "customer_segments": [
            "主要细分市场：{industry_label}行业中面临路演所述问题的客户与组织。",
            "次要细分市场：受益于相同价值主张的相邻买家群体。",
        ],
        "cost_structure": [
            "与所报告{profit_margin:.1f}%利润率相符的成本基础。",
            "主要成本驱动因素：团队、技术/基础设施与获客成本。",
            "与可持续规模化相关的月度烧钱率考量。",
        ],
        "revenue_streams": [
            "反映在所报告{revenue:,.0f}AOA中的主要收入来源。",
            "分析中所示{growth_rate:.1f}%的增长轨迹。",
            "随业务规模化而产生的潜在次要收入来源（建议投资额：{suggested_ticket}）。",
        ],
    },
    "umb": {
        "key_partners": [
            "Ovanepange votecnologia lo infraestrutura vokutumbika oku {startup_label} okwenda liwa.",
            "Ovanepange vokusongela lokwalusako komukanda wombiliko wa {industry_label}.",
            "Ovanepange vombongo lo vopagamento vokutumbika osapo ya {revenue:,.0f} AOA.",
        ],
        "key_activities": [
            "Okulinga upange wombiliko okwenda ketyulo lyoku eyi lyapitch.",
            "Oyilinga yokuandiwa lo okusongela akunyi, okutumbika okukula kwa {growth_rate:.1f}%.",
            "Okulinga kwoperação oku tumbika omangisi wa {profit_margin:.1f}% ndokukula.",
        ],
        "key_resources": [
            "Oyipulukusu yeutu wombangi yalombolwiwa ku elombolwilo (score: {founding_team_score:.1f}/10).",
            "Osapo yombangulo, yomake, lo yotecção yotete yalombolwiwa ku submissão.",
            "Ombongo yokulinga oku tumbika {revenue:,.0f} AOA mu operações.",
        ],
        "value_propositions": [
            "Etyulo lyoku eyi lyokolele lya {startup_label} (score {value_prop_score:.1f}/10), lyokwiyako ongongo yokahandeka mu {industry_label}.",
            "Ombangulo yaholoka pokati kwovakuavo lokolele mu industria.",
            "Oyisonehiwa yakwatisiwa kwakunyi, yokutumbikiwa lo osapo yapitch.",
        ],
        "customer_relationships": [
            "Ombangulo lokutumbika lokolele koku andiwa kwotete kwakunyi.",
            "Oyitatica yombiliko lo yombuavo yina yombiliko ku {industry_label}.",
            "Programas yokusongela yina yombiliko komukanda wa mercado-alvo (score: {target_market_score:.1f}/10).",
        ],
        "channels": [
            "Onjila yokolele yoku go-to-market yalombolwiwa lyapitch lo oyisitina yaindustria.",
            "Onjila yodigital lo/ale yotete yina yombiliko oku pandekela mercado-alvo.",
            "Okusongela lokwalusako oku tumbika alcance hena okukula kwombongo.",
        ],
        "customer_segments": [
            "Osapo yokolele: akunyi lo ovangantuve mu {industry_label} lina ongongo yalombolwiwa mu pitch.",
            "Osapo yavali: akunyi vakwavo lina etyulo limwe.",
        ],
        "cost_structure": [
            "Ombangulo yombongo yina ombiliko lomangisi wa {profit_margin:.1f}%.",
            "Oyisapo yokolele yombongo: eutu, tecnologia/infraestrutura, lo okuandiwa kwakunyi.",
            "Oyisapo yamburn rate yohuela yina ombiliko oku kula lokwalusako.",
        ],
        "revenue_streams": [
            "Osapo yombongo yokolele yalombolwiwa mu {revenue:,.0f} AOA.",
            "Onjila yokukula ya {growth_rate:.1f}% okwenda ku elombolwilo.",
            "Osapo yombongo yavali okwenda ndokukula kweutu (ticket yalombolwiwa: {suggested_ticket}).",
        ],
    },
}

_DEFAULT_LANGUAGE = "en"

_INDUSTRY_LABEL_KEY = {
    "tech": {"pt": "Tecnologia", "en": "Technology", "ru": "Технологии", "de": "Technologie",
             "es": "Tecnologia", "zh-hans": "科技", "umb": "Tecnologia"},
    "health": {"pt": "Saude", "en": "Health", "ru": "Здравоохранение", "de": "Gesundheit",
               "es": "Salud", "zh-hans": "医疗健康", "umb": "Usaude"},
    "finance": {"pt": "Financas", "en": "Finance", "ru": "Финансы", "de": "Finanzen",
                "es": "Finanzas", "zh-hans": "金融", "umb": "Ombongo"},
    "education": {"pt": "Educacao", "en": "Education", "ru": "Образование", "de": "Bildung",
                  "es": "Educacion", "zh-hans": "教育", "umb": "Elongiso"},
    "ecommerce": {"pt": "E-commerce", "en": "E-commerce", "ru": "Электронная коммерция", "de": "E-Commerce",
                  "es": "Comercio electronico", "zh-hans": "电子商务", "umb": "E-commerce"},
    "other": {"pt": "Outro", "en": "Other", "ru": "Другое", "de": "Sonstiges",
              "es": "Otro", "zh-hans": "其他", "umb": "Ikuavo"},
}


def _industry_label(industry: str, language: str) -> str:
    labels = _INDUSTRY_LABEL_KEY.get(industry) or {}
    return labels.get(language) or labels.get(_DEFAULT_LANGUAGE) or (industry or "").title()


def generate_business_model_canvas(analysis, language: str = _DEFAULT_LANGUAGE) -> dict:
    """
    Builds a 9-block Business Model Canvas dict for a PitchAnalysis, derived
    entirely from data already on the analysis (no external API calls).
    """
    language = language if language in _TEMPLATES else _DEFAULT_LANGUAGE
    templates = _TEMPLATES[language]
    titles = BLOCK_TITLES.get(language, BLOCK_TITLES[_DEFAULT_LANGUAGE])

    report = analysis.report or {}
    metadata = analysis.metadata or {}
    category_scores = report.get("category_scores", {}) or {}
    investor_pitch = report.get("investor_pitch", {}) or {}

    startup_label = (analysis.startup_name or metadata.get("startup_name") or "").strip() or {
        "pt": "a startup avaliada", "en": "the evaluated startup",
        "ru": "оцениваемый стартап", "de": "das bewertete Startup",
        "es": "la startup evaluada", "zh-hans": "本次评估的创业公司",
        "umb": "startup yina yakuandiwa",
    }.get(language, "the evaluated startup")

    fmt_kwargs = {
        "startup_label": startup_label,
        "industry_label": _industry_label(analysis.industry, language),
        "revenue": float(analysis.revenue or 0),
        "growth_rate": float(analysis.growth_rate or 0),
        "profit_margin": float(analysis.profit_margin or 0),
        "founding_team_score": float(category_scores.get("founding_team", 5.0) or 5.0),
        "value_prop_score": float(category_scores.get("value_proposition", 5.0) or 5.0),
        "target_market_score": float(category_scores.get("target_market", 5.0) or 5.0),
        "suggested_ticket": investor_pitch.get("suggested_ticket", ""),
    }

    blocks = {}
    for key in BLOCK_KEYS:
        bullets = templates.get(key, [])
        blocks[key] = {
            "title": titles.get(key, key.replace("_", " ").title()),
            "items": [b.format(**fmt_kwargs) for b in bullets],
        }

    return {
        "section_title": SECTION_TITLE.get(language, SECTION_TITLE[_DEFAULT_LANGUAGE]),
        "intro": SECTION_INTRO.get(language, SECTION_INTRO[_DEFAULT_LANGUAGE]).format(**fmt_kwargs),
        "blocks": blocks,
    }
