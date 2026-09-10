def _safe_str(value, default: str = "") -> str:
    text = str(value if value is not None else default).strip()
    return text or default


def _safe_sentence(text: str) -> str:
    sentence = " ".join(_safe_str(text, "").split())
    if not sentence:
        return ""
    if sentence[-1] not in ".!?":
        sentence += "."
    return sentence


def _wrap_text_lines(text: str, max_chars: int = 80) -> list[str]:
    text = " ".join((_safe_str(text, "")).split())
    if not text:
        return []
    words = text.split(" ")
    lines = []
    current = []
    current_len = 0
    for word in words:
        add_len = len(word) + (1 if current else 0)
        if current and current_len + add_len > max_chars:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += add_len
    if current:
        lines.append(" ".join(current))
    return lines


def _truncate_text(text: str, max_chars: int = 340) -> str:
    text = _safe_str(text, "")
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0].strip()
    return (cut or text[:max_chars]).rstrip() + "..."


def _extract_startup_name(payload: dict) -> str:
    title = _safe_str(payload.get("title"), "")
    if " - " in title:
        candidate = title.split(" - ", 1)[-1].strip()
        if candidate:
            return candidate
    return _safe_str(payload.get("startup_name"), "Startup")


# Keyword matching is language-agnostic on purpose: the sections list may
# have been produced by either the English or the Portuguese local
# generator (or by GPT, in whichever language it was asked for), so we
# find the right section by meaning rather than by an exact-language title.
_SECTION_KEYWORDS = {
    "problem": ("problem", "problema"),
    "solution": ("solution", "solu"),
    "market": ("market", "mercado", "segment"),
    "model": ("business model", "modelo de neg", "unit economics"),
    "traction": ("traction", "tração", "tracao", "valida"),
}


def _sections_map(payload: dict) -> dict:
    mapped = {}
    for section in (payload.get("sections") or []):
        if not isinstance(section, dict):
            continue
        title = _safe_str(section.get("title"), "").lower()
        content = _safe_str(section.get("content"), "")
        if not title or not content:
            continue
        for key, keywords in _SECTION_KEYWORDS.items():
            if key in mapped:
                continue
            if any(kw in title for kw in keywords):
                mapped[key] = content
    return mapped


_FILLER = {
    "en": {
        "variants": [
            "disciplined execution and predictable results",
            "growth with governance and operational efficiency",
            "competitive differentiation focused on recurring revenue",
            "scalability sustained by metrics and commercial validation",
        ],
        "default_problem": "a relevant market pain point",
        "default_solution": "a solution with a clear value proposition",
        "default_market": "a growing market with room for leadership",
        "default_traction": "early indicators consolidating",
        "default_model": "a replicable, scale-oriented model",
        "default_slogan": "{startup_name} turns a critical need into sustainable growth.",
        "bullet_empty": "{startup} structures this theme with clear product, operational, and revenue goals, ensuring alignment between strategy and execution.",
        "bullet_short": " In the context of {slide_title}, the startup prioritizes {variant}, with defined owners, a delivery calendar, and a measurable success criterion.",
        "bullet_medium": " The market reading considers {market} and the monetization plan combines {model}.",
        "bullet_long": " The strategic rationale starts from the core problem ({problem}) and connects that pain to the solution's delivery capability ({solution}), with evolving traction signals ({traction}).",
        "section_titles": ["Problem", "Solution", "Market", "Business Model", "Traction"],
        "section_pad": " {startup_name} develops this front with {variant}, setting quarterly priorities, performance indicators, and an executive follow-up routine. Execution combines market validation, financial discipline, and continuous improvement of the value proposition.",
        "script_default": [
            "Opening: set the context for the opportunity and market relevance.",
            "Problem: detail the main pain point and its financial impact on the customer.",
            "Solution: present the approach, differentiator, and value delivery.",
            "Execution: show the operating model, GTM, and growth pace.",
            "Fundraising: explain the use of capital, milestones, and governance.",
            "Conclusion: reinforce the investment thesis and invite the next meeting.",
        ],
        "script_pad": " In this step {idx}, {startup_name} highlights {variant}, including the target KPI, execution timeline, main risk, and planned mitigation to protect investor returns.",
        "deck_titles": ["Opening", "Problem", "Solution", "Market", "Business Model", "Traction", "Roadmap", "Fundraising"],
        "deck_default_bullets": {
            "Roadmap": "Quarterly milestones and success criteria to scale safely.",
            "Fundraising": "Investment thesis, use of capital, and expected return.",
        },
        "slide_no_bullets": "{title}: a priority axis for consistent growth and commercial validation.",
        "slide_extra_bullet": "{title}: an additional front with an execution plan, metrics, and risk governance.",
        "slide_word": "Slide",
        "elevator_pad": " {startup_name} combines market vision, commercial execution, and financial discipline to capture pent-up demand with predictable growth, prioritizing acquisition and retention efficiency.",
        "closing_pad": " The startup presents a clear value thesis, a validatable operating plan, and governance to scale with quality. The proposed next step is a working meeting to review diligence, milestones, and the round's structure.",
    },
    "pt": {
        "variants": [
            "execucao disciplinada e previsibilidade de resultados",
            "crescimento com governanca e eficiencia operacional",
            "diferenciacao competitiva com foco em receita recorrente",
            "escalabilidade sustentada por metricas e validacao comercial",
        ],
        "default_problem": "dor relevante de mercado",
        "default_solution": "solucao com proposta de valor clara",
        "default_market": "mercado em crescimento com espaco para lideranca",
        "default_traction": "indicadores iniciais em consolidacao",
        "default_model": "modelo replicavel e orientado a escala",
        "default_slogan": "{startup_name} transforma uma necessidade critica em crescimento sustentavel.",
        "bullet_empty": "{startup} estrutura este tema com metas claras de produto, operacao e receita, garantindo alinhamento entre estrategia e execucao.",
        "bullet_short": " No contexto de {slide_title}, a startup prioriza {variant}, com responsaveis definidos, calendario de entrega e criterio de sucesso mensuravel.",
        "bullet_medium": " A leitura de mercado considera {market} e o plano de monetizacao combina {model}.",
        "bullet_long": " O racional estrategico parte do problema central ({problem}) e conecta essa dor a capacidade de entrega da solucao ({solution}), com sinais de tracao em evolucao ({traction}).",
        "section_titles": ["Problema", "Solucao", "Mercado", "Modelo de Negocio", "Tracao"],
        "section_pad": " {startup_name} desenvolve esta frente com {variant}, estabelecendo prioridades por ciclo trimestral, indicadores de desempenho e rotina de acompanhamento executivo. A execucao combina validacao de mercado, disciplina financeira e melhoria continua da proposta de valor.",
        "script_default": [
            "Abertura: contextualizar oportunidade e relevancia de mercado.",
            "Problema: detalhar dor principal e impacto financeiro para o cliente.",
            "Solucao: apresentar abordagem, diferencial e entrega de valor.",
            "Execucao: mostrar modelo operacional, GTM e ritmo de crescimento.",
            "Captacao: explicar uso de capital, marcos e governanca.",
            "Conclusao: reforcar tese de investimento e convite para proxima reuniao.",
        ],
        "script_pad": " Neste passo {idx}, {startup_name} evidencia {variant}, incluindo KPI alvo, prazo de execucao, risco principal e mitigacao prevista para proteger retorno do investidor.",
        "deck_titles": ["Abertura", "Problema", "Solucao", "Mercado", "Modelo de Negocio", "Tracao", "Roadmap", "Captacao"],
        "deck_default_bullets": {
            "Roadmap": "Marcos trimestrais e criterio de sucesso para escalar com seguranca.",
            "Captacao": "Tese de investimento, uso de capital e retorno esperado.",
        },
        "slide_no_bullets": "{title}: eixo prioritario para crescimento consistente e validacao comercial.",
        "slide_extra_bullet": "{title}: frente adicional com plano de execucao, metricas e governanca de risco.",
        "slide_word": "Slide",
        "elevator_pad": " {startup_name} combina visao de mercado, execucao comercial e disciplina financeira para capturar demanda reprimida com crescimento previsivel, priorizando eficiencia de aquisicao e retencao.",
        "closing_pad": " A startup apresenta tese clara de valor, plano operacional validavel e governanca para escalar com qualidade. O proximo passo proposto e uma reuniao tecnica para revisar diligencia, milestones e estrutura da rodada.",
    },
}


def _filler(language: str) -> dict:
    return _FILLER.get(language) or _FILLER["en"]


def _detail_variant(unique_key: str, language: str) -> str:
    variants = _filler(language)["variants"]
    if not unique_key:
        return variants[0]
    try:
        idx = int(unique_key, 16)
    except ValueError:
        idx = sum(ord(ch) for ch in unique_key)
    return variants[idx % len(variants)]


def _build_detail_context(payload: dict, language: str) -> dict:
    f = _filler(language)
    sections = _sections_map(payload)
    startup_name = _extract_startup_name(payload)
    problem = sections.get("problem") or _safe_str(payload.get("elevator_pitch"), f["default_problem"])
    solution = sections.get("solution") or f["default_solution"]
    market = sections.get("market") or f["default_market"]
    traction = sections.get("traction") or f["default_traction"]
    model = sections.get("model") or f["default_model"]
    slogan = _safe_str(payload.get("slogan"), f["default_slogan"].format(startup_name=startup_name))
    return {
        "startup_name": startup_name,
        "problem": _safe_sentence(problem),
        "solution": _safe_sentence(solution),
        "market": _safe_sentence(market),
        "traction": _safe_sentence(traction),
        "model": _safe_sentence(model),
        "slogan": _safe_sentence(slogan),
    }


def _expand_slide_bullet(text: str, slide_title: str, context: dict, variant: str, language: str) -> str:
    f = _filler(language)
    startup = context["startup_name"]
    problem = context["problem"]
    solution = context["solution"]
    market = context["market"]
    traction = context["traction"]
    model = context["model"]

    base = _safe_sentence(text)
    if not base:
        base = f["bullet_empty"].format(startup=startup)
    if len(base) < 120:
        base = base + f["bullet_short"].format(slide_title=slide_title, variant=variant)
    if len(base) < 210:
        base = base + f["bullet_medium"].format(market=market, model=model)
    if len(base) < 290:
        base = base + f["bullet_long"].format(problem=problem, solution=solution, traction=traction)
    return _safe_sentence(_truncate_text(base, 340))


def _ensure_detailed_sections(payload: dict, context: dict, variant: str, language: str):
    f = _filler(language)
    sections = payload.get("sections") or []
    if not isinstance(sections, list):
        sections = []
    if not sections:
        titles = f["section_titles"]
        sections = [
            {"title": titles[0], "content": context["problem"]},
            {"title": titles[1], "content": context["solution"]},
            {"title": titles[2], "content": context["market"]},
            {"title": titles[3], "content": context["model"]},
            {"title": titles[4], "content": context["traction"]},
        ]

    enriched = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        title = _safe_str(section.get("title"), f["section_titles"][0])
        content = _safe_sentence(section.get("content"))
        if len(content) < 220:
            content = (content + f["section_pad"].format(startup_name=context["startup_name"], variant=variant)).strip()
        enriched.append({"title": title, "content": _safe_sentence(content)})
    payload["sections"] = enriched


def _ensure_detailed_script(payload: dict, context: dict, variant: str, language: str):
    f = _filler(language)
    script = payload.get("script_3min") or []
    if not isinstance(script, list):
        script = []
    if not script:
        script = list(f["script_default"])

    detailed = []
    for idx, line in enumerate(script[:8], start=1):
        sentence = _safe_sentence(line)
        if len(sentence) < 160:
            sentence = sentence + f["script_pad"].format(idx=idx, startup_name=context["startup_name"], variant=variant)
        detailed.append(_safe_sentence(sentence))
    payload["script_3min"] = detailed


def _ensure_detailed_deck(payload: dict, context: dict, variant: str, language: str):
    f = _filler(language)
    deck = payload.get("pitch_deck") or []
    if not isinstance(deck, list):
        deck = []
    if not deck:
        titles = f["deck_titles"]
        pads = f["deck_default_bullets"]
        deck = [
            {"slide": 1, "title": titles[0], "bullets": [context["slogan"]]},
            {"slide": 2, "title": titles[1], "bullets": [context["problem"]]},
            {"slide": 3, "title": titles[2], "bullets": [context["solution"]]},
            {"slide": 4, "title": titles[3], "bullets": [context["market"]]},
            {"slide": 5, "title": titles[4], "bullets": [context["model"]]},
            {"slide": 6, "title": titles[5], "bullets": [context["traction"]]},
            {"slide": 7, "title": titles[6], "bullets": [pads[titles[6]]]},
            {"slide": 8, "title": titles[7], "bullets": [pads[titles[7]]]},
        ]

    enriched_deck = []
    for idx, raw_item in enumerate(deck[:12], start=1):
        item = raw_item if isinstance(raw_item, dict) else {}
        title = _safe_str(item.get("title"), f"{f['slide_word']} {idx}")
        bullets = [_safe_str(b, "") for b in (item.get("bullets") or []) if _safe_str(b, "")]
        if not bullets:
            bullets = [f["slide_no_bullets"].format(title=title)]

        expanded = [_expand_slide_bullet(bullet, title, context, variant, language) for bullet in bullets[:5]]
        while len(expanded) < 4:
            expanded.append(
                _expand_slide_bullet(
                    f["slide_extra_bullet"].format(title=title), title, context, variant, language,
                )
            )

        enriched_deck.append({"slide": item.get("slide", idx), "title": title, "bullets": expanded[:6]})
    payload["pitch_deck"] = enriched_deck


def enrich_pitch_payload(payload: dict, language: str = "en") -> dict:
    language = language if language in _FILLER else "en"
    f = _filler(language)
    context = _build_detail_context(payload, language)
    variant = _detail_variant(_safe_str(payload.get("narrative_uniqueness_key"), ""), language)

    _ensure_detailed_sections(payload, context, variant, language)
    _ensure_detailed_script(payload, context, variant, language)
    _ensure_detailed_deck(payload, context, variant, language)

    elevator = _safe_sentence(payload.get("elevator_pitch"))
    if len(elevator) < 260:
        elevator = (elevator + f["elevator_pad"].format(startup_name=context["startup_name"])).strip()
    payload["elevator_pitch"] = _safe_sentence(elevator)

    closing = _safe_sentence(payload.get("closing"))
    if len(closing) < 170:
        closing = (closing + f["closing_pad"]).strip()
    payload["closing"] = _safe_sentence(closing)
    return payload
